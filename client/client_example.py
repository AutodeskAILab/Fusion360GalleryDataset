from pathlib import Path
import sys
import os
import json
from fusion_360_client import Fusion360Client

# Before running ensure the Fusion360Server is running
# and configured with the same host name and port number
HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


def main():
    current_dir = Path(__file__).parent
    root_dir = current_dir.parent
    data_dir = root_dir / "data"
    output_dir = data_dir / "output"
    if not output_dir.exists():
        output_dir.mkdir()

    # SETUP
    # Create the client class to interact with the server
    client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")
    # Clear to force close all documents in Fusion
    # Do this before a new reconstruction
    r = client.clear()
    # Example of how we read the response data
    response_data = r.json()
    print(f"[{r.status_code}] Response: {response_data['message']}")

    # RECONSTRUCT
    # The json file with our design
    box_design_json_file = data_dir / "SingleSketchExtrude_RootComponent.json"
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
    r = client.clear()

    # COMMANDS
    # Send a list of commands directly to the server to run in sequence
    # We need to load the json as a dict to reconstruct
    hex_design_json_file = data_dir / "Z0HexagonCutJoin_RootComponent.json"
    with open(hex_design_json_file) as file_handle:
        hex_design_json_data = json.load(file_handle)
    # All the output will go into this folder
    hex_design_dir = output_dir / "hex_design"
    if not hex_design_dir.exists():
        hex_design_dir.mkdir()
    # Set a name for the mesh file we will get back
    hex_design_mesh_file = hex_design_dir / "hex_design.stl"
    # Construct the command list
    command_list = [
        {
            "command": "reconstruct",
            "data": hex_design_json_data
        },
        {
            "command": "sketches",
            "data": {
                "format": ".png"
            }
        },
        {
            "command": "mesh",
            "data": {
                "file": hex_design_mesh_file.name
            }
        },
        {"command": "clear"}
    ]
    # Run the command
    r = client.commands(command_list, hex_design_dir)
    r = client.clear()

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
