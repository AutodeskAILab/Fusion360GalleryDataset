"""

Deserialize dictionary data from json to Fusion 360 entities

"""

import adsk.core
import adsk.fusion


def point2d(point_data):
    return adsk.core.Point2D.create(
        point_data["x"],
        point_data["y"]
    )


def point3d(point_data):
    return adsk.core.Point3D.create(
        point_data["x"],
        point_data["y"],
        point_data["z"]
    )


def point3d_list(point_list, xform=None):
    points = []
    for point_data in point_list:
        point = point3d(point_data)
        if xform is not None:
            point.transformBy(xform)
        points.append(point)
    return points


def vector3d(vector_data):
    return adsk.core.Vector3D.create(
        vector_data["x"],
        vector_data["y"],
        vector_data["z"]
    )


def line2d(start_point_data, end_point_data):
    start_point = point2d(start_point_data)
    end_point = point2d(end_point_data)
    return adsk.core.Line2D.create(start_point, end_point)


def plane(plane_data):
    origin = point3d(plane_data["origin"])
    normal = vector3d(plane_data["normal"])
    u_direction = vector3d(plane_data["u_direction"])
    v_direction = vector3d(plane_data["v_direction"])
    plane = adsk.core.Plane.create(origin, normal)
    plane.setUVDirections(u_direction, v_direction)
    return plane


def matrix3d(matrix_data):
    matrix = adsk.core.Matrix3D.create()
    origin = point3d(matrix_data["origin"])
    x_axis = vector3d(matrix_data["x_axis"])
    y_axis = vector3d(matrix_data["y_axis"])
    z_axis = vector3d(matrix_data["z_axis"])
    matrix.setWithCoordinateSystem(origin, x_axis, y_axis, z_axis)
    return matrix


def feature_operations(operation_data):
    if operation_data == "JoinFeatureOperation":
        return adsk.fusion.FeatureOperations.JoinFeatureOperation
    if operation_data == "CutFeatureOperation":
        return adsk.fusion.FeatureOperations.CutFeatureOperation
    if operation_data == "IntersectFeatureOperation":
        return adsk.fusion.FeatureOperations.IntersectFeatureOperation
    if operation_data == "NewBodyFeatureOperation":
        return adsk.fusion.FeatureOperations.NewBodyFeatureOperation
    if operation_data == "NewComponentFeatureOperation":
        return adsk.fusion.FeatureOperations.NewComponentFeatureOperation
    return None


def construction_plane(name):
    """Return a construction plane given a name"""
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    construction_planes = {
        "xy": design.rootComponent.xYConstructionPlane,
        "xz": design.rootComponent.xZConstructionPlane,
        "yz": design.rootComponent.yZConstructionPlane
    }
    name_lower = name.lower()
    if name_lower in construction_planes:
        return construction_planes[name_lower]
    return None


def face_by_point3d(point3d_data):
    """Find a face with given serialized point3d that sits on that face"""
    point_on_face = point3d(point3d_data)
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    for component in design.allComponents:
        try:
            entities = component.findBRepUsingPoint(
                point_on_face,
                adsk.fusion.BRepEntityTypes.BRepFaceEntityType,
                0.01, # -1.0 is the default tolerance
                False
            )
            if entities is None or len(entities) == 0:
                continue
            else:
                # Return the first face
                # although there could be multiple matches
                return entities[0]
        except Exception as ex:
            print("Exception finding BRepFace", ex)
            # Ignore and keep looking
            pass
    return None


def view_orientation(name):
    """Return a camera view orientation given a name"""
    view_orientations = {
        "ArbitraryViewOrientation": adsk.core.ViewOrientations.ArbitraryViewOrientation,
        "BackViewOrientation": adsk.core.ViewOrientations.BackViewOrientation,
        "BottomViewOrientation": adsk.core.ViewOrientations.BottomViewOrientation,
        "FrontViewOrientation": adsk.core.ViewOrientations.FrontViewOrientation,
        "IsoBottomLeftViewOrientation": adsk.core.ViewOrientations.IsoBottomLeftViewOrientation,
        "IsoBottomRightViewOrientation": adsk.core.ViewOrientations.IsoBottomRightViewOrientation,
        "IsoTopLeftViewOrientation": adsk.core.ViewOrientations.IsoTopLeftViewOrientation,
        "IsoTopRightViewOrientation": adsk.core.ViewOrientations.IsoTopRightViewOrientation,
        "LeftViewOrientation": adsk.core.ViewOrientations.LeftViewOrientation,
        "RightViewOrientation": adsk.core.ViewOrientations.RightViewOrientation,
        "TopViewOrientation": adsk.core.ViewOrientations.TopViewOrientation,
    }
    name_lower = name.lower()
    if name_lower in view_orientations:
        return view_orientations[name_lower]
    return None


def get_key_point_type(key_point_str):
    """Return Key Point Type used in a Joint"""
    if key_point_str == "CenterKeyPoint":
        return adsk.fusion.JointKeyPointTypes.CenterKeyPoint
    elif key_point_str == "EndKeyPoint":
        return adsk.fusion.JointKeyPointTypes.EndKeyPoint
    elif key_point_str == "MiddleKeyPoint":
        return adsk.fusion.JointKeyPointTypes.MiddleKeyPoint
    elif key_point_str == "StartKeyPoint":
        return adsk.fusion.JointKeyPointTypes.StartKeyPoint
    else:
        raise Exception(f"Unknown keyPointType type: {key_point_str}")


def get_rotation_axis(rotation_axis):
    """Receives a string and Return Joint direction type"""
    if rotation_axis == "XAxisJointDirection":
        return adsk.fusion.JointDirections.XAxisJointDirection
    elif rotation_axis == "YAxisJointDirection":
        return adsk.fusion.JointDirections.YAxisJointDirection
    elif rotation_axis == "ZAxisJointDirection":
        return adsk.fusion.JointDirections.ZAxisJointDirection
    elif rotation_axis == "CustomJointDirection":
        return adsk.fusion.JointDirections.CustomJointDirection
    else:
        raise Exception(f"Unknown JointDirections type: {rotation_axis}")