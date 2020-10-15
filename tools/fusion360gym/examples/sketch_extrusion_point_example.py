""""

Fusion 360 Gym sketch extrusion based construction using points

"""

from pathlib import Path
import sys
import os
import json
import random

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
    # Create the client class to interact with the server
    client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")
    # Clear to force close all documents in Fusion
    r = client.clear()

    # Create an empty sketch on a random plane
    planes = ["XY", "XZ", "YZ"]
    random_plane = random.choice(planes)
    r = client.add_sketch(random_plane)
    # Get the unique name of the sketch created
    response_json = r.json()
    sketch_name = response_json["data"]["sketch_name"]
    # Add four lines to the sketch to make a square
    pts = [
        {"x": -5, "y": -5},
        {"x": 5, "y": -5},
        {"x": 5, "y": 5},
        {"x": -5, "y": 5}
    ]
    for pt in pts:
        client.add_point(sketch_name, pt)
    r = client.close_profile(sketch_name)

    # Pull out the first profile id
    response_json = r.json()
    response_data = response_json["data"]
    profile_id = next(iter(response_data["profiles"]))
    random_distance = random.randrange(5, 10)
    # Extrude by a random distance to make a new body
    r = client.add_extrude(sketch_name, profile_id, random_distance, "NewBodyFeatureOperation")

    # Pick a random face for the next sketch
    response_json = r.json()
    response_data = response_json["data"]
    faces = response_data["extrude"]["faces"]
    random_face = random.choice(faces)
    # Create a second sketch on a random face
    r = client.add_sketch(random_face["face_id"])
    response_json = r.json()
    sketch_name = response_json["data"]["sketch_name"]
    # Draw the second smaller square
    pts = [
        {"x": 2, "y": 2},
        {"x": 3, "y": 2},
        {"x": 3, "y": 3},
        {"x": 2, "y": 3}
    ]
    for pt in pts:
        r = client.add_point(sketch_name, pt)
    r = client.close_profile(sketch_name)

    # Pull out the first profile id
    response_json = r.json()
    response_data = response_json["data"]
    profile_id = next(iter(response_data["profiles"]))
    # Extrude by a given distance, adding to the existing body
    random_distance = random.randrange(1, 5)
    # operations = ["JoinFeatureOperation", "CutFeatureOperation", "IntersectFeatureOperation", "NewBodyFeatureOperation"]
    r = client.add_extrude(sketch_name, profile_id, random_distance, "JoinFeatureOperation")

    # Its also possible to do different extrude operations here, for example a cut with a negative extrude value
    # random_distance = random.randrange(-5, -1)
    # r = client.add_extrude(sketch_name, profile_id, random_distance, "CutFeatureOperation")

    print("Finished creating design using add_point and add_extrude")


if __name__ == "__main__":
    main()
