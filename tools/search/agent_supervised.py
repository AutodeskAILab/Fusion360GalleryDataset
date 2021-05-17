import os
import sys
import numpy as np
import math
from pathlib import Path
import torch
import torch.nn as nn
import torch.nn.functional as F

from agent import Agent

# Add the network folder to sys.path
REGRAPHNET_DIR = os.path.join(os.path.dirname(__file__), "..", "regraphnet")
REGRAPHNET_SRC_DIR = os.path.join(REGRAPHNET_DIR, "src")
if REGRAPHNET_SRC_DIR not in sys.path:
    sys.path.append(REGRAPHNET_SRC_DIR)

import train_vanilla
import train_torch_geometric


class AgentSupervised(Agent):

    def __init__(self, agent, syn_data):
        super().__init__()
        if agent in ["gcn", "mlp"]:
            self.model = train_vanilla.NodePointer(
                nfeat=708,
                nhid=256,
                Use_GCN=(agent == "gcn")
            )
            self.train_ref = train_vanilla
        else:
            self.model = train_torch_geometric.NodePointer(
                nfeat=708,
                nhid=256,
                MPN_type=agent
            )
            self.train_ref = train_torch_geometric
        regraphnet_dir = Path(REGRAPHNET_DIR)
        checkpoint_name = f"model_{agent}"
        if syn_data is not None:
            checkpoint_name += f"_{syn_data}"
        checkpoint_file = regraphnet_dir / f"ckpt/{checkpoint_name}.ckpt"
        if not checkpoint_file.exists():
            print(f"Error: Checkpoint {checkpoint_file.name} does not exist")
            exit()

        print("-------------------------")
        print(f"Using {checkpoint_file.name}")

        # Using CUDA is slower, so we use cpu
        # Specify cpu to map to
        self.model.load_state_dict(
            torch.load(checkpoint_file, map_location=torch.device("cpu"))
        )

    def get_actions_probabilities(self, current_graph, target_graph):
        super().get_actions_probabilities(current_graph, target_graph)
        graph_pair_formatted, node_names = self.load_graph_pair(
            target_graph,
            current_graph
        )
        actions_sorted, probs_sorted = self.inference(
            graph_pair_formatted,
            node_names
        )
        return np.array(actions_sorted), np.array(probs_sorted)

    def load_graph_pair(self, data_tar, data_cur):
        adj_tar, features_tar = self.train_ref.format_graph_data(
            data_tar,
            self.bounding_box
        )
        # If the current graph is empty
        if len(data_cur["nodes"]) == 0:
            adj_cur, features_cur = torch.zeros((0)), torch.zeros((0))
        else:
            adj_cur, features_cur = self.train_ref.format_graph_data(
                data_cur, self.bounding_box
            )
        graph_pair_formatted = [adj_tar, features_tar, adj_cur, features_cur]
        node_names = [x["id"] for x in data_tar["nodes"]]
        return graph_pair_formatted, node_names

    def inference(self, graph_pair_formatted, node_names):
        self.model.eval()
        num_nodes = graph_pair_formatted[1].size()[0]
        output_end_conditioned = np.zeros((num_nodes, num_nodes))
        with torch.no_grad():
            graph_pair_formatted.append(0)
            output_start, _, output_op = self.model(
                graph_pair_formatted,
                use_gpu=False
            )
            output_start = F.softmax(output_start.view(1, -1), dim=1)
            output_op = F.softmax(output_op, dim=1)
            for i in range(num_nodes):
                graph_pair_formatted[4] = i
                _, output_end, _ = self.model(
                    graph_pair_formatted,
                    use_gpu=False
                )
                output_end = F.softmax(output_end.view(1, -1), dim=1)
                output_end_conditioned[i, :] = output_end.data.numpy()
        ps = [
            output_start.data.numpy()[0, :],
            output_end_conditioned,
            output_op.data.numpy()[0, :]
        ]
        # enumerate all actions
        actions, probs = [], []
        for i in range(len(node_names)):
            for j in range(len(node_names)):
                for k in range(len(self.operations)):
                    actions.append({
                        "start_face": node_names[i],
                        "end_face": node_names[j],
                        "operation": self.operations[k]
                    })
                    probs.append(ps[0][i]*ps[1][i, j]*ps[2][k])
        return actions, probs
