"""

Base Command Class

"""

import adsk.core
import os
import sys
from pathlib import Path
import tempfile
import importlib

# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

import serialize
import geometry
import regraph
importlib.reload(serialize)
importlib.reload(geometry)
importlib.reload(regraph)
from regraph import Regraph


class CommandBase():

    def __init__(self, runner, design_state):
        self.runner = runner
        self.design_state = design_state
        self.logger = None
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.state = {}

    def set_logger(self, logger):
        self.logger = logger

    def clear(self):
        """Clear the state"""
        self.state = {}
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)

    def get_temp_file(self, file, dest_dir=None):
        """Return a file with a given name in a temp directory"""
        if dest_dir is None:
            dest_dir = Path(tempfile.mkdtemp())
        # Make the dir if we need to
        if not dest_dir.exists():
            dest_dir.mkdir(parents=True)

        temp_file = dest_dir / file
        return temp_file

    def check_file(self, data, valid_formats):
        """Check that the data has a valid file value"""
        if data is None or "file" not in data:
            return None, "file not specified"
        data_file = Path(data["file"])
        if data_file.suffix not in valid_formats:
            return None, "invalid file extension specified"
        return data_file, None

    def return_extrude_data(self, extrude):
        """Return data from an extrude operation"""
        regraph = Regraph(
            reconstruction=self.design_state.reconstruction,
            logger=self.logger,
            mode="PerFace",
            use_temp_id=True,
            include_labels=False
        )
        return_data = {}
        # Info on the extrude
        return_data["extrude"] = serialize.extrude_feature_brep(extrude)
        # Generate the graph from the reconstruction component
        return_data["graph"] = regraph.generate_from_bodies(
            self.design_state.reconstruction.bRepBodies
        )
        # Calculate the IoU
        if self.design_state.target is not None:
            return_data["iou"] = geometry.intersection_over_union(
                self.design_state.target,
                self.design_state.reconstruction
            )
            if return_data["iou"] is None:
                self.logger.log("Warning! IoU calculation returned None")
        # Bounding box of the reconstruction component
        bbox = geometry.get_bounding_box(self.design_state.reconstruction)
        return_data["bounding_box"] = serialize.bounding_box3d(bbox)
        return self.runner.return_success(return_data)
