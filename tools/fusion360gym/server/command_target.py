"""

Reconstruct from a target design

"""

import adsk.core
import adsk.fusion
import os
import sys
import importlib

from .command_base import CommandBase

# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)
# import name
# import match
import deserialize
# import serialize
# importlib.reload(name)
# importlib.reload(match)
importlib.reload(deserialize)
# importlib.reload(serialize)
import regraph
importlib.reload(regraph)
from regraph import Regraph
from regraph import RegraphReconstructor


class CommandTarget(CommandBase):

    def __init__(self, runner):
        CommandBase.__init__(self, runner)
        self.target_component = None

    def set_target(self, data):
        """Set the target design"""
        error, suffix = self.check_file(data, [".step", ".stp", ".smt"])
        if error is not None:
            return self.runner.return_failure(error)
        # Create the file locally
        temp_file = self.get_temp_file(data["file"])
        with open(temp_file, "w") as f:
            f.write(data["file_data"])
        # We clear the design before importing
        self.runner.clear()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Import the geometry
        if suffix == ".step" or suffix == ".stp":
            import_options = self.app.importManager.createSTEPImportOptions(
                str(temp_file.resolve())
            )
        else:
            import_options = self.app.importManager.createSMTImportOptions(
                str(temp_file.resolve())
            )
        import_options.isViewFit = False
        imported_designs = self.app.importManager.importToTarget2(
            import_options,
            self.design.rootComponent
        )
        if imported_designs is None:
            return self.runner.return_failure(
                f"Error importing target {suffix} file")
        # Store references to the target bodies
        self.state["target_bodies"] = []

        # We do a little bit of clean up here so the target design
        # is in the root of the document
        for occ in imported_designs:
            for body in occ.bRepBodies:
                # Rename it as the goal so we don't get confused
                moved_body = body.moveToComponent(self.design.rootComponent)
                moved_body.name = f"Target-{moved_body.name}"
                self.state["target_bodies"].append(moved_body)
            # We can't seem to delete the occurrence
            # as it seems to be referenced...
            # occ.deleteMe()
        adsk.doEvents()
        regraph = Regraph(logger=self.logger, mode="PerFace")
        graph = regraph.generate_from_bodies(self.state["target_bodies"])
        temp_file.unlink()
        # Setup the reconstructor
        self.state["reconstructor"] = RegraphReconstructor()
        self.state["reconstructor"].setup()
        return self.runner.return_success({
            "graph": graph
        })

    def add_extrude_by_face(self, data):
        """Add an extrude from target faces"""
        # Check we have set a target
        if "reconstructor" not in self.state:
            return self.runner.return_failure("Target not set")
        if self.design.rootComponent.bRepBodies.count == 0:
            return self.runner.return_failure("Target not set")
        # Start face data checks
        start_face = self.state["reconstructor"].get_face_from_uuid(data["start_face"])
        if start_face is None:
            return self.runner.return_failure("Start face not in target")
        if start_face.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            return self.runner.return_failure("Start face is not a plane")
        # End face data checks
        end_face = self.state["reconstructor"].get_face_from_uuid(data["end_face"])
        if end_face is None:
            return self.runner.return_failure("End face not in target")
        if end_face.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            return self.runner.return_failure("End face is not a plane")
        # End face geometric checks
        if not end_face.geometry.isParallelToPlane(start_face.geometry):
            return self.runner.return_failure("End face is not parallel to start face")
        if end_face.geometry.isCoPlanarTo(start_face.geometry):
            return self.runner.return_failure("End face is coplanar to start face")
        operation = deserialize.feature_operations(data["operation"])
        if operation is None:
            return self.runner.return_failure("Extrude operation is not valid")
        # Add the extrude
        extrude = self.state["reconstructor"].add_extrude(
            start_face,
            end_face,
            operation
        )
        # If this is the first extrude, we initialize regraph
        if "regraph" not in self.state:
            self.state["regraph"] = Regraph(logger=self.logger, mode="PerFace")
        # Generate the graph from the reconstruction component
        graph = self.state["regraph"].generate_from_bodies(
            self.state["reconstructor"].reconstruction.bRepBodies
        )
        


