import adsk.core
import adsk.fusion
import uuid
import json
import math
from importlib import reload

import geometry_util
import entity_exporter
reload(geometry_util)
reload(entity_exporter)


def get_uuid(entity, groupName="Dataset"):
    if isinstance(entity, adsk.fusion.Profile):
        return get_profile_uuid(entity)
    else:
        uuid_att = entity.attributes.itemByName(groupName, "uuid")
        if uuid_att is not None:
            return uuid_att.value
        else:
            # Return None to allow for workarounds
            return None


def get_profile_uuid(profile):
    # Sketch profiles don"t support attributes
    # so we cook up a UUID from the curves UUIDs
    profile_curves = []
    for loop in profile.profileLoops:
        for curve in loop.profileCurves:
            sketch_ent = curve.sketchEntity
            profile_curves.append(get_uuid(sketch_ent))
    # Concat all the uuids from the curves
    curve_uuids = "_".join(profile_curves)
    # Generate a UUID by hashing the curve_uuids
    return str(uuid.uuid3(uuid.NAMESPACE_URL, curve_uuids))


def set_uuid(entity, groupName="Dataset"):
    uuid_att = entity.attributes.itemByName(groupName, "uuid")
    if uuid_att is None:
        unique_id = uuid.uuid1()
        entity.attributes.add(groupName, "uuid", str(unique_id))


def set_custom_uuid(entity, custom_uuid, groupName="Dataset"):
    entity.attributes.add(groupName, "uuid", custom_uuid)


def set_uuids_for_collection(entities, groupName="Dataset"):
    for ent in entities:
        # Strange -- We sometimes get an None entity in the contraints array
        # when we have a SketchFixedSpline in the sketch.  We guard against
        # that crashing the threads here
        if ent is not None:
            set_uuid(ent, groupName)


def get_object_type(entity):
    return entity.objectType.split("::")[-1]


def get_point2d(point):
    data = {}
    data["type"] = get_object_type(point)
    data["x"] = point.x
    data["y"] = point.y
    return data


def get_point3d(point):
    data = {}
    data["type"] = get_object_type(point)
    data["x"] = point.x
    data["y"] = point.y
    data["z"] = point.z
    return data


def get_vector2d(vector):
    data = {}
    data["type"] = get_object_type(vector)
    data["x"] = vector.x
    data["y"] = vector.y
    data["length"] = vector.length
    return data


def get_vector3d(vector):
    data = {}
    data["type"] = get_object_type(vector)
    data["x"] = vector.x
    data["y"] = vector.y
    data["z"] = vector.z
    data["length"] = vector.length
    return data


def get_plane(plane):
    data = {}
    data["type"] = get_object_type(plane)
    data["origin"] = get_point3d(plane.origin)
    data["normal"] = get_vector3d(plane.normal)
    data["u_direction"] = get_vector3d(plane.uDirection)
    data["v_direction"] = get_vector3d(plane.vDirection)
    return data


def get_matrix3d_coordinate_system(matrix3d):
    (origin, x_axis, y_axis, z_axis) = matrix3d.getAsCoordinateSystem()
    data = {}
    data["origin"] = get_point3d(origin)
    data["x_axis"] = get_vector3d(x_axis)
    data["y_axis"] = get_vector3d(y_axis)
    data["z_axis"] = get_vector3d(z_axis)
    return data


def get_bounding_box3d(box):
    data = {}
    data["type"] = get_object_type(box)
    data["max_point"] = get_point3d(box.maxPoint)
    data["min_point"] = get_point3d(box.minPoint)
    return data


def get_model_parameter(model_parameter):
    data = {}
    data["type"] = get_object_type(model_parameter)
    if model_parameter.value is not None and model_parameter.value != "":
        data["value"] = model_parameter.value
    # if model_parameter.unit is not None and model_parameter.unit != "":
    #     data["unit"] = model_parameter.unit
    if model_parameter.name is not None and model_parameter.name != "":
        data["name"] = model_parameter.name
    if model_parameter.role is not None and model_parameter.role != "":
        data["role"] = model_parameter.role
    # if model_parameter.expression is not None and
    # model_parameter.expression != "":
    # data["expression"] = model_parameter.expression
    return data


