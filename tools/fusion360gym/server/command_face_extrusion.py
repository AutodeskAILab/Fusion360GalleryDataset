"""

Face Extrusion Reconstruction

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
import serialize
import geometry
import regraph
import face_reconstructor
importlib.reload(deserialize)
importlib.reload(serialize)
importlib.reload(geometry)
importlib.reload(regraph)
importlib.reload(face_reconstructor)
from regraph import Regraph
from face_reconstructor import FaceReconstructor


class CommandFaceExtrusion(CommandBase):

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
        # This also clears the local state
        self.design_state.clear()
        self.design_state.set_target(temp_file)

        # Use temp_ids
        regraph_graph = Regraph(
            reconstruction=self.design_state.reconstruction,
            logger=self.logger,
            mode="PerFace",
            use_temp_id=True,
            include_labels=False
        )
        self.state["target_graph"] = regraph_graph.generate_from_bodies(
            self.design_state.target.bRepBodies
        )
        bbox = geometry.get_bounding_box(self.design_state.target)
        self.state["target_bounding_box"] = serialize.bounding_box3d(bbox)
        temp_file.unlink()
        # Setup the reconstructor
        self.state["reconstructor"] = FaceReconstructor(
            target=self.design_state.target,
            reconstruction=self.design_state.reconstruction
        )
        return self.runner.return_success({
            "graph": self.state["target_graph"],
            "bounding_box": self.state["target_bounding_box"]
        })

    def revert_to_target(self):
        """Reverts to the target design, removing all reconstruction"""
        if "target_graph" not in self.state:
            return self.runner.return_failure("Target not set")
        if "reconstructor" not in self.state:
            return self.runner.return_failure("Target not set")
        self.__clear_reconstruction()
        return self.runner.return_success({
            "graph": self.state["target_graph"],
            "bounding_box": self.state["target_bounding_box"]
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
        return self.return_extrude_data(extrude)

    def add_extrudes_by_target_face(self, data):
        """Executes multiple extrude operations,
            between two faces of the target, in sequence"""
        # Check we have set a target
        if "reconstructor" not in self.state:
            return self.runner.return_failure("Target not set")
        # Revert if requested
        if "revert" in data:
            if data["revert"]:
                self.__clear_reconstruction()
        # Loop over the extrude actions and execute them
        actions = data["actions"]
        extrude = None
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
        return self.return_extrude_data(extrude)

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

    def __clear_reconstruction(self):
        self.design_state.clear_reconstruction()
        # Update the reference to the new reconstruction component
        self.state["reconstructor"].set_reconstruction_component(
            self.design_state.reconstruction
        )
        if "regraph" in self.state:
            del self.state["regraph"]
