""""

Fusion 360 Gym face extrusion based reconstruction

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
    # SETUP
    # Create the client class to interact with the server
    client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")
    # Clear to force close all documents in Fusion
    r = client.clear()

    # Get our target design file
    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "testdata"
    couch_design_smt_file = data_dir / "Couch.smt"
    # Set the target
    r = client.set_target(couch_design_smt_file)
    # The face adjacency graph is returned
    # which we use to pick nodes for face extrusion
    response_json = r.json()
    graph = response_json["data"]["graph"]
    nodes = graph["nodes"]
    # A series of actions to extrude from node to node in the graph
    r = client.add_extrudes_by_target_face([
        {
            "start_face": nodes[0]["id"],
            "end_face": nodes[9]["id"],
            "operation": "NewBodyFeatureOperation"
        },
        {
            "start_face": nodes[1]["id"],
            "end_face": nodes[3]["id"],
            "operation": "JoinFeatureOperation"
        }
    ])
    response_json = r.json()
    response_data = response_json["data"]
    iou = response_data["iou"]
    print(f"Finished creating design using face extrusion with IoU value of {iou}")


if __name__ == "__main__":
    main()
