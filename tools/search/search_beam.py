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
        elif rollout_length > 2:
            rollout_length = math.ceil(rollout_length / 2)

        rollout_attempt = 0
        used_budget = 0
        max_score = 0
        max_scores = []

        # we set a beam width, and double it each time if we did not solve it
        beam_width = 1

        while used_budget < budget:
            # We begin each rollout an empty graph
            cur_graph = self.env.get_empty_graph()
            # the beam datastructure, for each time_step, holds a list,
            # representing the top_beam_width number of (prefix, logpr(prefix))
            # where the logpr(prefix) is the logpr of generation under the policy
            # () is the empty prefix of actions, the original log_probability is 0
            # at the 0th timestep
            beam = [
                [
                    ((), 0)
                ]
            ]
            # Example:
            # beam = [
            #     [
            #         ((a1, a2, a10), -7),
            #         ((a3, a5, a12), -8)
            #     ]
            # ]
            # Each element in the data structure
            # prefix (dict): start_face, end_face, operation
            # prefix_prob (tuple): [prefix], prefix_logpr
            # beam_head (list): [prefix_prob]
            # beam (list): beam_heads

            for i in range(rollout_length):
                # the last time-step in the beam
                last_beam_head = beam[-1]
                # the candidate for the next time-step in the beam
                new_beam_candidates = []
                for prefix, prefix_logpr in last_beam_head:
                    # execute the prefix, and since we took an envstep, add 1 to budget (make extrudes able to handle empty enumerables)
                    new_graph, cur_iou = self.env.extrudes(list(prefix), revert=True)
                    # Only increment the budget when we did work
                    if len(prefix) > 0:
                        used_budget += 1
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
                            "current_iou": cur_iou,
                            "max_iou": max_score,
                            "prefix": list(prefix)
                        }
                        self.log.log(log_data, take_screenshot)
                        max_scores.append(max_score)
                        # Stop early if we find a solution
                        if math.isclose(max_score, 1, abs_tol=0.00001):
                            return max_scores
                        # Stop if the rollout hits the budget
                        if used_budget >= budget:
                            break

                    # If there was an invalid operation
                    # continue without adding it to the search space
                    if (new_graph is None or cur_iou is None) and len(prefix) > 0:
                        continue

                    # extend the current prefix by 1 step forward
                    actions, action_probabilities = agent.get_actions_probabilities(cur_graph, self.target_graph)
                    # Filter for clearly bad actions
                    action_probabilities = self.filter_bad_actions(cur_graph, actions, action_probabilities)
                    # Convert probability to logpr so they can be added rather than multiplied for numerical stability
                    action_logprs = np.log(action_probabilities)
                    # add to the candidates the extended prefix
                    # and the added log_probability (note the logpr will get more and more negative)
                    new_beam_candidates = []
                    for (a, a_logpr) in zip(actions, action_logprs):
                        child_prefix = prefix + (a,)
                        child_prob = prefix_logpr + a_logpr
                        new_beam_candidates.append((child_prefix, child_prob))

                if used_budget >= budget:
                    break
                # take the top_beam_width number of candidates, sort by -log_prob
                new_beam_candidates_sorted = sorted(new_beam_candidates, key = lambda xx : -xx[1])
                new_beam_head = new_beam_candidates_sorted[:beam_width]
                if len(new_beam_head) == 0:
                    # print("All prefixed are not good, restarting")
                    break
                print(f"[{used_budget}/{budget}] Score: {max_score}")
                beam.append(new_beam_head)

            # if we did not solve with the current beam width, multiply width by 2
            beam_width = beam_width * 2
            # print(f"Doubling the beam width: {beam_width}")

            # Revert to the target and remove all reconstruction
            self.env.revert_to_target()
            rollout_attempt += 1
        return max_scores
