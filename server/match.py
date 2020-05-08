
import adsk.core
import adsk.fusion

from . import deserialize
from . import name


def sketch(sketch_id):
    """Return a sketch with a given id"""
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    for sketch in design.rootComponent.sketches:
        uuid = name.get_uuid(sketch_id)
        if uuid is not None:
            return sketch
    return None


def sketch_plane(sketch_plane_data):
    """Return the sketch plane to create a sketch on"""
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    # String for brepface or construction plane
    if isinstance(sketch_plane_data, str):
        # Look for construction plane first
        construction_plane = deserialize.construction_plane(sketch_plane_data)
        if construction_plane is not None:
            return construction_plane
        # Now lets see if it is a brep tempid
        brep_face = face_by_temp_id(sketch_plane_data)
        if brep_face is not None:
            return brep_face
    elif isinstance(sketch_plane_data, dict):
        point_on_face = deserialize.point3d(sketch_plane_data)
        brep_face = face_by_point3d(point_on_face)
        if brep_face is not None:
            return brep_face
    return None


def face_by_temp_id(temp_id):
    """Find a face with a given tempid"""
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    for component in design.allComponents:
        for body in component.bRepBodies:
            try:
                entities = body.findByTempId(temp_id)
                if entities is None or len(entities) == 0:
                    continue
                else:
                    return entities[0]
            except:
                # Ignore and keep looking
                pass
    return None


def face_by_point3d(point3d):
    """Find a face with given point3d that sits on that face"""
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    for component in design.allComponents:
        try:
            entities = component.findBRepUsingPoint(point3d, adsk.fusion.BRepEntityTypes.BRepFaceEntityType)
            if entities is None or len(entities) == 0:
                continue
            else:
                return entities[0]
        except:
            # Ignore and keep looking
            pass
    return None
