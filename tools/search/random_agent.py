from agent import Agent


class RandomAgent(Agent):

    def __init__(self, target_graph):
        Agent.__init__(self, target_graph)
        # Store a list of the faces we can choose from
        self.target_faces = []
        for node in self.target_graph["nodes"]:
            # Leaving all faces in right now to compare fairly with
            # other search approaches
            # if node["surface_type"] == "PlaneSurfaceType":
            self.target_faces.append(node["id"])
        assert len(self.target_faces) >= 2

    def get_actions_prob(current_graph, target_graph):
        list_actions = []
        list_probabilities = []
        for t1 in self.target_faces:
            prob_t1 = 1 / len(self.target_faces)
            for t2 in self.target_faces:
                if t1 != t2:
                    prob_t2 = 1 / (len(self.target_faces) - 1)
                    for op in self.operations:
                        prob_op = 1 / len(self.operations)

                        action = (t1, t2, op)
                        action_prob = prob_t1 * prob_t2 * prob_op

                        list_actions.append(action)
                        list_probabilities.append(action_prob)

        return list_actions, list_probabilities
