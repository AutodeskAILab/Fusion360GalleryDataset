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


class CommandRunner():

    def __init__(self):
        self.logger = None
        self.app = adsk.core.Application.get()
        self.last_command = ""
        self.export = CommandExport(self)
        self.export = CommandExport(self)
        self.increment = CommandIncrement(self)
        self.target = CommandTarget(self)
        self.reconstruct = CommandReconstruct(self)

    def set_logger(self, logger):
        self.logger = logger
        self.export.set_logger(logger)
        self.increment.set_logger(logger)
        self.target.set_logger(logger)

    def run_command(self, command, data=None):
        """Run a command and route it to the right method"""
        try:
            self.last_command = command
            result = None
            if command == "ping":
                result = self.ping()
            elif command == "refresh":
                result = self.refresh()
            elif command == "reconstruct":
                result = self.reconstruct.reconstruct(data)
            elif command == "reconstruct_sketch":
                result = self.reconstruct.reconstruct_sketch(data)
            elif command == "clear":
                result = self.clear()
            elif command == "mesh":
                result = self.export.mesh(data)
            elif command == "brep":
                result = self.export.brep(data)
            elif command == "sketches":
                result = self.export.sketches(data)
            elif command == "commands":
                result = self.export.commands(data)
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
            elif command == "add_extrude_by_target_face":
                result = self.target.add_extrude_by_target_face(data)
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

    def refresh(self):
        """Refresh the active viewport"""
        self.app.activeViewport.refresh()
        return self.return_success()

    def clear(self):
        """Clear (i.e. close) all open designs in Fusion"""
        for doc in self.app.documents:
            # Save without closing
            doc.close(False)
        self.increment.clear()
        self.target.clear()
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
