"""

Reconstruct from a target design

"""

import adsk.core
import adsk.fusion
import os
import sys
import importlib

from .command_base import CommandBase

# # Add the common folder to sys.path
# COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
# if COMMON_DIR not in sys.path:
#     sys.path.append(COMMON_DIR)
# import name
# import match
# import deserialize
# import serialize
# importlib.reload(name)
# importlib.reload(match)
# importlib.reload(deserialize)
# importlib.reload(serialize)


class CommandTarget(CommandBase):

    def __init__(self, runner):
        command_base.CommandBase.__init__(self, runner)
        self.target_component = None

    def set_target(self, data):
        """Set the target design"""
        error, suffix = self.check_file(data, [".step", ".stp", ".smt"])
        if error is not None:
            return self.runner.return_failure(error)
        # Create the file locally
        temp_file = self.get_temp_file(data["file"], dest_dir)
        with open(temp_file, "w") as f:
            f.write(data["file_data"])
        # We clear the design before importing
        self.runner.clear()
        # Import the geometry
        if suffix == ".step" or suffix == ".stp":
            import_options = self.app.importManager.createSTEPImportOptions(
                str(self.temp_file.resolve())
            )
        else:
            import_options = self.app.importManager.createSMTImportOptions(
                str(self.temp_file.resolve())
            )
        import_options.isViewFit = False
        imported_designs = self.app.importManager.importToTarget2(
            import_options,
            self.design.rootComponent
        )
        # Store references to the target bodies
        self.state["target_bodies"] = []
        # We do a little bit of clean up here so the target design
        # is in the root of the document
        for occ in imported_designs:
            for body in occ.bRepBodies:
                # Rename it as the goal so we don't get confused
                self.state["target_bodies"].append(body)
                body.name = f"Target-{body.name}"
                body.moveToComponent(self.design.rootComponent)
            occ.deleteMe()
        # TODO: Return a graph of the target design
