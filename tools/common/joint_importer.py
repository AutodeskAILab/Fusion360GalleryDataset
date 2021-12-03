import adsk.core
import adsk.fusion
import traceback
import json
import os
import sys
from pathlib import Path
import importlib
import random
import time
import deserialize


class JointImporter():
    """Joint Importer
        Takes a joint json file and reconstructs the joint"""

    def __init__(self, json_file, json_data=None):
        self.json_file = json_file
        self.json_data = json_data
        # References to the Fusion design
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)

    def reconstruct(self, joint_index=0, transform_map=None, transform_only=False):
        """Reconstruct the joint from the json file"""
        if self.json_data is None:
            with open(self.json_file, "r", encoding="utf8") as f:
                self.json_data = json.load(f)
        self.app.activeDocument.name = self.json_file.stem
        joint_data = self.json_data["joints"][joint_index]
        self.design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        smt_1, smt_2 = self.get_smt_files(joint_data)
        occ_1, occ_2 = self.import_smt_files(smt_1, smt_2, transform_map)

        if transform_only:
            transform1_data = joint_data["geometry_or_origin_one"]["transform"]
            transform2_data = joint_data["geometry_or_origin_two"]["transform"]
            transform1 = deserialize.matrix3d(transform1_data)
            transform2 = deserialize.matrix3d(transform2_data)
            occ_1.transform = transform1
            occ_2.transform = transform2
        else:
            return self.create_joint(joint_data, occ_1, occ_2)

    def get_smt_files(self, data):
        """Get the smt files used by the joint"""
        smt_name_1 = data["geometry_or_origin_one"]["entity_one"]["body"]
        smt_name_2 = data["geometry_or_origin_two"]["entity_one"]["body"]
        smt_1 = self.json_file.parent / f"{smt_name_1}.smt"
        smt_2 = self.json_file.parent / f"{smt_name_2}.smt"
        return smt_1, smt_2

    def import_smt_files(self, smt_1, smt_2, transform_map=None):
        """Import two smt files as new occurrences"""
        transform1 = None
        transform2 = None
        if transform_map is not None:
            if smt_1.stem in transform_map:
                transform1 = transform_map[smt_1.stem]
            if smt_2.stem in transform_map:
                transform2 = transform_map[smt_2.stem]
        occ_1 = self.import_smt_file(smt_1, transform1)
        occ_2 = self.import_smt_file(smt_2, transform2)
        return occ_1, occ_2

    def import_smt_file(self, smt_file, transform=None):
        """Import an smt to a new occurrence"""
        if transform is None:
            transform = adsk.core.Matrix3D.create()
        #
        # # Using temp brep manager requires direct design mode
        # occ = self.design.rootComponent.occurrences.addNewComponent(transform)
        # occ.component.name = smt_file.stem
        # occ_comp = occ.component
        # temp_brep_mgr = adsk.fusion.TemporaryBRepManager.get()
        # breps = temp_brep_mgr.createFromFile(str(smt_file.resolve()))
        # if len(breps) == 1:
        #     brep = breps[0]
        # else:
        #     raise Exception(f"{len(breps)} entities present in {smt_file} file")
        # occ_comp.bRepBodies.add(brep)
        # return occ
        #
        # Using import manager for parametric design mode
        smt_options = self.app.importManager.createSMTImportOptions(
            str(smt_file.resolve())
        )
        smt_options.isViewFit = False
        components = self.app.importManager.importToTarget2(
            smt_options,
            self.design.rootComponent
        )
        if len(components) != 1:
            raise Exception(f"{len(components)} entities present in {smt_file} file")
        components[0].transform = transform
        return components[0]

    def get_entities(self, data, occ_1, occ_2):
        """Get the entities use to setup the joint"""
        index_1 = data["geometry_or_origin_one"]["entity_one"]["index"]
        index_2 = data["geometry_or_origin_two"]["entity_one"]["index"]
        type_1 = data["geometry_or_origin_one"]["entity_one"]["type"]
        type_2 = data["geometry_or_origin_two"]["entity_one"]["type"]
        ent_1 = self.get_entity(index_1, type_1, occ_1)
        ent_2 = self.get_entity(index_2, type_2, occ_2)
        return ent_1, ent_2

    def get_entity(self, index, entity_type, occ):
        """Get an entity from an occurrence"""
        if entity_type == "BRepEdge":
            return occ.bRepBodies[0].edges[index]
        elif entity_type == "BRepFace":
            return occ.bRepBodies[0].faces[index]
        else:
            raise Exception("Unsupported entity type")

    def create_joint(self, data, occ_1, occ_2, retry=False):
        """Create a joint"""
        # Get the entities first
        ent_1, ent_2 = self.get_entities(data, occ_1, occ_2)
        self.design.rootComponent.isJointsFolderLightBulbOn = False
        current_joints = self.design.rootComponent.joints
        geo_one_data = data["geometry_or_origin_one"]
        geo_two_data = data["geometry_or_origin_two"]
        geo_one = self.create_joint_geometry(geo_one_data, ent_1)
        geo_two = self.create_joint_geometry(geo_two_data, ent_2)
        joint_input = current_joints.createInput(geo_one, geo_two)
        # Set the joint input
        joint_input.angle = adsk.core.ValueInput.createByReal(data["angle"]["value"])
        joint_input.offset = adsk.core.ValueInput.createByReal(data["offset"]["value"])
        joint_input.isFlipped = data["is_flipped"]
        self.set_joint_motion(joint_input, data["joint_motion"])
        joint = current_joints.add(joint_input)
        joint.name = data["name"]
        return joint

    def get_key_point_type(self, key_point):
        """Get the key point type from a string"""
        if key_point == "CenterKeyPoint":
            return adsk.fusion.JointKeyPointTypes.CenterKeyPoint
        elif key_point == "EndKeyPoint":
            return adsk.fusion.JointKeyPointTypes.EndKeyPoint
        elif key_point == "MiddleKeyPoint":
            return adsk.fusion.JointKeyPointTypes.MiddleKeyPoint
        elif key_point == "StartKeyPoint":
            return adsk.fusion.JointKeyPointTypes.StartKeyPoint
        else:
            raise Exception(f"Unknown keyPointType type: {key_point}")

    def get_joint_direction(self, joint_direction):
        """Get the joint direction from a string"""
        if joint_direction == "XAxisJointDirection":
            return adsk.fusion.JointDirections.XAxisJointDirection
        elif joint_direction == "YAxisJointDirection":
            return adsk.fusion.JointDirections.YAxisJointDirection
        elif joint_direction == "ZAxisJointDirection":
            return adsk.fusion.JointDirections.ZAxisJointDirection
        elif joint_direction == "CustomJointDirection":
            return adsk.fusion.JointDirections.CustomJointDirection
        else:
            raise Exception(f"Unknown JointDirections type: {joint_direction}")

    def create_joint_geometry(self, geo_data, brep_entity):
        """Create joint geometry object"""
        entity_one = geo_data["entity_one"]
        entity_type = entity_one["type"]
        joint_key_point_type = self.get_key_point_type(geo_data["key_point_type"])
        if "BRepFace" == entity_type:
            if brep_entity.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
                geo = adsk.fusion.JointGeometry.createByPlanarFace(brep_entity, None, joint_key_point_type)
            else:
                geo = adsk.fusion.JointGeometry.createByNonPlanarFace(brep_entity, joint_key_point_type)
        elif "BRepEdge" == entity_type:
            geo = adsk.fusion.JointGeometry.createByCurve(brep_entity, joint_key_point_type)
        else:
            raise Exception(f"Entity type : {entity_type} not supported")
        return geo

    def set_joint_motion(self, joint_input, joint_motion_data):
        """Set the joint motion of the rebuilt joint"""
        joint_type = joint_motion_data["joint_type"]
        if joint_type == "PlanarJointType":
            self.set_planar_joint_motion(joint_input, joint_motion_data)
        elif joint_type == "BallJointType":
            self.set_ball_joint_motion(joint_input, joint_motion_data)
        elif joint_type == "RigidJointType":
            self.set_rigid_joint_motion(joint_input, joint_motion_data)
        elif joint_type == "PinSlotJointType":
            self.set_pin_slot_joint_motion(joint_input, joint_motion_data)
        elif joint_type == "RevoluteJointType":
            self.set_revolute_joint_motion(joint_input, joint_motion_data) 
        elif joint_type == "SliderJointType":
            self.set_slider_joint_motion(joint_input, joint_motion_data)
        elif joint_type == "CylindricalJointType":
            self.set_cylindrical_joint_motion(joint_input, joint_motion_data)
        else:
            raise Exception("Joint motion type not supported")
        # Set the joint motion limits
        self.set_joint_motion_limits(joint_input.jointMotion, joint_motion_data)

    def set_planar_joint_motion(self, joint_input, joint_motion_data):
        """Set the planar joint motion of the rebuilt joint"""
        normal_direction = self.get_joint_direction(joint_motion_data["normal_direction"])
        if normal_direction == adsk.fusion.JointDirections.CustomJointDirection:
            raise Exception("Custom joint motion entities not supported")
        else:
            joint_input.setAsPlanarJointMotion(normal_direction)

    def set_ball_joint_motion(self, joint_input, joint_motion_data):
        """Set the ball joint motion of the rebuilt joint"""
        pitch_direction = self.get_joint_direction(joint_motion_data["pitch_direction"])
        yaw_direction = self.get_joint_direction(joint_motion_data["yaw_direction"])
        custom_pitch = pitch_direction == adsk.fusion.JointDirections.CustomJointDirection
        custom_yaw = yaw_direction == adsk.fusion.JointDirections.CustomJointDirection
        if custom_pitch or custom_yaw:
            raise Exception("Custom joint motion entities not supported")
        else:
            joint_input.setAsBallJointMotion(pitch_direction, yaw_direction)

    def set_rigid_joint_motion(self, joint_input, joint_motion_data):
        """Set the rigid joint motion of the rebuilt joint"""
        joint_input.setAsRigidJointMotion()

    def set_pin_slot_joint_motion(self, joint_input, joint_motion_data):
        """Set the pin slot joint motion of the rebuilt joint"""
        rotation_axis = self.get_joint_direction(joint_motion_data["rotation_axis"])
        slide_direction = self.get_joint_direction(joint_motion_data["slide_direction"])
        custom_rotation = rotation_axis == adsk.fusion.JointDirections.CustomJointDirection
        custom_slide = slide_direction == adsk.fusion.JointDirections.CustomJointDirection
        if custom_rotation or custom_slide:
            raise Exception("Custom joint motion entities not supported")
        else:
            joint_input.setAsPinSlotJointMotion(rotation_axis, slide_direction)

    def set_revolute_joint_motion(self, joint_input, joint_motion_data):
        """Set the planar joint motion of the rebuilt joint"""
        rotation_axis = self.get_joint_direction(joint_motion_data["rotation_axis"])
        if rotation_axis == adsk.fusion.JointDirections.CustomJointDirection:
            raise Exception("Custom joint motion entities not supported")
        else:
            joint_input.setAsRevoluteJointMotion(rotation_axis)

    def set_slider_joint_motion(self, joint_input, joint_motion_data):
        """Set the slider joint motion of the rebuilt joint"""
        slide_direction = self.get_joint_direction(joint_motion_data["slide_direction"])
        if slide_direction == adsk.fusion.JointDirections.CustomJointDirection:
            raise Exception("Custom joint motion entities not supported")
        else:
            joint_input.setAsSliderJointMotion(slide_direction)

    def set_cylindrical_joint_motion(self, joint_input, joint_motion_data):
        """Set the cylindrical joint motion of the rebuilt joint"""
        rotation_axis = self.get_joint_direction(joint_motion_data["rotation_axis"])
        if rotation_axis == adsk.fusion.JointDirections.CustomJointDirection:
            raise Exception("Custom joint motion entities not supported")
        else:
            joint_input.setAsCylindricalJointMotion(rotation_axis)

    def set_limits(self, limits, limits_data):
        """Set the joint motion limits"""
        limits.isMinimumValueEnabled = limits_data["is_minimum_value_enabled"]
        limits.minimumValue = limits_data["minimum_value"]
        limits.isMaximumValueEnabled = limits_data["is_maximum_value_enabled"]
        limits.maximumValue = limits_data["maximum_value"]
        limits.isRestValueEnabled = limits_data["is_rest_value_enabled"]
        limits.restValue = limits_data["rest_value"]

    def set_joint_motion_limits(self, joint_motion, joint_motion_data):
        """Set the joint motion limits"""
        try:
            if "slide_limits" in joint_motion_data:
                limits = joint_motion.slideLimits
                self.set_limits(limits, joint_motion_data["slide_limits"])
            if "primary_slide_limits" in joint_motion_data:
                limits = joint_motion.primarySlideLimits
                self.set_limits(limits, joint_motion_data["primary_slide_limits"])
            if "rotation_limits" in joint_motion_data:
                limits = joint_motion.rotationLimits
                self.set_limits(limits, joint_motion_data["rotation_limits"])
            if "pitch_limits" in joint_motion_data:
                limits = joint_motion.pitchLimits
                self.set_limits(limits, joint_motion_data["pitch_limits"])
            if "roll_limits" in joint_motion_data:
                limits = joint_motion.rollLimits
                self.set_limits(limits, joint_motion_data["roll_limits"])
            if "yaw_limits" in joint_motion_data:
                limits = joint_motion.yawLimits
                self.set_limits(limits, joint_motion_data["yaw_limits"])
        except Exception as ex:
            pass
