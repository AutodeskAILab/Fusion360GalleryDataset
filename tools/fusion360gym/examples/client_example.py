"""

Simple example showing usage of the Fusion 360 Gym Client

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

# Before running ensure the Fusion360GymServer is running
# and configured with the same host name and port number
HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


def main():
    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent.parent / "testdata"
    output_dir = data_dir / "output"
    if not output_dir.exists():
        output_dir.mkdir()

    # SETUP
    # Create the client class to interact with the server
    client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")
    # Clear to force close all documents in Fusion
    # Do this before a new reconstruction
    r = client.clear()
    # Example of how we read the response data
    response_data = r.json()
    print(f"[{r.status_code}] Response: {response_data['message']}")

    # RECONSTRUCT
    # The json file with our design
    box_design_json_file = data_dir / "SingleSketchExtrude.json"
    # First clear to start fresh
    r = client.clear()
    r = client.reconstruct(box_design_json_file)

    # MESH
    # Create an stl file in the data directory
    stl_file = output_dir / "test.stl"
    r = client.mesh(stl_file)

    # BREP
    # Create a 'step' file
    # Or change the file extension to 'smt' to save in that format
    step_file = output_dir / "test.step"
    r = client.brep(step_file)

    # SKETCHES
    # Create a directory for the sketches to go in
    sketch_dir = output_dir / "sketches"
    if not sketch_dir.exists():
        sketch_dir.mkdir()
    # By default sketches are saves as png images
    r = client.sketches(sketch_dir)
    # Or we can export vector data as .dxf
    r = client.sketches(sketch_dir, ".dxf")

    # OTHER
    # Ping: check if the server is responding
    r = client.ping()
    # Refresh: force the ui to refresh
    r = client.refresh()
    # Detach: stop the server so Fusion becomes responsive again
    # r = client.detach()

    # DEBUGGING
    # # Uncomment to send an invalid file and show some error info
    # invalid_json_file = data_dir / "SingleSketchExtrude_Invalid.json"
    # r = client.reconstruct(invalid_json_file)
    # response_data = r.json()
    # # This will spew out the errors we caught on the server and the stack trace
    # print(f"[{r.status_code}] Response message: {response_data['message']}")

    print(f"Done! Check this folder for exported files: {output_dir}")


if __name__ == "__main__":
    main()
