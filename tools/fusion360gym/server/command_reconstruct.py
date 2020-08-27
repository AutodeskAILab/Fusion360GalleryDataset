"""

Reconstruct from a json design

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
import match
from sketch_extrude_importer import SketchExtrudeImporter


class CommandReconstruct(CommandBase):

    def reconstruct(self, data):
        """Reconstruct a design from the provided json data"""
        importer = SketchExtrudeImporter(data)
        importer.reconstruct()
        return self.runner.return_success()

    def reconstruct_sketch(self, data):
        if (data is None or "json_data" not in data or
           "sketch_name" not in data):
            return self.runner.return_failure("reconstruct_sketch data not specified")
        json_data = data["json_data"]
        sketch_name = data["sketch_name"]
        if json_data is None:
            return self.runner.return_failure("reconstruct json not found")
        if sketch_name is None:
            return self.runner.return_failure("reconstruct sketch not found")
        entities = json_data["entities"]
        if entities is None:
            return self.runner.return_failure("reconstruct entities not found")
        # retrieve sketch id from sketch name
        sketch_uuid = None
        for entity in entities:
            if entities[entity]["name"] == sketch_name:
                sketch_uuid = entity
        if sketch_uuid is None:
            return self.runner.return_failure("reconstruct sketch id doesn't exist")
        # Optional sketch plane
        sketch_plane = None
        if "sketch_plane" in data:
            sketch_plane = match.sketch_plane(data["sketch_plane"])
        # Optional transform
        scale = None
        translate = None
        if "scale" in data:
            scale = deserialize.vector3d(data["scale"])
        if "translate" in data:
            translate = deserialize.vector3d(data["translate"])
        transform = None
        if scale is not None or translate is not None or sketch_plane is not None:
            # Get the transform or an identity matrix
            transform = self.__get_scale_translation_matrix(scale, translate)
        # Create the sketch
        importer = SketchExtrudeImporter(json_data)
        sketch = importer.reconstruct_sketch(sketch_uuid, sketch_plane=sketch_plane, transform=transform)
        # Serialize the data and return
        profile_data = serialize.sketch_profiles(sketch.profiles)
        return self.runner.return_success({
            "sketch_id": sketch_uuid,
            "sketch_name": sketch.name,
            "profiles": profile_data
        })

    def __get_scale_translation_matrix(self, scale=None, translation=None):
        """Get a transformation matrix that scales and translates"""
        transform = adsk.core.Matrix3D.create()
        if scale is not None:
            # We don't have a Matrix3D.scale() function
            # so we set this manually
            transform.setWithArray([
                scale.x, 0, 0, 0,
                0, scale.y, 0, 0,
                0, 0, scale.z, 0,
                0, 0, 0, 1
            ])
        if translation is not None:
            # We do have a shortcut to set the translation
            transform.translation = translation
        return transform
