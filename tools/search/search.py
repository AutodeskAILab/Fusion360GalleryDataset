import time
import json
from pathlib import Path

from log import Log


class Search:

    def __init__(self, env, log_dir=None):
        self.env = env
        self.log = Log(env, log_dir)

    def set_target(self, target_file):
        """Set the target we are searching for"""
        assert target_file.exists()
        self.target_file = target_file
        self.log.set_target(target_file)
        self.target_graph, self.target_bounding_box = self.env.set_target(
            self.target_file
        )
        # Make a set of the valid nodes that are planar
        # We use this for filtering later on
        nodes = self.target_graph["nodes"]
        self.valid_nodes = set()
        for node in nodes:
            if node["surface_type"] == "PlaneSurfaceType":
                self.valid_nodes.add(node["id"])
        return self.target_graph, self.target_bounding_box

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
        epsilon = 0.00000000001
        # Flag for if the current graph is empty
        is_current_graph_empty = len(current_graph["nodes"]) == 0
        # Adjust the probabilities of bad actions
        for index, action in enumerate(actions):
            # We only want faces that are planar
            if action["start_face"] not in self.valid_nodes:
                action_probabilities[index] = epsilon
            elif action["end_face"] not in self.valid_nodes:
                action_probabilities[index] = epsilon
            # If the current graph is empty, we want a new body operation
            elif is_current_graph_empty and action["operation"] != "NewBodyFeatureOperation":
                action_probabilities[index] = epsilon
            # This operation is not valid for the reconstruction task
            elif action["operation"] == "NewComponentFeatureOperation":
                action_probabilities[index] = epsilon
            # Hack to avoid divide by zero
            if action_probabilities[index] < epsilon:
                action_probabilities[index] = epsilon

        action_probabilities = action_probabilities / sum(action_probabilities)
        return action_probabilities
