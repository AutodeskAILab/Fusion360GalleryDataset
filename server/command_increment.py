"""

Incremental geometry construction commands

"""

import adsk.core
import adsk.fusion

from . import name
from . import match
from . import deserialize
from . import serialize


class CommandIncrement():

    def __init__(self, runner):
        self.runner = runner
        self.logger = None
        self.app = adsk.core.Application.get()

    def set_logger(self, logger):
        self.logger = logger

    def add_sketch(self, data):
        """Add a sketch to the existing design"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if data is None or "sketch_plane" not in data:
            return self.runner.return_failure("sketch_plane not specified")
        sketch_plane = match.sketch_plane(data["sketch_plane"])
        if sketch_plane is None:
            return self.runner.return_failure("sketch_plane could not be found")
        sketches = design.rootComponent.sketches
        sketch = sketches.addWithoutEdges(sketch_plane)
        sketch_uuid = name.set_uuid(sketch)
        return self.runner.return_success({
            "sketch_id": sketch_uuid,
            "sketch_name": sketch.name
        })

    def add_line(self, data):
        """Add a line to an existing sketch"""
        if (data is None or "sketch_name" not in data or
                "pt1" not in data or "pt2" not in data):
            return self.runner.return_failure("add_line data not specified")
        sketch = match.sketch_by_name(data["sketch_name"])
        if sketch is None:
            return self.runner.return_failure("sketch not found")
        sketch_uuid = name.get_uuid(sketch)
        start_point = deserialize.point3d(data["pt1"])
        end_point = deserialize.point3d(data["pt2"])
        if "transform" in data:
            # For mapping Fusion exported data back correctly
            xform = deserialize.matrix3d(data["transform"])
            sketch_transform = sketch.transform
            sketch_transform.invert()
            xform.transformBy(sketch_transform)
            start_point.transformBy(xform)
            end_point.transformBy(xform)

        line = sketch.sketchCurves.sketchLines.addByTwoPoints(start_point, end_point)
        curve_uuid = name.set_uuid(line)
        name.set_uuids_for_sketch(sketch)
        profile_data = serialize.sketch_profiles(sketch.profiles)
        return self.runner.return_success({
            "sketch_id": sketch_uuid,
            "sketch_name": sketch.name,
            "curve_id": curve_uuid,
            "profiles": profile_data
        })

    def add_extrude(self, data):
        """Add an extrude feature from a sketch"""
        if (data is None or "sketch_name" not in data or
                "profile_id" not in data or "distance" not in data or
                "operation" not in data):
            return self.runner.return_failure("add_extrude data not specified")
        sketch = match.sketch_by_name(data["sketch_name"])
        if sketch is None:
            return self.runner.return_failure("extrude sketch not found")
        profile = match.sketch_profile_by_id(data["profile_id"], [sketch])
        if profile is None:
            return self.runner.return_failure("extrude sketch profile not found")
        operation = self.__get_extrude_operation(data["operation"])
        if operation is None:
            return self.runner.return_failure("extrude operation not found")

        # Make the extrude
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        extrudes = design.rootComponent.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, operation)
        distance = adsk.core.ValueInput.createByReal(data["distance"])
        extent_distance = adsk.fusion.DistanceExtentDefinition.create(distance)
        extrude_input.setOneSideExtent(extent_distance, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        extrude_feature = extrudes.add(extrude_input)
        # Serialize the data and return
        extrude_feature_data = serialize.extrude_feature_brep(extrude_feature)
        return self.runner.return_success(extrude_feature_data)

    def __get_extrude_operation(self, operation):
        """Return an appropriate extrude operation"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Check that the operation is going to work
        body_count = 0
        for component in design.allComponents:
            body_count += component.bRepBodies.count
        # If there are no other bodies, we have to make a new body
        if body_count == 0:
            operation = "NewBodyFeatureOperation"
        return deserialize.feature_operations(operation)
