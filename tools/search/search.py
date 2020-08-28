import time
import json
from pathlib import Path

from log import Log


class Search:

    def __init__(self, env):
        self.env = env
        self.log = Log(env)

    def set_target(self, target_file):
        """Set the target we are searching for"""
        assert target_file.exists()
        self.target_file = target_file
        self.log.set_target(target_file)
        self.target_graph = self.env.set_target(self.target_file)
        return self.target_graph

    def search(self, agent, budget, score_function=None, screenshot=False):
        """Given a particular agent, a search budget
            (measured in number of repl invocations, specifically,
            the number of "extrude" function calls),
            and a particular scoring function (iou or complete reconstruction)
            search for up to each repl invocation,
            the best score obtained from the set of explored programs in the search"""
        assert self.target_graph is not None

    def filter_bad_actions(self, current_graph, actions, action_probabilities):
        """Filter out some actions we clearly don't want to take"""
        assert self.target_graph is not None
        # Make a set of the valid nodes that are planar
        nodes = self.target_graph["nodes"]
        valid_nodes = set()
        for node in nodes:
            if node["surface_type"] == "PlaneSurfaceType":
                valid_nodes.add(node["id"])
        # Flag for if the current graph is empty
        is_current_graph_empty = len(current_graph["nodes"]) == 0
        # Adjust the probabilities of bad actions
        for index, action in enumerate(actions):
            # We only want faces that are planar
            if action["start_face"] not in valid_nodes:
                action_probabilities[index] = 0.0
            elif action["end_face"] not in valid_nodes:
                action_probabilities[index] = 0.0
            # If the current graph is empty, we want a new body operation
            elif is_current_graph_empty and action["operation"] != "NewBodyFeatureOperation":
                action_probabilities[index] = 0.0
        action_probabilities = action_probabilities / sum(action_probabilities)
        return action_probabilities
