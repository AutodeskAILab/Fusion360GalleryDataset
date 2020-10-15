""""

Fusion 360 Gym sketch extrusion based construction using lines

"""

from pathlib import Path
import sys
import os
import json

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)

from fusion360gym_client import Fusion360GymClient


# Before running ensure the Fusion360Server is running
# and configured with the same host name and port number
HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


def main():
    # SETUP
    # Create the client class to interact with the server
    client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")
    # Clear to force close all documents in Fusion
    # Do this before a new reconstruction
    r = client.clear()

    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "testdata"
    output_dir = data_dir / "output"
    if not output_dir.exists():
        output_dir.mkdir()

    # Send a list of commands directly to the server to run in sequence
    # We need to load the json as a dict to reconstruct
    # NOTE: this will not work for all files
    # only ones with single profiles (or the first profile used) in a sketch
    couch_design_json_file = data_dir / "Couch.json"
    with open(couch_design_json_file) as file_handle:
        couch_design_json_data = json.load(file_handle)

    timeline = couch_design_json_data["timeline"]
    entities = couch_design_json_data["entities"]
    # Pull out just the profiles that are used for extrude operations
    profiles_used = get_extrude_profiles(timeline, entities)

    sketches = {}
    for timeline_object in timeline:
        entity_key = timeline_object["entity"]
        entity = entities[entity_key]
        if entity["type"] == "Sketch":
            sketches[entity_key] = add_sketch(client, entity, entity_key, profiles_used)
        elif entity["type"] == "ExtrudeFeature":
            add_extrude_feature(client, entity, entity_key, sketches)
    print("Finished creating design using add_line and add_extrude")


def get_extrude_profiles(timeline, entities):
    """Get the profiles used with extrude operations"""
    profiles = set()
    for timeline_object in timeline:
        entity_key = timeline_object["entity"]
        entity = entities[entity_key]
        if entity["type"] == "ExtrudeFeature":
            for profile in entity["profiles"]:
                profiles.add(profile["profile"])
    return profiles


def add_sketch(client, sketch, sketch_id, profiles_used):
    """Add a sketch to the design"""
    # First we need a plane to sketch on
    ref_plane = sketch["reference_plane"]
    ref_plane_type = ref_plane["type"]
    # Default to making a sketch on the XY plane
    sketch_plane = "XY"
    if ref_plane_type == "ConstructionPlane":
        # Use the name as a reference to the plane axis
        sketch_plane = ref_plane["name"]
    elif ref_plane_type == "BRepFace":
        # Identify the face by a point that sits on it
        sketch_plane = ref_plane["point_on_face"]
    r = client.add_sketch(sketch_plane)
    # Get the sketch name back
    response_json = r.json()
    sketch_name = response_json["data"]["sketch_name"]
    profile_ids = add_profiles(client, sketch_name, sketch, profiles_used)
    return {
        "sketch_name": sketch_name,
        "profile_ids": profile_ids
    }


def add_profiles(client, sketch_name, sketch, profiles_used):
    """Add the sketch profiles to the design"""
    profiles = sketch["profiles"]
    original_curves = sketch["curves"]
    transform = sketch["transform"]
    profile_ids = {}
    response_json = None
    for original_profile_id, profile in profiles.items():
        # Check if this profile is used
        if original_profile_id in profiles_used:
            for loop in profile["loops"]:
                for curve in loop["profile_curves"]:
                    if curve["type"] != "Line3D":
                        print(f"Warning: Unsupported curve type - {curve['type']}")
                        continue
                    # Skip over curves that are construction geometry
                    curve_id = curve["curve"]
                    curve_construction_geom = original_curves[curve_id]["construction_geom"]
                    if curve_construction_geom:
                        continue
                    # We have to send the sketch transform here
                    # due to the way Fusion saves out data from designs
                    r = client.add_line(sketch_name, curve["start_point"], curve["end_point"], transform)
                    response_json = r.json()
            # Look at the response and add profiles to the lookup dict
            # mapping between the original uuids and the profiles
            response_data = response_json["data"]
            for re_profile in response_data["profiles"]:
                profile_ids[original_profile_id] = re_profile
                # Note we make a silly assumption that its always the first
                # profile we use, so we return early here
                # when there could be many profiles in a sketch
                return profile_ids


def add_extrude_feature(client, extrude_feature, extrude_feature_id, sketches):
    """Add an extrude feature to the design"""
    # We only handle a single profile
    original_profile_id = extrude_feature["profiles"][0]["profile"]
    original_sketch_id = extrude_feature["profiles"][0]["sketch"]
    # Use the original ids to find the new ids
    sketch_name = sketches[original_sketch_id]["sketch_name"]
    profile_id = sketches[original_sketch_id]["profile_ids"][original_profile_id]
    # Pull out the other extrude parameters
    distance = extrude_feature["extent_one"]["distance"]["value"]
    operation = extrude_feature["operation"]
    # Add the extrude
    r = client.add_extrude(sketch_name, profile_id, distance, operation)
    response_json = r.json()
    response_data = response_json["data"]
    # response_data contains a lot of information about:
    # - face adjacency graph: response_data["graph"]
    # - extrude faces: response_data["extrude"]
    # - bounding box: response_data["bounding_box"]


if __name__ == "__main__":
    main()
