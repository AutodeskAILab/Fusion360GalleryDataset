import adsk.core
import adsk.fusion


def get_bounding_box(entity):
    """Get the bounding box of an entity"""
    if isinstance(entity, adsk.fusion.Component):
        # Component bounding box calculation is unreliable
        # so do it ourselves from the bodies
        body_bb = get_brep_bodies_bounding_box(entity.bRepBodies)
        return body_bb
    else:
        return entity.boundingBox


def get_brep_bodies_bounding_box(bodies):
    """Manually calculate the bounding box of a collection of bodies"""
    min_point = adsk.core.Point3D.create(
        float('inf'), float('inf'), float('inf'))
    max_point = adsk.core.Point3D.create(
        float('-inf'), float('-inf'), float('-inf'))
    for body in bodies:
        try:
            body_min = body.boundingBox.minPoint
            body_max = body.boundingBox.maxPoint

            if body_min.x < min_point.x:
                min_point.x = body_min.x
            if body_min.y < min_point.y:
                min_point.y = body_min.y
            if body_min.z < min_point.z:
                min_point.z = body_min.z

            if body_max.x > max_point.x:
                max_point.x = body_max.x
            if body_max.y > max_point.y:
                max_point.y = body_max.y
            if body_max.z > max_point.z:
                max_point.z = body_max.z
        except:
            # Body without a boundingBox?
            # Lets assume it is invalid and keep moving
            pass
    bbox = adsk.core.BoundingBox3D.create(min_point, max_point)
    return bbox


def get_face_normal(face):
    """Get the normal at the center of the face"""
    point_on_face = face.pointOnFace
    evaluator = face.evaluator
    normal_result, normal = evaluator.getNormalAtPoint(point_on_face)
    assert normal_result
    return normal


def are_faces_perpendicular(face1, face2):
    normal1 = get_face_normal(face1)
    normal2 = get_face_normal(face2)
    return normal1.isPerpendicularTo(normal2)


def are_faces_tangentially_connected(face1, face2):
    for tc_face in face1.tangentiallyConnectedFaces:
        if tc_face.tempId == face2.tempId:
            return True
    return False
