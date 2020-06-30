import adsk.core
import adsk.fusion

import data_util


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


def get_vertex_valence_tally(entity):
    """ Return a tally of the vertex valence:
        number of edges connected to each vertex"""
    bodies = __get_bodies_from_entity(entity)
    valence_tally = {}

    for body in bodies:
        for vertex in body.vertices:
            edge_count = vertex.edges.count
            if edge_count not in valence_tally:
                valence_tally[edge_count] = 0
            valence_tally[edge_count] += 1

    valence_list = []
    for key, value in valence_tally.items():
        valence_list.append({
            "valence": key,
            "count": value
        })
    return valence_list


def get_brep_bodies_bounding_box(bodies):
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


def get_surface_types_tally(entity):
    """Return a tally of the types of surfaces
        in a component, occurrence or body"""
    bodies = []
    surface_type_tally = {}

    if (isinstance(entity, adsk.fusion.Component) or
       isinstance(entity, adsk.fusion.Occurrence)):
        bodies = entity.bRepBodies
    elif isinstance(entity, adsk.fusion.BRepBody):
        bodies = [entity]
    else:
        raise Exception(f"Unexpected entity type: {entity.classType()}")

    for body in bodies:
        for face in body.faces:
            surface_type = data_util.get_surface_type(face.geometry)
            if surface_type not in surface_type_tally:
                surface_type_tally[surface_type] = 0
            surface_type_tally[surface_type] += 1

    surface_type_list = []
    for key, value in surface_type_tally.items():
        surface_type_list.append({
            "surface_type": key,
            "face_count": value
        })
    return surface_type_list


def get_temp_ids_from_faces(faces):
    """From a collection of faces make a set of the tempids"""
    id_set = set()
    for face in faces:
        if face is not None:
            temp_id = face.tempId
            id_set.add(temp_id)
    return id_set


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
