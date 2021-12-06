import adsk.core
import adsk.fusion
import json
import glob
from pathlib import Path
import deserialize

class AssemblyImporterException(Exception):
    """Raised when something goes wrong with AssemblyImporter"""
    pass

class AssemblyImporter():
    """Reconstruct a model based on assembly json and smt files"""

    def __init__(self, assembly_file):
        """
        Assembly Importer Constructor receives one mandatory parameter
        Parameters:
        assembly_file  - Path - path type from pathlib library 
        """
        self.assembly_file = assembly_file
        self.app = adsk.core.Application.get()
        product = self.app.activeProduct
        self.design = adsk.fusion.Design.cast(product)
        self.design.designType = adsk.fusion.DesignTypes.DirectDesignType
        self.app.activeDocument.name = self.assembly_file.parent.stem
        # memoize vars ----------------->
        self.body_proxy_id_map = {}
        self.joint_origin_id_map = {}
        # hash map for quick components retrieval. 
        self.comp_id_map = {}
        # hash map for quick occurrences retrieval. 
        self.occ_id_map = {}
        # we will have a record on occurrences affected by joints definition
        # it is possible that its transform changed by the joint
        self.occurrences_affected = {}
        # memoize vars ----------------->
        if not assembly_file.exists():
            raise AssemblyImporterException("Assembly file is missing")
        with open(assembly_file, "r", encoding="utf-8") as f:
            self.assembly_data = json.load(f)
    
    def get_uuid(self, entity):
        uuid_att = entity.attributes.itemByName("Dataset", "uuid")
        if uuid_att is not None:
            return uuid_att.value
        else:
            return None

    def set_uuid(self, entity, unique_id):
        uuid_att = entity.attributes.itemByName("Dataset", "uuid")
        if uuid_att is None:
            entity.attributes.add("Dataset", "uuid", unique_id)

    def reconstruct(self):
        """
        Starts model recostruction using as a reference
        the path of self.assembly_file
        """
        derivatives_folder = self.assembly_file.parent
        derivatives_path_files = [Path(f) for f in glob.glob(str(derivatives_folder) + "**/*.smt")]
        if len(derivatives_path_files) == 0:
            raise AssemblyImporterException("smt files are missing")
        root_key = self.get_root_key()
        root_bodies = self.assembly_data["root"].get("bodies", {})
        root_component = self.design.rootComponent
        self.set_uuid(root_component, root_key)
        self.comp_id_map[root_key] = root_component
        # First reconstruct the bodies that are located at root component level
        self.reconstruct_bodies_at_comp_level(root_component, derivatives_path_files, root_bodies)

        self.start_tree_reconstruction(derivatives_path_files,
                                        root_component, 
                                        self.assembly_data["tree"]["root"], 
                                        parent_occ=None,
                                        occ_branch=[],
                                        components_reconstructed={})

        # Joints are part of parametric design
        self.design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        self.create_joints()
        self.verify_occurrences_transformation()

    def get_root_key(self):
        for key, value in self.assembly_data["components"].items():
            if value["name"] == "root":
                return key

    def import_single_brep_to_target(self, temp_brep_mgr, breps):
        """
        Union an array of breps using a boolean operation
        """
        new_body = temp_brep_mgr.copy(breps[0])
        for i, body in enumerate(breps):
            if i == 0:
                continue
            temp_brep_mgr.booleanOperation(new_body, body, adsk.fusion.BooleanTypes.UnionBooleanType)
        return new_body

    def import_smt_to_target(self, target, smt_file, body_key, body_value):
        """
        Import smt first as a temporary brep and then add it to the component
        The createFromFile function may return more than one brep, meaning that 
        one smt file could contain two or more breps.
        """
        temp_brep_mgr = adsk.fusion.TemporaryBRepManager.get()
        breps = temp_brep_mgr.createFromFile(str(smt_file))
        if len(breps) > 1:
            # turn multiple breps into a single one by joining them
            brep = self.import_single_brep_to_target(temp_brep_mgr, breps)
        elif len(breps) == 1:
            brep = breps[0]
        else:
            raise Exception(f'No Bodies present in {smt_file} file')
        new_brep = target.bRepBodies.add(brep)
        # use assembly file information to set properties in the newly body added
        new_brep.isLightBulbOn = body_value["is_visible"]
        self.set_uuid(new_brep, body_key)

    def reconstruct_bodies_at_comp_level(self, component, derivatives_path_files, bodies_to_import):
        """
        Import all smt bodies that belongs to that component
        """
        for body_k, body_value in bodies_to_import.items():
            body_smt_file = \
                next((file for file in derivatives_path_files
                      if body_k in file.stem), None)
            if body_smt_file is None:
                print(f"{body_k} is missing, reconstruction will be incomplete.")
                continue
            self.import_smt_to_target(component, body_smt_file, body_k, body_value)

    def get_occ_by_name(self, occ_name):
        for occ in self.design.rootComponent.allOccurrences:
            if occ.name == occ_name:
                return occ

    def get_transform_by_name(self, child_occ_tree, name):
        for occ_key, tree_value in child_occ_tree.items():
            occurrence_properties = self.assembly_data["occurrences"][occ_key]
            # occurrence name usually have this format -> <component name>:<number>
            # if occurrence_properties["name"] = "Low Cap v8:1" then _name="Low Cap v8"
            _name = occurrence_properties["name"][:occurrence_properties["name"].find(":")]
            if _name == name and "used" not in occurrence_properties:
                occurrence_properties["used"] = True
                return (occ_key, occurrence_properties["is_visible"],
                        occurrence_properties["transform"], tree_value)

    def update_child_occ(self, child_occurrences, child_occ_tree, branch_register):
        try:
            for child in child_occurrences:
                # occurrence name usually have this format -> <component name>:<number>
                # if child.name = "Low Cap v8:1" then child_name="Low Cap v8"
                child_name = child.name[:child.name.find(":")]
                identity_transform = adsk.core.Matrix3D.create()
                occ_key, is_visible, transform, new_child_occ_tree = self.get_transform_by_name(child_occ_tree, child_name)
                fusion_transform = deserialize.matrix3d(transform)
                self.set_uuid(child, occ_key)
                child.transform = identity_transform
                child.isLightBulbOn = is_visible
                branch_register.append({
                    "occurrence": child,
                    "transform": fusion_transform
                })
                if child.childOccurrences.count > 0:
                    self.update_child_occ(
                        child.childOccurrences, new_child_occ_tree, branch_register)
        except Exception as ex:
            print(ex)

    def apply_transformations(self, occ_branch):
        """
        Apply tranformation from bottom to top of the occurrence tree
        """
        for occ_dict in reversed(occ_branch):
            occ = occ_dict["occurrence"]
            transform = occ_dict["transform"]
            occ.transform = transform

    def start_tree_reconstruction(self, derivatives_path_files, parent_comp,
              occ_tree, parent_occ, occ_branch, components_reconstructed):
        """
        Start reconstruction, this is a recursive function
        to reconstruct occurrence tree 
        """
        for occ_key, occ_value in occ_tree.items():
            occurrence_properties = self.assembly_data["occurrences"][occ_key]
            transform = occurrence_properties["transform"]
            fusion_transform = deserialize.matrix3d(transform)
            # we stored components that are reconstructed already in a variable
            # if the component was reconstructed already we use it to create the new occurrence
            if occurrence_properties["component"] in components_reconstructed:
                component = components_reconstructed[occurrence_properties["component"]]
                # This branch register is to store the key-pair of occurrence and
                # transformation . we'll going to use this info once all the pieces
                # of the component/occurrences are in place. we apply transformations
                # from childs to parent due to a bug found in nested occurrence rotation.
                branch_register = []
                transform = adsk.core.Matrix3D.create()
                new_occ = parent_comp.occurrences.addExistingComponent(component, fusion_transform)
                new_occ.transform = transform
                # You can think it is doing nothing but for some reason in
                # occurrence sub-tree(recursive call) setting custom uuid
                # doesn"t have any effect in new_occ comming from function
                # above
                new_occ = self.get_occ_by_name(new_occ.name)
                new_occ.isLightBulbOn = occurrence_properties["is_visible"]
                new_occ.isGrounded = occurrence_properties["is_grounded"]
                self.set_uuid(new_occ, occ_key)
                self.occ_id_map[occ_key] = new_occ
                branch_register.append({
                    "occurrence": new_occ,
                    "transform": fusion_transform
                })
                # we need to collect childs transformation and after that apply
                # transformation from bottom to top in the tree
                if new_occ.childOccurrences.count > 0:
                    self.update_child_occ(new_occ.childOccurrences, occ_value, branch_register)
                self.apply_transformations(branch_register)
            else:
                # create Identity transform
                transform = adsk.core.Matrix3D.create()
                new_occ = parent_comp.occurrences.addNewComponent(transform)
                occ_branch.append({
                    "occurrence": new_occ,
                    "transform": fusion_transform
                })
                new_comp = new_occ.component
                comp_name = self.assembly_data["components"][occurrence_properties["component"]]["name"]
                # An issue found with this character included in component name
                if "/" in comp_name:
                    comp_name = comp_name.replace("/", "-")
                new_comp.name = comp_name
                new_occ = self.get_occ_by_name(new_occ.name)
                new_occ.isLightBulbOn = occurrence_properties["is_visible"]
                new_occ.isGrounded = occurrence_properties["is_grounded"]
                self.set_uuid(new_comp, occurrence_properties["component"])
                self.comp_id_map[occurrence_properties["component"]] = new_comp
                self.set_uuid(new_occ, occ_key)
                self.occ_id_map[occ_key] = new_occ
                # create this transient component to import the body
                # with its component, then we move only the body where
                # it corresponds and finally deletes the component
                # that came with the body and also delete transient
                bodies_to_import = occurrence_properties.get("bodies", {})
                self.reconstruct_bodies_at_comp_level(new_comp, derivatives_path_files, bodies_to_import)
                new_occ_tree = occ_value
                if new_occ_tree:
                    self.start_tree_reconstruction(
                        derivatives_path_files,
                        new_comp, new_occ_tree, new_occ, occ_branch, components_reconstructed)
                # When Component/Occurrences is fully reconstructed
                # We can start applying real transformations
                if parent_occ is None:
                    self.apply_transformations(occ_branch)
                    occ_branch.clear()
                components_reconstructed[occurrence_properties["component"]] = new_comp

    def create_bodyid_bodyproxy_cache(self):
        """
        Create a bodies hash map for faster retrieval
        as bodies ids are not unique we create a hash map
        by combining occurrence/component id + body id
        """
        root_comp = self.design.rootComponent
        root_uuid = self.get_uuid(root_comp)
        for body in root_comp.bRepBodies:
            body_uuid = self.get_uuid(body)
            key = f"{root_uuid}_{body_uuid}"
            self.body_proxy_id_map[key] = body
        for occ in root_comp.allOccurrences:
            occ_uuid = self.get_uuid(occ)
            for proxy_body in occ.bRepBodies:
                body_uuid = self.get_uuid(proxy_body.nativeObject)
                key = f"{occ_uuid}_{body_uuid}"
                self.body_proxy_id_map[key] = proxy_body

    def find_joint_entity(self, entity_data, occ=None):
        """
        We need to return proxies data in order to use them
        as references in Joints
        """
        if 'occurrence' in entity_data:
            key = f"{entity_data['occurrence']}_{entity_data['body']}"
            if key not in self.body_proxy_id_map:
                raise Exception("Body Id not present in cache")

            body = self.body_proxy_id_map[key]
            if entity_data['occurrence'] not in self.occurrences_affected:
                self.occurrences_affected[entity_data['occurrence']] = {
                    "occ": body.assemblyContext,
                    "transform": body.assemblyContext.transform.copy()
                }
        else:
            key = f"{entity_data['root_component']}_{entity_data['body']}"
            if key not in self.body_proxy_id_map:
                # Handle a case where the direct design assembly
                # is missing the entity occurrence but we have the joint occurrence
                key = f"{occ}_{entity_data['body']}"
                if key not in self.body_proxy_id_map:
                    raise Exception("Body Id not present in cache")
            body = self.body_proxy_id_map[key]
        if entity_data["type"] == "BRepFace":
            return body.faces[entity_data["index"]]
        elif entity_data["type"] == "BRepEdge":
            return body.edges[entity_data["index"]]
        elif entity_data["type"] == "BRepVertex":
            return body.vertices[entity_data["index"]]
        else:
            raise Exception(f"Invalid enity type : {entity_data['type']}")

    def build_joint_geo_from_planes(self, geo_data, entity_one, joint_key_point_type, entity_two=None):
        plane_one = self.find_joint_entity(geo_data["plane_one"])
        plane_two = self.find_joint_entity(geo_data["plane_two"])
        jointGeometry = adsk.fusion.JointGeometry.createByBetweenTwoPlanes(plane_one, plane_two, entity_one,
                                                                           entity_two,
                                                                           joint_key_point_type)
        return jointGeometry

    def create_joint_origin(self, joint_data):
        parent_comp = self.get_parent_component(joint_data)
        joint_geometry = self.create_joint_geometry(joint_data["joint_geometry"])
        joint_origins = parent_comp.jointOrigins
        joint_origin_input = joint_origins.createInput(joint_geometry)
        joint_origin_input.angle = adsk.core.ValueInput.createByReal(joint_data["angle"]["value"])
        joint_origin_input.isFlipped = joint_data["is_flipped"]
        # Create the JointOrigin
        joint_origin = joint_origins.add(joint_origin_input)
        joint_origin.name = joint_data["name"]
        # These parameters will not exist in direct design so don't add them 
        if "name" in joint_data["angle"]:
            joint_origin.angle.name = joint_data["angle"]["name"]
        return joint_origin

    def create_as_built_joint(self, joint_data):
        parent_comp = self.get_parent_component(joint_data)
        as_built_joints = parent_comp.asBuiltJoints
        occ1 = self.occ_id_map[joint_data["occurrence_one"]]
        occ2 = self.occ_id_map[joint_data["occurrence_two"]]
        if "joint_geometry" in joint_data:
            geo_data = joint_data["joint_geometry"]
            geo = self.create_joint_geometry(geo_data, joint_data["occurrence_one"])
        else:
            geo = None
        asBuiltJointInput = as_built_joints.createInput(occ1, occ2, geo)
        self.set_joint_movement(joint_data, asBuiltJointInput)
        # Create the AsBuiltJoint
        return as_built_joints.add(asBuiltJointInput)

    def create_joint_geometry(self, geo_data, occ=None):
        """
        Creates a joint geometry from assembly data
        Not all joint Geometries are supported
        """
        entity_one = geo_data["entity_one"]
        entity_type = entity_one["type"]
        joint_key_point_type = deserialize.get_key_point_type(geo_data["key_point_type"])
        if "BRepFace" == entity_type:
            brep_entity = self.find_joint_entity(entity_one, occ)
            if geo_data["geometry_type"] == "JointBetweenTwoPlanesGeometry":
                geo = self.build_joint_geo_from_planes(geo_data, brep_entity, joint_key_point_type)
            elif geo_data["geometry_type"] == "JointPlanarBRepFaceGeometry":
                # In this scenario the user has selected a face and within the face an edge
                edge = None
                if "entity_two" in geo_data:
                    edge = self.find_joint_entity(geo_data["entity_two"], occ)
                geo = adsk.fusion.JointGeometry.createByPlanarFace(brep_entity, edge, joint_key_point_type)
            else:
                geo = adsk.fusion.JointGeometry.createByNonPlanarFace(brep_entity, joint_key_point_type)
        elif "BRepEdge" == entity_type:
            brep_entity = self.find_joint_entity(entity_one, occ)
            geo = adsk.fusion.JointGeometry.createByCurve(brep_entity, joint_key_point_type)
        elif "BRepVertex" == entity_type:
            brep_entity = self.find_joint_entity(entity_one, occ)
            geo = adsk.fusion.JointGeometry.createByPoint(brep_entity)
        else:
            raise Exception(f"Entity type : {entity_type} not supported")
        return geo

    def set_limits(self, limits, limits_data):
        limits.isMinimumValueEnabled = limits_data["is_minimum_value_enabled"]
        limits.minimumValue = limits_data["minimum_value"]
        limits.isMaximumValueEnabled = limits_data["is_maximum_value_enabled"]
        limits.maximumValue = limits_data["maximum_value"]
        limits.isRestValueEnabled = limits_data["is_rest_value_enabled"]
        limits.restValue = limits_data["rest_value"]

    def set_joint_motion_limits(self, joint, joint_motion):
        """
        Set joint motion and limits
        """
        try:
            if "slide_limits" in joint_motion:
                limits = joint.jointMotion.slideLimits
                self.set_limits(limits, joint_motion["slide_limits"])
            if "primary_slide_limits" in joint_motion:
                limits = joint.jointMotion.primarySlideLimits
                self.set_limits(limits, joint_motion["primary_slide_limits"])
            if "rotation_limits" in joint_motion:
                limits = joint.jointMotion.rotationLimits
                self.set_limits(limits, joint_motion["rotation_limits"])
            if "pitch_limits" in joint_motion:
                limits = joint.jointMotion.pitchLimits
                self.set_limits(limits, joint_motion["pitch_limits"])
            if "roll_limits" in joint_motion:
                limits = joint.jointMotion.rollLimits
                self.set_limits(limits, joint_motion["roll_limits"])
            if "yaw_limits" in joint_motion:
                limits = joint.jointMotion.yawLimits
                self.set_limits(limits, joint_motion["yaw_limits"])
        except Exception as ex:
            pass

    def get_movement_and_custom_entity(self, joint_motion, movement_name, custom_entity_name):
        movement_dir = custom_entity = None
        if movement_name in joint_motion:
            movement_dir = deserialize.get_rotation_axis(joint_motion[movement_name])
            if movement_dir == adsk.fusion.JointDirections.CustomJointDirection:
                custom_entity = self.find_joint_entity(
                    joint_motion[custom_entity_name])
        return movement_dir, custom_entity

    def get_joint_geometry_or_origin(self, geo_data, occ):
        if geo_data["type"] == "JointGeometry":
            geo = self.create_joint_geometry(geo_data, occ)
        else:
            geo = self.joint_origin_id_map[geo_data["joint_origin"]]
        return geo

    def set_joint_movement(self, joint, joint_input):
        if joint["joint_motion"]["joint_type"] == "PlanarJointType":
            norm_direct, norm_direct_entity = self.get_movement_and_custom_entity(joint["joint_motion"],
                                                                                  "normal_direction",
                                                                                  "custom_normal_direction_entity")
            primary_slide_direct, primary_slide_direct_entity = self.get_movement_and_custom_entity(
                joint["joint_motion"],
                "primary_slide_direction",
                "custom_primary_slide_direction_entity")
            if norm_direct_entity is None:
                joint_input.setAsPlanarJointMotion(norm_direct)
            else:
                joint_input.setAsPlanarJointMotion(norm_direct, norm_direct_entity, primary_slide_direct_entity)
        elif joint["joint_motion"]["joint_type"] == "BallJointType":
            pitch_direct, pitch_direct_entity = self.get_movement_and_custom_entity(joint["joint_motion"],
                                                                                    "pitch_direction",
                                                                                    "custom_pitch_direction_entity")
            yaw_direct, yaw_direct_entity = self.get_movement_and_custom_entity(joint["joint_motion"],
                                                                                "yaw_direction",
                                                                                "custom_yaw_direction_entity")
            if pitch_direct_entity is None or yaw_direct_entity is None:
                joint_input.setAsBallJointMotion(pitch_direct, yaw_direct)
            else:
                joint_input.setAsBallJointMotion(pitch_direct, yaw_direct, pitch_direct_entity, yaw_direct_entity)
        else:
            rotation_dir, custom_rot = self.get_movement_and_custom_entity(joint["joint_motion"],
                                                                           "rotation_axis",
                                                                           "custom_rotation_axis_entity")
            slide_dir, custom_slide = self.get_movement_and_custom_entity(joint["joint_motion"],
                                                                          "slide_direction",
                                                                          "custom_slide_direction_entity")
            if joint["joint_motion"]["joint_type"] == "RigidJointType":
                joint_input.setAsRigidJointMotion()
            elif joint["joint_motion"]["joint_type"] == "PinSlotJointType":
                if custom_rot is None and custom_slide is None:
                    joint_input.setAsPinSlotJointMotion(rotation_dir, slide_dir)
                else:
                    joint_input.setAsPinSlotJointMotion(rotation_dir, slide_dir, custom_rot, custom_slide)
            elif joint["joint_motion"]["joint_type"] == "RevoluteJointType":
                if custom_rot is None:
                    joint_input.setAsRevoluteJointMotion(rotation_dir)
                else:
                    joint_input.setAsRevoluteJointMotion(rotation_dir, custom_rot)
            elif joint["joint_motion"]["joint_type"] == "SliderJointType":
                if custom_slide is None:
                    joint_input.setAsSliderJointMotion(slide_dir)
                else:
                    joint_input.setAsSliderJointMotion(slide_dir, custom_slide)
            elif joint["joint_motion"]["joint_type"] == "CylindricalJointType":
                if custom_rot is None:
                    joint_input.setAsCylindricalJointMotion(rotation_dir)
                else:
                    joint_input.setAsCylindricalJointMotion(rotation_dir, custom_rot)
            else:
                raise Exception("Joint Motion Type not supported")

    def get_parent_component(self, joint_data):
        component_id = joint_data["parent_component"]
        return self.comp_id_map[component_id]

    def create_joints(self):
        joints = self.assembly_data.get("joints",{})
        joints_origin = self.assembly_data.get("joint_origins",{})
        as_built_joints = self.assembly_data.get("as_built_joints",{}) 
        self.create_bodyid_bodyproxy_cache()
        for j_origin_key, joint_origin_val in joints_origin.items():
            if j_origin_key is None:
                continue
            joint_origin = self.create_joint_origin(joint_origin_val)
            joint_origin.isLightBulbOn = False
            self.joint_origin_id_map[j_origin_key] = joint_origin
            self.set_uuid(joint_origin, j_origin_key)

        for joint_k, joint in joints.items():
            if joint_k is None:
                continue
            parent_comp = self.get_parent_component(joint)
            current_joints = parent_comp.joints
            geo_one_data = joint["geometry_or_origin_one"]
            geo_two_data = joint["geometry_or_origin_two"]
            occ_one = None
            if "occurrence_one" in joint:
                occ_one = joint["occurrence_one"]
            occ_two = None
            if "occurrence_two" in joint:
                occ_two = joint["occurrence_two"]
            geo_one = self.get_joint_geometry_or_origin(geo_one_data, occ_one)
            geo_two = self.get_joint_geometry_or_origin(geo_two_data, occ_two)
            joint_input = current_joints.createInput(geo_one, geo_two)
            # Set the joint input
            joint_input.angle = adsk.core.ValueInput.createByReal(joint["angle"]["value"])
            joint_input.offset = adsk.core.ValueInput.createByReal(joint["offset"]["value"])
            joint_input.isFlipped = joint["is_flipped"]
            self.set_joint_movement(joint, joint_input)
            _joint = current_joints.add(joint_input)
            try:
                _joint.name = joint["name"]
            except Exception as ex:
                # This is a workaround when a joint is invalid
                # We catch the exception and set the design type to direct design
                self.design.designType = adsk.fusion.DesignTypes.DirectDesignType
                _joint = current_joints.add(joint_input)
                _joint.name = joint["name"]
            _joint.isLightBulbOn = False

            if _joint.angle is not None and "angle" in joint and "name" in joint["angle"]:
                _joint.angle.name = joint["angle"]["name"]
            if _joint.offset is not None and "offset" in joint and "name" in joint["offset"]:
                _joint.offset.name = joint["offset"]["name"]
            self.set_uuid(_joint, joint_k)
            self.set_joint_motion_limits(_joint, joint["joint_motion"])

        for as_builtj_k, as_builtj in as_built_joints.items():
            if as_builtj_k is None:
                continue
            as_built_joint = self.create_as_built_joint(as_builtj)
            as_built_joint.isLightBulbOn = False
            as_built_joint.name = as_builtj["name"]
            self.set_uuid(as_built_joint, as_builtj_k)
            self.set_joint_motion_limits(as_built_joint, as_builtj["joint_motion"])

    def verify_occurrences_transformation(self):
        """
        Occurrence transformation might be affected
        after setting a joint, for that reason 
        we re-set occurrence transformation in occurrences
        that might be affected
        """
        for occ_ in self.occurrences_affected.values():
            occ = occ_["occ"]
            occ.transform = occ_["transform"]
