

class Agent:

    def __init__(self, target_graph):
        self.target_graph = target_graph
        self.operations = [
            "NewBodyFeatureOperation",
            "JoinFeatureOperation",
            "CutFeatureOperation",
            "IntersectFeatureOperation"
        ]

    def get_actions_prob(current_graph, target_graph):
        """Given the current graph, and the target graph, give two lists:
            1) a list of all possible actions,
                where each action is a triple (start_face, end_face, operation)
            2) the associated probability for each action"""
        pass
