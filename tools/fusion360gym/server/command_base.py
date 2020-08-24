"""

Base Command Class

"""

import adsk.core


class CommandBase():

    def __init__(self, runner):
        self.runner = runner
        self.logger = None
        self.app = adsk.core.Application.get()
        self.state = {}

    def set_logger(self, logger):
        self.logger = logger

    def clear(self):
        """Clear the state"""
        self.state = {}
