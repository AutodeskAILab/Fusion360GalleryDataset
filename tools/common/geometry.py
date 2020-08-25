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


def get_edge_count(entity):
    bodies = __get_bodies_from_entity(entity)
    count = 0
    for body in bodies:
        try:
            count += body.edges.count
        except Exception:
            pass
    return count


def get_face_count(entity):
    bodies = __get_bodies_from_entity(entity)
    count = 0
    for body in bodies:
        try:
            count += body.faces.count
        except Exception:
            pass
    return count


def get_shell_count(entity):
    bodies = __get_bodies_from_entity(entity)
    count = 0
    for body in bodies:
        try:
            count += body.shells.count
        except Exception:
            pass
    return count


def get_loop_count(entity):
    bodies = __get_bodies_from_entity(entity)
    count = 0
    for body in bodies:
        for face in body.faces:
            count += face.loops.count
    return count


def get_sketch_point_count(entity):
    count = 0
    if isinstance(entity, adsk.fusion.Components):
        for component in entity:
            for sketch in component.sketches:
                count += sketch.sketchPoints.count
    elif isinstance(entity, adsk.fusion.Component):
        for sketch in entity.sketches:
            count += sketch.sketchPoints.count
    return count


def get_vertex_count(entity):
    bodies = __get_bodies_from_entity(entity)
    count = 0
    for body in bodies:
        count += body.vertices.count
    return count


def intersection_over_union(component_one, component_two):
    """Calculate the intersection over union between two components"""
    # TODO: Union
    # We union all bodies together and take the volume

    # TODO: Intersect
    # We union the bodies for each component
    # then find the intersection of each body, with all bodies
    # in the other component
    pass


def join_temp_brep_bodies(bodies):
    """Try to join multiple brep bodies into a single temp body"""
    if len(bodies) == 0:
        return None
    temp_brep_manager = adsk.fusion.TemporaryBRepManager.get()
    first_brep = temp_brep_manager.copy(bodies[0])
    if len(bodies) == 1:
        return first_brep
    union = adsk.fusion.BooleanTypes.UnionBooleanType
    for index in range(1, len(bodies)):
        # TODO: Check if the volume of first_brep
        # has changed before/after boolean
        # if it hasn't changed add that tool to the list to return
        result = temp_brep_manager.booleanOperation(
            first_brep,
            bodies[index],
            union
        )
        # result will be true if successful
    return first_brep


def __get_bodies_from_entity(entity):
    """Return a collection of bodies from a Component, Instance, or BRepBody"""
    bodies = []
    if (isinstance(entity, adsk.fusion.Component) or
       isinstance(entity, adsk.fusion.Occurrence)):
        bodies = entity.bRepBodies
    elif isinstance(entity, adsk.fusion.BRepBody):
        bodies = [entity]
    else:
        raise Exception(f"Unexpected entity type: {entity.classType()}")
    return bodies
