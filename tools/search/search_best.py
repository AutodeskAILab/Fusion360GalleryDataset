import sys
import os
import random
import math
import functools
from pathlib import Path
import numpy as np
from queue import PriorityQueue


from search import Search


class SearchBest(Search):

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

        used_budget = 0
        max_score = 0
        max_scores = []

        # We begin each rollout an empty graph
        cur_graph = self.env.get_empty_graph()
        # like beam search, we keep track of prefixes, but instead of a beam we keep a "fringe"
        # we implement this with a priority queue, the queue ordered by min first max last
        # so we'll use _negative_ log likelihood and go after the "smallest" nll instead of the max like we do in beam
        # each entry in the fringe is a custom PriorityAction (neg_likelihood, (prefix))
        # where prefix is a tuple that contains the actions, that are dicts
        # for example an element of the queue is something like : (10, (a1, a4, a10))
        fringe = PriorityQueue()
        fringe.put(PriorityAction(0, ()))

        # while there is item in the fridge and we still have budget
        while fringe.qsize() > 0 and used_budget < budget:
            priority_action = fringe.get()
            # nll is something like 10, prefix is something like (a1, a4, a10)
            nll = priority_action.nll
            prefix = priority_action.prefix
            new_graph, cur_iou = self.env.extrudes(list(prefix), revert=True)
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
                    # "rollout_attempt": rollout_attempt,
                    # "rollout_step": i,
                    # "rollout_length": rollout_length,
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
            # add to the candidates back to fringe
            for (a, a_logpr) in zip(actions, action_logprs):
                child_prefix = prefix + (a,)
                child_nll = nll - a_logpr
                # do not add a prefix that's longer than rollout length
                if len(child_prefix) < rollout_length:
                    fringe.put(PriorityAction(child_nll, child_prefix))

            print(f"[{used_budget}/{budget}] Score: {max_score}")
        return max_scores


@functools.total_ordering
class PriorityAction():

    def __init__(self, nll, prefix):
        self.nll = nll
        self.prefix = prefix
        self.prefix_str = str(prefix)

    def __gt__(self, other):
        if self.nll == other.nll:
            return self.prefix_str > other.prefix_str
        else:
            return self.nll > other.nll

    def __eq__(self, other):
        return self.nll == other.nll and self.prefix_str == other.prefix_str
