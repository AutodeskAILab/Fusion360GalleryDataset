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
        data_file, error = self.check_file(data, [".step", ".stp", ".smt"])
        suffix = data_file.suffix
        if error is not None:
            return self.runner.return_failure(error)
        # self.design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        # Create the file locally
        temp_file = self.get_temp_file(data["file"])
        with open(temp_file, "w") as f:
            f.write(data["file_data"])
        # We clear the design before importing
        self.runner.clear()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Switch to direct design mode for performance
        self.design.designType = adsk.fusion.DesignTypes.DirectDesignType
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
        self.target = imported_designs[0]
        # Store references to the target bodies
        self.state["target_bodies"] = []
        # Rename the bodies with Target-*
        for body in self.target.bRepBodies:
            body.name = f"Target-{body.name}"
            self.state["target_bodies"].append(body)
        adsk.doEvents()
        regraph = Regraph(logger=self.logger, mode="PerFace")
        self.state["target_graph"] = regraph.generate_from_bodies(self.state["target_bodies"])
        temp_file.unlink()
        # Setup the reconstructor
        self.state["reconstructor"] = RegraphReconstructor(
            target_component=self.target)
        self.state["reconstructor"].setup()
        return self.runner.return_success({
            "graph": self.state["target_graph"]
        })

    def revert_to_target(self):
        """Reverts to the target design, removing all reconstruction"""
        if "target_graph" not in self.state:
            return self.runner.return_failure("Target not set")
        if "reconstructor" not in self.state:
            return self.runner.return_failure("Target not set")
        self.state["reconstructor"].reset()
        if "regraph" in self.state:
            del self.state["regraph"]
        return self.runner.return_success({
            "graph": self.state["target_graph"]
        })

    def add_extrude_by_target_face(self, data):
        """Add an extrude between two faces of the target"""
        # Check we have set a target
        if "reconstructor" not in self.state:
            return self.runner.return_failure("Target not set")
        action, error = self.__check_extrude_actions(
            data["start_face"], data["end_face"], data["operation"])
        if error is not None:
            return self.runner.return_failure(error)
        # Add the extrude
        extrude = self.state["reconstructor"].add_extrude(
            action["start_face"],
            action["end_face"],
            action["operation"]
        )
        adsk.doEvents()
        return self.__return_graph_iou()

    def add_extrudes_by_target_face(self, data):
        """Executes multiple extrude operations,
            between two faces of the target, in sequence"""
        # Check we have set a target
        if "reconstructor" not in self.state:
            return self.runner.return_failure("Target not set")
        # Revert if requested
        if "revert" in data:
            if data["revert"]:
                self.revert_to_target()
        # Loop over the extrude actions and execute them
        actions = data["actions"]
        for action in actions:
            valid_action, error = self.__check_extrude_actions(
                action["start_face"], action["end_face"], action["operation"])
            if error is not None:
                return self.runner.return_failure(error)
            # Add the extrude
            extrude = self.state["reconstructor"].add_extrude(
                valid_action["start_face"],
                valid_action["end_face"],
                valid_action["operation"]
            )
        adsk.doEvents()
        return self.__return_graph_iou()

    def __check_extrude_actions(self, start_face_uuid, end_face_uuid, operation_data):
        """Check the extrude actions are valid"""
        result = {
            "start_face": None,
            "end_face": None,
            "operation": None
        }
        # Start face data checks
        start_face = self.state["reconstructor"].get_face_from_uuid(start_face_uuid)
        if start_face is None:
            return result, "Start face not in target"
        start_face_geometry = start_face.geometry
        if start_face_geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            return result, "Start face is not a plane"
        # End face data checks
        end_face = self.state["reconstructor"].get_face_from_uuid(end_face_uuid)
        if end_face is None:
            return result, "End face not in target"
        end_face_geometry = end_face.geometry
        if end_face_geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            return result, "End face is not a plane"
        # End face geometric checks
        if not end_face_geometry.isParallelToPlane(start_face_geometry):
            return result, "End face is not parallel to start face"
        if end_face_geometry.isCoPlanarTo(start_face_geometry):
            return result, "End face is coplanar to start face"
        operation = deserialize.feature_operations(operation_data)
        if operation is None:
            return result, "Extrude operation is not valid"
        result["start_face"] = start_face
        result["end_face"] = end_face
        result["operation"] = operation
        return result, None

    def __return_graph_iou(self):
        """Return the graph and IoU"""
        # If this is the first extrude, we initialize regraph
        if "regraph" not in self.state:
            self.state["regraph"] = Regraph(logger=self.logger, mode="PerFace")
        # Generate the graph from the reconstruction component
        graph = self.state["regraph"].generate_from_bodies(
            self.state["reconstructor"].reconstruction.bRepBodies
        )
        # Calculate the IoU
        iou = geometry.intersection_over_union(
            self.target,
            self.state["reconstructor"].reconstruction
        )
        if iou is None:
            logger.log("Warning! IoU calculation returned None")
        return self.runner.return_success({
            "graph": graph,
            "iou": iou
        })
