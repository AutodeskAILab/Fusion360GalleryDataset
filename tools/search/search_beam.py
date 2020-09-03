import sys
import os
import random
import math
from pathlib import Path
import numpy as np


from search import Search


class SearchBeam(Search):

    def __init__(self, env, log_dir=None):
        super().__init__(env, log_dir)

    def search(self, agent, budget, score_function=None, screenshot=False):
        super().search(agent, budget, score_function, screenshot)
        # the length of rollout is the same as the number of planar faces as a maximum
        rollout_length = 0
        for node in self.target_graph["nodes"]:
            if node["surface_type"] == "PlaneSurfaceType":
                rollout_length += 1
        if rollout_length < 2:
            # There exist some designs with no planar faces that we can't handle
            # We need at least 2 faces
            raise Exception("Not enough valid planar faces in target")
        rollout_attempt = 0
        used_budget = 0
        max_score = 0
        max_scores = []

        while used_budget < budget:
            # We begin each rollout an empty graph
            cur_graph = self.env.get_empty_graph()
            for i in range(rollout_length):
                actions, action_probabilities = agent.get_actions_probabilities(cur_graph, self.target_graph)
                # Filter for clearly bad actions
                action_probabilities = self.filter_bad_actions(cur_graph, actions, action_probabilities)

                # TODO: Implement Beam Search here
                new_graph, cur_iou = self.env.extrude(action["start_face"], action["end_face"], action["operation"])

                # Not implemented yet, but to execute a sequence of extrudes we can do something like this
                # To pass in the actions and a flag to indicate if we want to revert (i.e. start from scratch)
                # new_graph, cur_iou = self.env.extrudes([
                #     [start_face_0, end_face_0, operation_0],
                #     [start_face_1, end_face_1, operation_1],
                #     [start_face_2, end_face_2, operation_2]
                # ], revert=True)

                take_screenshot = screenshot
                if cur_iou is not None:
                    max_score = max(max_score, cur_iou)
                else:
                    # We only want to take screenshots when something changes
                    take_screenshot = False
                if new_graph is not None:
                    cur_graph = new_graph

                log_data = {
                    "rollout_attempt": rollout_attempt,
                    "rollout_step": i,
                    "rollout_length": rollout_length,
                    "used_budget": used_budget,
                    "budget": budget,
                    "start_face": action["start_face"],
                    "end_face": action["end_face"],
                    "operation": action["operation"],
                    "current_iou": cur_iou,
                    "max_iou": max_score
                }
                self.log.log(log_data, take_screenshot)
                max_scores.append(max_score)
                # Stop early if we find a solution
                if math.isclose(max_score, 1, abs_tol=0.00001):
                    return max_scores
                used_budget += 1
                # Stop if the rollout hits the budget
                if used_budget >= budget:
                    break
            # Revert to the target and remove all reconstruction
            self.env.revert_to_target()
            rollout_attempt += 1
        return max_scores
