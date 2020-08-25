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
    all_bodies = adsk.core.ObjectCollection.create()
    for body in component_one.bRepBodies:
        all_bodies.add(body)
    for body in component_two.bRepBodies:
        all_bodies.add(body)
    union_volume = get_union_volume(all_bodies)
    intersect_volume = get_intersect_volume(all_bodies)
    return intersect_volume / union_volume


def get_union_volume(bodies):
    """Get the unioned volume of a set of bodies"""
    if len(bodies) == 0:
        return 0.0
    if len(bodies) == 1:
        return bodies[0].volume

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    timeline = app.activeProduct.timeline
    prev_timeline_position = timeline.markerPosition
    # We use combine here as it handles multiple tools
    # we could use TemporaryBRepManager.booleanOperation
    # for a speed up if we add handling for multiple bodies
    combines = design.rootComponent.features.combineFeatures
    first_body = bodies[0]
    tools = adsk.core.ObjectCollection.create()
    for index in range(1, len(bodies)):
        tools.add(body[index])
    combine_input = combines.createInput(first_body, tools)
    # combine_input.isKeepToolBodies = True
    # combine_input.isNewComponent = True
    combine = combines.add(combine_input)
    volume = 0
    for body in combine.bodies:
        volume += body.volume
    # Revert the timeline
    timeline.markerPosition = prev_timeline_position
    timeline.deleteAllAfterMarker()
    return volume


def get_intersect_volume(bodies):
    """Get the intersection volume of a set of bodies"""
    if len(bodies) == 0:
        return 0.0
    if len(bodies) == 1:
        return bodies[0].volume
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    # Analyze interference
    input = design.createInterferenceInput(bodies)
    results = design.analyzeInterference(input)
    # Calculate the interference volumes
    volume = 0
    for result in results:
        volume += result.interferenceBody.volume
    return volume


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