def get_value_input(value_input):
    data = {}
    data["type"] = get_object_type(value_input)
    if value_input.valueType == adsk.fusion.ValueTypes.RealValueType:
        data["value"] = value_input.realValue
    elif value_input.valueType == adsk.fusion.ValueTypes.StringValueType:
        data["value"] = value_input.stringValue
    elif value_input.valueType == adsk.fusion.ValueTypes.ObjectValueType:
        print("Unsupported value input type: ObjectValueType")
    return data


def get_operation_data(operation):
    if operation == adsk.fusion.FeatureOperations.JoinFeatureOperation:
        return "JoinFeatureOperation"
    elif operation == adsk.fusion.FeatureOperations.CutFeatureOperation:
        return "CutFeatureOperation"
    elif operation == adsk.fusion.FeatureOperations.IntersectFeatureOperation:
        return "IntersectFeatureOperation"
    elif operation == adsk.fusion.FeatureOperations.NewBodyFeatureOperation:
        return "NewBodyFeatureOperation"
    elif operation == adsk.fusion.FeatureOperations.NewComponentFeatureOperation:
        return "NewComponentFeatureOperation"
    else:
        raise Exception(f"Unknown operation: {operation.classType()}")


def get_extent_type_data(extent_type):
    if extent_type == adsk.fusion.FeatureExtentTypes.OneSideFeatureExtentType:
        return "OneSideFeatureExtentType"
    elif extent_type == adsk.fusion.FeatureExtentTypes.TwoSidesFeatureExtentType:
        return "TwoSidesFeatureExtentType"
    elif extent_type == adsk.fusion.FeatureExtentTypes.SymmetricFeatureExtentType:
        return "SymmetricFeatureExtentType"
    else:
        raise Exception(f"Unknown extend type: {extent_type.classType()}")


def get_surface_type(surface):
    if surface.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType:
        return "PlaneSurfaceType"
    elif surface.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType:
        return "CylinderSurfaceType"
    elif surface.surfaceType == adsk.core.SurfaceTypes.ConeSurfaceType:
        return "ConeSurfaceType"
    elif surface.surfaceType == adsk.core.SurfaceTypes.SphereSurfaceType:
        return "SphereSurfaceType"
    elif surface.surfaceType == adsk.core.SurfaceTypes.TorusSurfaceType:
        return "TorusSurfaceType"
    elif surface.surfaceType == adsk.core.SurfaceTypes.EllipticalCylinderSurfaceType:
        return "EllipticalCylinderSurfaceType"
    elif surface.surfaceType == adsk.core.SurfaceTypes.EllipticalConeSurfaceType:
        return "EllipticalConeSurfaceType"
    elif surface.surfaceType == adsk.core.SurfaceTypes.NurbsSurfaceType:
        return "NurbsSurfaceType"
    else:
        raise Exception(f"Unknown surface type: {surface.surfaceType}")


def get_principal_axes(physical_properties):
    (result, pa_x, pa_y, pa_z) = physical_properties.getPrincipalAxes()
    pa = {}
    if result:
        pa = {
            "x_axis": get_vector3d(pa_x),
            "y_axis": get_vector3d(pa_y),
            "z_axis": get_vector3d(pa_z)
        }
    return pa


def get_moments_of_inertia_at_cog(physical_properties):
    """Return the moments of inertia at the center of gravity"""
    (result, xx, yy, zz, xy, yz, xz) = \
        physical_properties.getXYZMomentsOfInertia()
    moi_at_cog = {}
    if result:
        mass = physical_properties.mass
        cog = physical_properties.centerOfMass

        xxcog = cog.y * cog.y + cog.z * cog.z
        yycog = cog.x * cog.x + cog.z * cog.z
        zzcog = cog.x * cog.x + cog.y * cog.y
        # Note: tensor stores off diag in reverse order to asm output
        # xycog = -cog.x*cog.y  # m_productsOfInertia[2]
        # xzcog = -cog.x*cog.z  # m_productsOfInertia[1]
        # yzcog = -cog.y*cog.z  # m_productsOfInertia[0]

        xxcog *= mass
        yycog *= mass
        zzcog *= mass
        # xycog *= mass
        # yzcog *= mass
        # xzcog *= mass

        xx -= xxcog
        yy -= yycog
        zz -= zzcog
        # xy -= xycog
        # yz -= yzcog
        # xz -= xzcog
        moi_at_cog = {
            "i1": xx,
            "i2": yy,
            "i3": zz
        }
    return moi_at_cog


