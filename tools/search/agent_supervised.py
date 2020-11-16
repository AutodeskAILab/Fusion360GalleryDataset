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
REGRAPHNET_SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "regraphnet", "src")
if REGRAPHNET_SRC_DIR not in sys.path:
    sys.path.append(REGRAPHNET_SRC_DIR)

from train import *


class AgentSupervised(Agent):

    def __init__(self, use_gcn=True, syn_data=None):
        super().__init__()
        self.model = NodePointer(nfeat=708, nhid=256, Use_GCN=use_gcn)
        regraphnet_dir = Path(REGRAPHNET_DIR)
        if syn_data == "syn":
            # Currently only support synthetic data with GCN
            checkpoint_file = regraphnet_dir / "ckpt/model_mpn_syn.ckpt"
        elif syn_data == "semisyn":
            # Currently only support semi synthetic data with GCN
            checkpoint_file = regraphnet_dir / "ckpt/model_mpn_semisyn.ckpt"
        else:
            if use_gcn:
                if syn_data == "aug":
                    checkpoint_file = regraphnet_dir / "ckpt/model_mpn_aug.ckpt"
                else:
                    checkpoint_file = regraphnet_dir / "ckpt/model_mpn.ckpt"
            else:
                if syn_data == "aug":
                    checkpoint_file = regraphnet_dir / "ckpt/model_mlp_aug.ckpt"
                else:
                    checkpoint_file = regraphnet_dir / "ckpt/model_mlp.ckpt"
        print(f"Using {checkpoint_file.name}")
        assert checkpoint_file.exists()
        # Using CUDA is slower, so we use cpu
        # Specify cpu to map to
        self.model.load_state_dict(
            torch.load(checkpoint_file, map_location=torch.device("cpu"))
        )

    def get_actions_probabilities(self, current_graph, target_graph):
        super().get_actions_probabilities(current_graph, target_graph)
        graph_pair_formatted, node_names = self.load_graph_pair(target_graph, current_graph)
        actions_sorted, probs_sorted = self.inference(graph_pair_formatted, node_names)
        return np.array(actions_sorted), np.array(probs_sorted)

    def load_graph_pair(self, data_tar, data_cur):
        adj_tar, features_tar = format_graph_data(data_tar, self.bounding_box)
        # If the current graph is empty
        if len(data_cur["nodes"]) == 0:
            adj_cur, features_cur = torch.zeros((0)), torch.zeros((0))
        else:
            adj_cur, features_cur = format_graph_data(
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
                graph_pair_formatted, use_gpu=False)
            output_start = F.softmax(output_start.view(1, -1), dim=1)
            output_op = F.softmax(output_op, dim=1)
            for i in range(num_nodes):
                graph_pair_formatted[4] = i
                _, output_end, _ = self.model(graph_pair_formatted, use_gpu=False)
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
