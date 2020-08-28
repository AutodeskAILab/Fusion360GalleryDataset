import numpy as np
import math

from agent import Agent


class AgentSupervised(Agent):

    def __init__(self, target_graph):
        super().__init__(target_graph)

    def get_actions_probabilities(self, current_graph, target_graph):
        super().get_actions_probabilities(current_graph, target_graph)
        list_actions = []
        list_probabilities = []
        # TODO: Populate the actions and probabilities lists
        return np.array(list_actions), np.array(list_probabilities)