def get_xyz_moments_of_inertia(physical_properties):
    (result, xx, yy, zz, xy, yz, xz) = \
        physical_properties.getXYZMomentsOfInertia()
    xyz_moi = {}
    if result:
        xyz_moi = {
            "xx": xx,
            "yy": yy,
            "zz": zz,
            "xy": xy,
            "yz": yz,
            "xz": xz
        }
    return xyz_moi


def get_properties(entity):
    """Return the properties of a component, occurrence, or body"""
    data = {}
    #  Roll this into a collection so we can set the accuracy to high
    entity_collection = adsk.core.ObjectCollection.create()
    entity_collection.add(entity)
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    physical_properties = design.physicalProperties(
        entity_collection,
        adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy)
    data["name"] = entity.name

    # Component bounding box calculation is unreliable
    # so do it ourselves from the bodies
    adsk.doEvents()  # Possibly needed to populate bounding box data
    if isinstance(entity, adsk.fusion.Component):
        body_bb = geometry_util.get_brep_bodies_bounding_box(entity.bRepBodies)
        data["bounding_box"] = get_bounding_box3d(body_bb)
    else:
        data["bounding_box"] = get_bounding_box3d(entity.boundingBox)
    data["vertex_count"] = geometry_util.get_vertex_count(entity)
    data["edge_count"] = geometry_util.get_edge_count(entity)
    data["face_count"] = geometry_util.get_face_count(entity)
    data["loop_count"] = geometry_util.get_loop_count(entity)
    data["shell_count"] = geometry_util.get_shell_count(entity)
    if isinstance(entity, adsk.fusion.Component) or \
            isinstance(entity, adsk.fusion.Occurrence):
        data["body_count"] = entity.bRepBodies.count
    data["area"] = physical_properties.area
    data["volume"] = physical_properties.volume
    if not math.isnan(physical_properties.density):
        data["density"] = physical_properties.density
    data["mass"] = physical_properties.mass
    data["center_of_mass"] = get_point3d(physical_properties.centerOfMass)
    data["principal_axes"] = get_principal_axes(physical_properties)
    data["xyz_moments_of_inertia"] = get_xyz_moments_of_inertia(
        physical_properties)
    data["surface_types"] = geometry_util.get_surface_types_tally(entity)
    data["vertex_valence"] = geometry_util.get_vertex_valence_tally(entity)
    return data


def get_profile_properties(profile):
    """Return the properties of a profile"""
    data = {}
    props = profile.areaProperties(adsk.fusion.CalculationAccuracy.HighCalculationAccuracy)
    data["area"] = props.area
    data["centroid"] = get_point3d(props.centroid)
    data["perimeter"] = props.perimeter
    return data


def get_occurrence_tree_data(root_comp):
    """Return Occurrence tree structure of the model"""
    data = {"tree": {

    }}
    root_comp_exporter = \
        entity_exporter.ComponentExporter(root_comp)
    root_comp_id = root_comp_exporter.uuid
    data["tree"][root_comp_id] = {}
    data["tree"][root_comp_id]["bodies"] = {}
    body_exporters = root_comp_exporter.body_exporter_collection.get_body_exporters()
    for body_exp in body_exporters:
        data["tree"][root_comp_id]["bodies"][body_exp.uuid] = {
            "is_visible": body_exp.entity.isLightBulbOn
        }

    occ_collection = root_comp.occurrences

    for occ in occ_collection:
        occ_exporter = entity_exporter.OccurrenceExporter(occ)
        occ_data, error = occ_exporter.get_data()
        if error is None:
            data["tree"][root_comp_id][occ_exporter.uuid] = occ_data
        else:
            raise Exception(error)
    return data
