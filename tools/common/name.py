"""

Give and get names for Fusion 360 entities

"""


import adsk.core
import adsk.fusion
import uuid
import json
import math


def get_uuid(entity, group_name="Dataset"):
    if isinstance(entity, adsk.fusion.Profile):
        return get_profile_uuid(entity)
    elif isinstance(entity, adsk.fusion.BRepFace):
        return get_brep_face_uuid(entity, group_name)
    else:
        uuid_att = entity.attributes.itemByName(group_name, "uuid")
        if uuid_att is not None:
            return uuid_att.value
        else:
            # Return None to allow for workarounds
            return None


def get_brep_face_uuid(entity, group_name):
    """Handle the special case of split brep faces with the same uuid"""
    uuid_att = entity.attributes.itemByName(group_name, "uuid")
    return get_brep_face_uuid_from_attribute(entity, uuid_att)


def get_brep_face_uuid_from_attribute(entity, uuid_att):
    """Handle the special case of split brep faces with the same uuid"""
    if uuid_att is None:
        return None
    # First check if this Face was previously split
    if (uuid_att.otherParents is not None and
            uuid_att.otherParents.count > 0):
        # Now we know we have a split face
        # because it has another parent
        # Next lets see if this face is the original face
        # or if was newly created from the split
        for parent in uuid_att.otherParents:
            if isinstance(parent, adsk.fusion.BRepFace):
                is_original = entity.tempId == parent.tempId
                # The original face keeps its uuid
                if is_original:
                    return uuid_att.value
        # Now we know we are the newly created split face
        # so we have to make a uuid
        # Due to a bug in Fusion we can't assign a new id
        # as an attribute on the split face, so we append the
        # number of parents at the end of the uuid
        uuid_concat = f"{uuid_att.value}_{uuid_att.otherParents.count}"
        return str(uuid.uuid3(uuid.NAMESPACE_URL, uuid_concat))
    else:
        # The face was not split, so we are good to go
        return uuid_att.value


def get_profile_uuid(profile):
    """Sketch profiles don"t support attributes
        so we cook up a UUID from the curves UUIDs"""
    profile_curves = []
    for loop in profile.profileLoops:
        for curve in loop.profileCurves:
            sketch_ent = curve.sketchEntity
            profile_curves.append(get_uuid(sketch_ent))
    # Concat all the uuids from the curves
    curve_uuids = "_".join(profile_curves)
    # Generate a UUID by hashing the curve_uuids
    return str(uuid.uuid3(uuid.NAMESPACE_URL, curve_uuids))


def set_uuid(entity, group_name="Dataset"):
    """Set a uuid of an entity
        Returns the new or existing uuid of the entity"""
    if isinstance(entity, adsk.fusion.BRepFace):
        return set_brep_face_uuid(entity, group_name)
    uuid_att = entity.attributes.itemByName(group_name, "uuid")
    if uuid_att is None:
        unique_id = uuid.uuid1()
        entity.attributes.add(group_name, "uuid", str(unique_id))
        return str(unique_id)
    else:
        return uuid_att.value


def set_brep_face_uuid(entity, group_name="Dataset"):
    """Handle the special case of split brep faces with a parent"""
    uuid_att = entity.attributes.itemByName(group_name, "uuid")
    entity_uuid = get_brep_face_uuid_from_attribute(entity, uuid_att)
    # uuid will always be returned if this is a split face
    # as a special version of the parent uuid is returned
    if entity_uuid is not None:
        # We already have a uuid, so use it
        return entity_uuid
    # Add a uuid directly to the face
    unique_id = uuid.uuid1()
    entity.attributes.add(group_name, "uuid", str(unique_id))
    return str(unique_id)


def reset_uuid(entity, group_name="Dataset"):
    """Reset a uuid of an entity
        Returns the reset uuid of the entity"""
    unique_id = uuid.uuid1()
    entity.attributes.add(group_name, "uuid", str(unique_id))
    return str(unique_id)


def set_custom_uuid(entity, custom_uuid, group_name="Dataset"):
    entity.attributes.add(group_name, "uuid", custom_uuid)


def set_uuids_for_collection(entities, group_name="Dataset"):
    for ent in entities:
        # Strange -- We sometimes get an None entity in the contraints array
        # when we have a SketchFixedSpline in the sketch.  We guard against
        # that crashing the threads here
        if ent is not None:
            set_uuid(ent, group_name)


def get_uuids_for_collection(entities, group_name="Dataset"):
    """Return a list of uuids from a collection"""
    uuids = []
    for ent in entities:
        # Strange -- We sometimes get an None entity in the contraints array
        # when we have a SketchFixedSpline in the sketch.  We guard against
        # that crashing the threads here
        if ent is not None:
            uuid = get_uuid(ent)
            uuids.append(uuid)
    return uuids


def set_uuids_for_sketch(sketch, group_name="Dataset"):
    # Work around to ensure the profiles are populated
    # on a newly opened design
    sketch.isComputeDeferred = True
    sketch.isVisible = False
    sketch.isVisible = True
    sketch.isComputeDeferred = False
    # We are only interested points and curves
    set_uuids_for_collection(sketch.sketchCurves)
    set_uuids_for_collection(sketch.sketchPoints)


def get_temp_ids_from_collection(collection):
    """From a collection, make a set of the tempids"""
    id_set = set()
    for entity in collection:
        if entity is not None:
            temp_id = entity.tempId
            id_set.add(temp_id)
    return id_set
