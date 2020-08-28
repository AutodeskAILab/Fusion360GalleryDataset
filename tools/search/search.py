import time
import json
from pathlib import Path

from log import Log


class Search:

    def __init__(self, env):
        self.env = env
        self.log = Log()

    def set_target(self, target_file):
        """Set the target we are searching for"""
        self.target_file = target_file
        assert self.target_file.exists()
        self.target_graph = self.env.set_target(self.target_file)
        return self.target_graph

    def get_score_over_time(self, agent, budget, score_function):
        pass
