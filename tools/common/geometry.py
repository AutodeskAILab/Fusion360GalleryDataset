import adsk.core
import adsk.fusion
import math


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
    all_bodies = []
    all_bodies.extend(component_one.bRepBodies)
    all_bodies.extend(component_two.bRepBodies)
    union_volume = get_union_volume(all_bodies)
    # Boolean failure
    if union_volume is None:
        return None
    # Avoid divide by zero
    if union_volume <= 0:
        return 0.0
    intersect_volume = get_intersect_volume(
        component_one.bRepBodies,
        component_two.bRepBodies
    )
    return intersect_volume / union_volume


def get_union_volume(bodies, copy=True):
    """Get the unioned volume of a set of bodies"""
    num_bodies = len(bodies)
    if num_bodies == 0:
        return 0.0
    if num_bodies == 1:
        return bodies[0].volume

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    temp_brep_manager = adsk.fusion.TemporaryBRepManager.get()
    operation = adsk.fusion.BooleanTypes.UnionBooleanType 

    bodies_copy = []
    # We make a transient copy of the bodies if we need to
    if copy:
        for body in bodies:
            body_copy = temp_brep_manager.copy(body)
            bodies_copy.append(body_copy)
    else:
        bodies_copy = bodies

    # Loop over all pairs of bodies
    for i in range(num_bodies):
        for j in range(i):
            # Get the target and tool bodies to try
            # Check if we already accumulated
            # the target or tool into another body
            target = bodies_copy[i]
            if target is None:
                continue
            tool = bodies_copy[j]
            if tool is None:
                continue
            # Store the previous volume of the target
            prev_target_volume = target.volume
            # Do the boolean
            boolean_success = temp_brep_manager.booleanOperation(target, tool, operation)
            if not boolean_success:
                return None
            else:
                volume_diff = math.fabs(prev_target_volume - target.volume)
                # If the volume has changed, we know there was an overlap
                if volume_diff > app.pointTolerance:
                    # Mark that the tool was accumulated into the target
                    bodies_copy[j] = None
                # If the volume has not changed there is either:
                # 1. OUTSIDE: No overlap, so we want to count that volume
                # 2. INSIDE: Direct overlap/containment
                #            so we don't want to count it
                else:
                    keep_tool = False
                    # We check that the first point on the tool face
                    # is within the target
                    containment = target.pointContainment(tool.faces[0].pointOnFace)
                    # If this points is outside of the target
                    # we can keep the tool to have the volume count
                    if containment != adsk.fusion.PointContainment.PointOutsidePointContainment:
                        # The tool is inside of the target, so remove it
                        bodies_copy[j] = None

    # Now find the volume of the disjoint bodies remaining
    volume = 0
    for body_copy in bodies_copy:
        if body_copy is None:
            continue
        volume += body_copy.volume
    return volume


def get_intersect_volume(bodies_one, bodies_two):
    """Get the intersection volume of two lists of bodies"""
    if len(bodies_one) == 0 or len(bodies_two) == 0:
        return 0.0
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)

    # Store which bodies are in each list
    bodies_group = {}
    for body in bodies_one:
        bodies_group[body.revisionId] = 1
    for body in bodies_two:
        bodies_group[body.revisionId] = 2

    # Create a collection of all bodies
    bodies = adsk.core.ObjectCollection.create()
    for body in bodies_one:
        bodies.add(body)
    for body in bodies_two:
        bodies.add(body)

    # Analyze interference
    input = design.createInterferenceInput(bodies)
    results = design.analyzeInterference(input)
    # Calculate the interference volumes
    # where the intersection is between the lists
    # not self-intersection within the list
    intersection_bodies = []
    for result in results:
        group_one = bodies_group[result.entityOne.revisionId]
        group_two = bodies_group[result.entityTwo.revisionId]
        # Make sure the intersection comes from between the groups
        if group_one != group_two:
            intersection_bodies.append(result.interferenceBody)

    num_intersection_bodies = len(intersection_bodies)
    if num_intersection_bodies == 0:
        return 0.0
    elif num_intersection_bodies == 1:
        return intersection_bodies[0].volume
    else:
        return get_union_volume(intersection_bodies, copy=False)


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
