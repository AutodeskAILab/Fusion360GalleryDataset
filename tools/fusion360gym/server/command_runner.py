"""

Run incoming commands from the client

"""

import adsk.core
import adsk.fusion
import traceback
import tempfile
import shutil
import os
from zipfile import ZipFile
from pathlib import Path

from .command_export import CommandExport
from .command_increment import CommandIncrement
from .command_target import CommandTarget
from .command_reconstruct import CommandReconstruct
from .design_state import DesignState


class CommandRunner():

    def __init__(self):
        self.logger = None
        self.app = adsk.core.Application.get()
        self.last_command = ""
        self.design_state = DesignState(self)
        self.export = CommandExport(self, self.design_state)
        self.increment = CommandIncrement(self, self.design_state)
        self.target = CommandTarget(self, self.design_state)
        self.reconstruct = CommandReconstruct(self, self.design_state)
        self.command_objects = [
            self.export,
            self.increment,
            self.target,
            self.reconstruct
        ]
        self.design_state.set_command_objects(self.command_objects)

    def set_logger(self, logger):
        """Set the logger in all command objects"""
        self.logger = logger
        self.design_state.set_logger(logger)
        for obj in self.command_objects:
            obj.set_logger(logger)

    def run_command(self, command, data=None):
        """Run a command and route it to the right method"""
        try:
            self.last_command = command
            result = None
            if command == "ping":
                result = self.ping()
            elif command == "refresh":
                result = self.design_state.refresh()
            elif command == "reconstruct":
                result = self.reconstruct.reconstruct(data)
            elif command == "reconstruct_sketch":
                result = self.reconstruct.reconstruct_sketch(data)
            elif command == "reconstruct_profile":
                result = self.reconstruct.reconstruct_profile(data)
            elif command == "reconstruct_curve":
                result = self.reconstruct.reconstruct_curve(data)
            elif command == "clear":
                result = self.design_state.clear()
            elif command == "mesh":
                result = self.export.mesh(data)
            elif command == "brep":
                result = self.export.brep(data)
            elif command == "sketches":
                result = self.export.sketches(data)
            elif command == "screenshot":
                result = self.export.screenshot(data)
            elif command == "graph":
                result = self.export.graph(data)
            elif command == "add_sketch":
                result = self.increment.add_sketch(data)
            elif command == "add_point":
                result = self.increment.add_point(data)
            elif command == "add_line":
                result = self.increment.add_line(data)
            elif command == "close_profile":
                result = self.increment.close_profile(data)
            elif command == "add_extrude":
                result = self.increment.add_extrude(data)
            elif command == "set_target":
                result = self.target.set_target(data)
            elif command == "revert_to_target":
                result = self.target.revert_to_target()
            elif command == "add_extrude_by_target_face":
                result = self.target.add_extrude_by_target_face(data)
            elif command == "add_extrudes_by_target_face":
                result = self.target.add_extrudes_by_target_face(data)
            else:
                return self.return_failure("Unknown command")
            return result
        except Exception as ex:
            return self.return_exception(ex)
        finally:
            # Update the UI
            adsk.doEvents()

    def ping(self):
        """Ping for debugging"""
        return self.return_success()

    def return_success(self, data=None):
        message = f"Success processing {self.last_command} command"
        return 200, message, data

    def return_failure(self, reason):
        message = f"Failed processing {self.last_command} command due to {reason}"
        return 500, message, None

    def return_exception(self, ex):
        message = f"""Error processing {self.last_command} command\n
                        Exception of type {type(ex)} with args: {ex.args}\n
                        {traceback.format_exc()}"""
        return 500, message, None
