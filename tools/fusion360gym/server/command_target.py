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

import deserialize
import geometry
import regraph
importlib.reload(deserialize)
importlib.reload(geometry)
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
        existing_document = self.app.activeDocument
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
        # Import to a new document so the bodies land in the rootComponent
        new_document = self.app.importManager.importToNewDocument(import_options)
        if new_document is None:
            return self.runner.return_failure(
                f"Error importing target {suffix} file")
        existing_document.close(False)
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        # Store references to the target bodies
        self.state["target_bodies"] = []
        # Rename the bodies with Target-*
        for body in self.design.rootComponent.bRepBodies:
            body.name = f"Target-{body.name}"
            self.state["target_bodies"].append(body)
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

    def add_extrude_by_target_face(self, data):
        """Add an extrude by target faces"""
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
        adsk.doEvents()
        # If this is the first extrude, we initialize regraph
        if "regraph" not in self.state:
            self.state["regraph"] = Regraph(logger=self.logger, mode="PerFace")
        # Generate the graph from the reconstruction component
        graph = self.state["regraph"].generate_from_bodies(
            self.state["reconstructor"].reconstruction.bRepBodies
        )
        # Calculate the IoU
        iou = geometry.intersection_over_union(
            self.design.rootComponent,
            self.state["reconstructor"].reconstruction
        )
        if iou is None:
            logger.log("Warning! IoU calculation returned None")
        return self.runner.return_success({
            "graph": graph,
            "iou": iou
        })
