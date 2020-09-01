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

from train_v4 import *


class AgentSupervised(Agent):

    def __init__(self, target_graph):
        super().__init__(target_graph)
        self.model = NodePointer(nfeat=120, nhid=256)
        regraphnet_dir = Path(REGRAPHNET_DIR)
        checkpoint_file = regraphnet_dir / "ckpt/model_v4.ckpt"
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
        adj_tar, features_tar = format_graph_data(data_tar)
        # If the current graph is empty
        if len(data_cur["nodes"]) == 0:
            adj_cur, features_cur = torch.zeros((0)), torch.zeros((0))
        else:
            adj_cur, features_cur = format_graph_data(data_cur)
        graph_pair_formatted = [adj_tar, features_tar, adj_cur, features_cur]
        node_names = [x["id"] for x in data_tar["nodes"]]
        return graph_pair_formatted, node_names

    def inference(self, graph_pair_formatted, node_names):
        self.model.eval()
        with torch.no_grad():
            output_node, output_op = self.model(
                graph_pair_formatted, use_gpu=False)
            output_start = F.softmax(output_node[:, 0].view(1, -1), dim=1)
            output_end = F.softmax(output_node[:, 1].view(1, -1), dim=1)
            output_op = F.softmax(output_op, dim=1)
            ps = [
                output_start.data.numpy()[0, :],
                output_end.data.numpy()[0, :],
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
                    probs.append(ps[0][i]*ps[1][j]*ps[2][k])
        # actions_sorted, probs_sorted = [], []
        # idx = np.argsort(-np.array(probs))
        # for i in range(len(probs)):
        #     actions_sorted.append(actions[idx[i]])
        #     probs_sorted.append(probs[idx[i]])
        # return actions_sorted, probs_sorted
        return actions, probs
