import adsk.core
import adsk.fusion
import uuid
import json
import math


def get_uuid(entity, group_name="Dataset"):
    if isinstance(entity, adsk.fusion.Profile):
        return get_profile_uuid(entity)
    else:
        try:
            if entity is None:
                return None
            uuid_att = entity.attributes.itemByName(group_name, "uuid")
            if uuid_att is not None:
                return uuid_att.value
            else:
                # Return None to allow for workarounds
                return None
        except:
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


def set_uuid(entity, group_name="Dataset"):
    uuid_att = entity.attributes.itemByName(group_name, "uuid")
    if uuid_att is None:
        unique_id = uuid.uuid1()
        entity.attributes.add(group_name, "uuid", str(unique_id))
        return str(unique_id)
    return uuid_att.value


def set_custom_uuid(entity, custom_uuid, group_name="Dataset"):
    entity.attributes.add(group_name, "uuid", custom_uuid)


def set_uuids_for_collection(entities, group_name="Dataset"):
    for ent in entities:
        if ent is not None:
            set_uuid(ent, group_name)
