"""

Serialize Fusion 360 entities to dictionary data for json

"""

import adsk.core
import adsk.fusion

from . import name


def object_type(entity):
    return entity.objectType.split("::")[-1]


def point2d(point):
    data = {}
    data["type"] = object_type(point)
    data["x"] = point.x
    data["y"] = point.y
    return data


def point3d(point):
    data = {}
    data["type"] = object_type(point)
    data["x"] = point.x
    data["y"] = point.y
    data["z"] = point.z
    return data


def vector2d(vector):
    data = {}
    data["type"] = object_type(vector)
    data["x"] = vector.x
    data["y"] = vector.y
    data["length"] = vector.length
    return data


def vector3d(vector):
    data = {}
    data["type"] = object_type(vector)
    data["x"] = vector.x
    data["y"] = vector.y
    data["z"] = vector.z
    data["length"] = vector.length
    return data


def plane(plane):
    data = {}
    data["type"] = object_type(plane)
    data["origin"] = point3d(plane.origin)
    data["normal"] = vector3d(plane.normal)
    data["u_direction"] = vector3d(plane.uDirection)
    data["v_direction"] = vector3d(plane.vDirection)
    return data


def matrix3d_coordinate_system(matrix3d):
    (origin, x_axis, y_axis, z_axis) = matrix3d.getAsCoordinateSystem()
    data = {}
    data["origin"] = point3d(origin)
    data["x_axis"] = vector3d(x_axis)
    data["y_axis"] = vector3d(y_axis)
    data["z_axis"] = vector3d(z_axis)
    return data


def sketch_profiles(profiles):
    data = {}
    for profile in profiles:
        if profile is not None:
            uuid = name.get_uuid(profile)
            data[uuid] = sketch_profile(profile)
    return data


def sketch_profile(profile):
    data = {}
    loops_list = []
    for loop in profile.profileLoops:
        if loop is not None:
            loops_list.append(sketch_profile_loop(loop))
    data["loops"] = loops_list
    data["properties"] = sketch_profile_properties(profile)
    return data


def sketch_profile_loop(loop):
    data = {}
    data["is_outer"] = loop.isOuter
    profile_curves = []
    for curve in loop.profileCurves:
        if curve is not None:
            curve_data = sketch_profile_curve(curve)
            curve_data["curve"] = curve_uuid = name.get_uuid(curve.sketchEntity)
            profile_curves.append(curve_data)
    data["profile_curves"] = profile_curves
    return data


def sketch_profile_curve(curve):
    data = {}
    curve_geometry = curve.geometry
    curve_type = curve.geometryType
    data["type"] = object_type(curve_geometry)
    if curve_type == adsk.core.Curve3DTypes.Line3DCurveType:
        curve_data = __get_line_data(curve_geometry)
    elif curve_type == adsk.core.Curve3DTypes.Arc3DCurveType:
        curve_data = __get_arc_data(curve_geometry)
    elif curve_type == adsk.core.Curve3DTypes.Circle3DCurveType:
        curve_data = __get_circle_data(curve_geometry)
    elif curve_type == adsk.core.Curve3DTypes.Ellipse3DCurveType:
        curve_data = __get_ellipse_data(curve_geometry)
    elif curve_type == adsk.core.Curve3DTypes.EllipticalArc3DCurveType:
        curve_data = __get_elliptical_arc_data(curve_geometry)
    elif curve_type == adsk.core.Curve3DTypes.InfiniteLine3DCurveType:
        curve_data = __get_infinite_line_data(curve_geometry)
    elif curve_type == adsk.core.Curve3DTypes.NurbsCurve3DCurveType:
        curve_data = __get_nurbs_curve_data(curve_geometry)
    else:
        raise Exception(f"Unknown curve type: {curve_type}")
    data.update(**curve_data)
    return data


def sketch_profile_properties(profile):
    """Return the properties of a profile"""
    data = {}
    props = profile.areaProperties(adsk.fusion.CalculationAccuracy.HighCalculationAccuracy)
    data["area"] = props.area
    data["centroid"] = point3d(props.centroid)
    data["perimeter"] = props.perimeter
    return data


# Private Members ---------------------------------


def __get_common_open_curve_members_data(curve):
    data = {}
    data["start_point"] = point3d(curve.startPoint)
    data["end_point"] = point3d(curve.endPoint)
    return data


def __get_common_arc_members_data(curve):
    data = {}
    data["start_angle"] = curve.startAngle
    data["end_angle"] = curve.endAngle
    return data


def __get_common_circle_members_data(curve):
    data = {}
    data["center_point"] = point3d(curve.center)
    data["radius"] = curve.radius
    data["normal"] = vector3d(curve.normal)
    return data


def __get_common_elliptical_curve_members_data(curve):
    data = {}
    data["major_axis"] = vector3d(curve.majorAxis)
    data["major_axis_radius"] = curve.majorRadius
    data["minor_axis_radius"] = curve.minorRadius
    data["center_point"] = point3d(curve.center)
    data["normal"] = vector3d(curve.normal)
    return data


def __get_common_spline_members_data(nurb):
    data = {}
    (return_value, control_points, degree, knots, is_rational, weights, is_periodic) = nurb.getData()
    if return_value:
        data["degree"] = degree
        data["knots"] = knots
        data["rational"] = is_rational
        control_point_data = []
        for point in control_points:
            control_point_data.append(point3d(point))
        data["control_points"] = control_point_data
        data["weights"] = weights
        data["periodic"] = is_periodic
    return data


def __get_line_data(curve):
    data = __get_common_open_curve_members_data(curve)
    return data


def __get_arc_data(curve):
    data = __get_common_open_curve_members_data(curve)
    common_circle_data = __get_common_circle_members_data(curve)
    common_arc_data = __get_common_arc_members_data(curve)
    data.update(**common_circle_data, **common_arc_data)
    data["reference_vector"] = vector3d(curve.referenceVector)
    return data


def __get_circle_data(curve):
    data = __get_common_circle_members_data(curve)
    return data


def __get_ellipse_data(curve):
    data = __get_common_elliptical_curve_members_data(curve)
    return data


def __get_elliptical_arc_data(curve):
    data = __get_common_elliptical_curve_members_data(curve)
    common_arc_data = __get_common_arc_members_data(curve)
    data.update(**common_arc_data)
    return data


def __get_infinite_line_data(curve):
    data = {}
    data["origin"] = point3d(curve.origin)
    data["direction"] = vector3d(curve.direction)
    return data


def __get_nurbs_curve_data(curve):
    return __get_common_spline_members_data(curve)
