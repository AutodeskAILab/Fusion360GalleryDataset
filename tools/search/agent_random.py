import numpy as np
import math

from agent import Agent


class AgentRandom(Agent):

    def __init__(self):
        super().__init__()

    def set_target(self, target_graph, bounding_box):
        """Set the target graph"""
        super().set_target(target_graph, bounding_box)
        # Store a list of the faces we can choose from
        # These will get filtered for something sensible during search
        self.target_faces = []
        for node in self.target_graph["nodes"]:
            self.target_faces.append(node["id"])
        assert len(self.target_faces) >= 2

    def get_actions_probabilities(self, current_graph, target_graph):
        super().get_actions_probabilities(current_graph, target_graph)
        list_actions = []
        list_probabilities = []
        for t1 in self.target_faces:
            prob_t1 = 1 / len(self.target_faces)
            for t2 in self.target_faces:
                if t1 != t2:
                    prob_t2 = 1 / (len(self.target_faces) - 1)
                    for op in self.operations:
                        prob_op = 1 / len(self.operations)
                        action = {
                            "start_face": t1,
                            "end_face": t2,
                            "operation": op
                        }
                        action_prob = prob_t1 * prob_t2 * prob_op
                        if math.isnan(action_prob):
                            action_prob = 0.0

                        list_actions.append(action)
                        list_probabilities.append(action_prob)

        return np.array(list_actions), np.array(list_probabilities)
