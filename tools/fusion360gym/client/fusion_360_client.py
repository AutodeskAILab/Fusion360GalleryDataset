import requests
import json
from pathlib import Path
import shutil
import tempfile
from zipfile import ZipFile
import os

class Fusion360Client():

    def __init__(self, url="http://127.0.0.1:8080"):
        self.url = url
        self.feature_operations = [
            "JoinFeatureOperation",
            "CutFeatureOperation",
            "IntersectFeatureOperation",
            "NewBodyFeatureOperation"
        ]
        self.construction_planes = ["XY", "XZ", "YZ"]

    def send_command(self, command, data=None, stream=False):
        command_data = {
            "command": command,
        }
        if data is not None:
            command_data["data"] = data
        return requests.post(
            url=self.url,
            data=json.dumps(command_data),
            stream=stream
        )

    # -------------------------------------------------------------------------
    # RECONSTRUCTION
    # -------------------------------------------------------------------------

    def reconstruct(self, file):
        """Reconstruct a design from the provided json file"""
        if isinstance(file, str):
            file = Path(file)
        if not file.exists():
            return self.__return_error("JSON file does not exist")
        with open(file, encoding="utf8") as file_handle:
            json_data = json.load(file_handle)
        return self.send_command("reconstruct", json_data)

    def reconstruct_sketch(self, json_data, sketch_name, sketch_plane=None, scale=None, translate=None):
        """Reconstruct a sketch from the provided json data and sketch name"""
        if not isinstance(json_data, dict) or not bool(json_data):
            return self.__return_error("JSON data is invalid")
        if "timeline" not in json_data or "entities" not in json_data:
            return self.__return_error("JSON data is invalid")
        if not isinstance(sketch_name, str):
            return self.__return_error("Sketch name is not string")
        # check if the sketch name exists in the JSON data
        sketches = []
        timeline = json_data["timeline"]
        entities = json_data["entities"]
        for timeline_object in timeline:
            entity_uuid = timeline_object["entity"]
            entity_index = timeline_object["index"]
            entity = entities[entity_uuid]
            if entity["type"] == "Sketch":
                sketches.append(entity["name"])
        if sketch_name not in sketches:
            return self.__return_error("Sketch name doesn't exist")
        if sketch_plane is not None:
            is_str = isinstance(sketch_plane, str)
            is_int = isinstance(sketch_plane, int)
            is_dict = isinstance(sketch_plane, dict)
            if not is_str and not is_int and not is_dict:
                return self.__return_error(f"Invalid sketch_plane value")
            if is_str and sketch_plane not in self.construction_planes:
                    return self.__return_error(f"Invalid sketch_plane value")
            if is_dict:
                if ("x" not in sketch_plane or
                        "y" not in sketch_plane or
                        "z" not in sketch_plane):
                    return self.__return_error(f"Invalid sketch_plane value")
        if scale is not None:
            if not isinstance(scale, dict):
                return self.__return_error("Invalid scale dtype")
            if ("x" not in scale or
                "y" not in scale or
                "z" not in scale):
                return self.__return_error(f"Invalid key in scale")
            scale["type"] = "Vector3D"
        if translate is not None:
            if not isinstance(translate, dict):
                return self.__return_error("Invalid translate dtype")
            if ("x" not in translate or
                "y" not in translate or
                "z" not in translate):
                return self.__return_error(f"Invalid key in translate")
            translate["type"] = "Vector3D"
        command_data = {
            "json_data": json_data,
            "sketch_name": sketch_name
        }
        # Add optional args if they are defined
        if sketch_plane is not None:
            command_data["sketch_plane"] = sketch_plane
        if scale is not None:
            command_data["scale"] = scale
        if translate is not None:
            command_data["translate"] = translate
        return self.send_command("reconstruct_sketch", data=command_data)

    def clear(self):
        """Clear (i.e. close) all open designs in Fusion"""
        return self.send_command("clear")

    # -------------------------------------------------------------------------
    # INCREMENTAL CONSTRUCTION
    # -------------------------------------------------------------------------

    def add_sketch(self, sketch_plane):
        """Add a sketch to the design"""
        is_str = isinstance(sketch_plane, str)
        is_int = isinstance(sketch_plane, int)
        is_dict = isinstance(sketch_plane, dict)
        if not is_str and not is_int and not is_dict:
            return self.__return_error(f"Invalid sketch_plane value")
        if is_dict:
            if ("x" not in sketch_plane or
                    "y" not in sketch_plane or
                    "z" not in sketch_plane):
                return self.__return_error(f"Invalid sketch_plane value")

        command_data = {
            "sketch_plane": sketch_plane
        }
        return self.send_command("add_sketch", data=command_data)

    def add_point(self, sketch_name, pt, transform=None):
        """Add a point to create a new sequential line in the given sketch"""
        if not isinstance(sketch_name, str):
            return self.__return_error(f"Invalid sketch_name")
        pt_is_dict = isinstance(pt, dict)
        if not pt_is_dict or "x" not in pt or "y" not in pt:
            return self.__return_error(f"Invalid pt value")
        if "z" not in pt:
            pt["z"] = 0.0
        pt["type"] = "Point3D"
        command_data = {
            "sketch_name": sketch_name,
            "pt": pt
        }
        if transform is not None:
            if (isinstance(transform, dict) or
                    isinstance(transform, str)):
                command_data["transform"] = transform
        return self.send_command("add_point", data=command_data)

    def add_line(self, sketch_name, pt1, pt2, transform=None):
        """Add a line to the given sketch"""
        if not isinstance(sketch_name, str):
            return self.__return_error(f"Invalid sketch_name")
        pt1_is_dict = isinstance(pt1, dict)
        if not pt1_is_dict or "x" not in pt1 or "y" not in pt1:
            return self.__return_error(f"Invalid pt1 value")
        pt2_is_dict = isinstance(pt1, dict)
        if not pt2_is_dict or "x" not in pt2 or "y" not in pt2:
            return self.__return_error(f"Invalid pt2 value")
        if "z" not in pt1:
            pt1["z"] = 0.0
        if "z" not in pt2:
            pt2["z"] = 0.0
        pt1["type"] = "Point3D"
        pt2["type"] = "Point3D"
        command_data = {
            "sketch_name": sketch_name,
            "pt1": pt1,
            "pt2": pt2
        }
        if transform is not None:
            if (isinstance(transform, dict) or
                    isinstance(transform, str)):
                command_data["transform"] = transform
        return self.send_command("add_line", data=command_data)

    def close_profile(self, sketch_name):
        """Close the current set of lines to create one or more profiles
           by joining the first point to the last"""
        if not isinstance(sketch_name, str):
            return self.__return_error(f"Invalid sketch_name")
        command_data = {
            "sketch_name": sketch_name
        }
        return self.send_command("close_profile", data=command_data)

    def add_extrude(self, sketch_name, profile_id, distance, operation):
        """Add an extrude using the given sketch profile"""
        if (sketch_name is None or profile_id is None or
                distance is None or operation is None):
            return self.__return_error(f"Missing arguments")
        if not isinstance(sketch_name, str) or len(sketch_name) == 0:
            return self.__return_error(f"Invalid sketch_name value")
        if not isinstance(profile_id, str) or len(profile_id) == 0:
            return self.__return_error(f"Invalid profile_id value")
        if not isinstance(distance, (int, float, complex)):
            return self.__return_error(f"Invalid distance value")
        if operation not in self.feature_operations:
            return self.__return_error(f"Invalid operation value")
        command_data = {
            "sketch_name": sketch_name,
            "profile_id": profile_id,
            "distance": distance,
            "operation": operation
        }
        return self.send_command("add_extrude", data=command_data)

    # -------------------------------------------------------------------------
    # TARGET RECONSTRUCTION
    # -------------------------------------------------------------------------

    def set_target(self, file):
        """Set the target that we want to reconstruct with a .step or .smt file.
            This call will clear the current design"""
        if isinstance(file, str):
            file = Path(file)
        if not file.exists():
            return self.__return_error("Target file does not exist")
        suffix = file.suffix
        valid_formats = [".step", ".stp", ".smt"]
        if suffix not in valid_formats:
            return self.__return_error(f"Invalid file format: {suffix}")
        # Open the file and load the text
        with open(file, "r") as f:
            file_data = f.read()
        command_data = {
            "file": file.name,
            "file_data": file_data
        }
        return self.send_command("set_target", command_data)

    def revert_to_target(self):
        """Reverts to the target design, removing all reconstruction"""
        return self.send_command("revert_to_target")

    def add_extrude_by_target_face(self, start_face, end_face, operation):
        """Add an extrude between two faces of the target"""
        if not isinstance(start_face, str) or len(start_face) == 0:
            return self.__return_error(f"Invalid start_face value")
        if not isinstance(end_face, str) or len(end_face) == 0:
            return self.__return_error(f"Invalid end_face value")
        if operation not in self.feature_operations:
            return self.__return_error(f"Invalid operation value")
        command_data = {
            "start_face": start_face,
            "end_face": end_face,
            "operation": operation
        }
        return self.send_command("add_extrude_by_target_face", command_data)

    def add_extrudes_by_target_face(self, actions, revert=False):
        """Executes multiple extrude operations,
            between two faces of the target, in sequence"""
        if (actions is None or not isinstance(actions, list) or
           len(actions) == 0):
            return self.__return_error(f"Invalid actions")
        for action in actions:
            if ("start_face" not in action or
                    "end_face" not in action or
                    "operation" not in action):
                return self.__return_error(f"Invalid actions")
            start_face = action["start_face"]
            end_face = action["end_face"]
            operation = action["operation"]
            if not isinstance(start_face, str) or len(start_face) == 0:
                return self.__return_error(f"Invalid start_face value")
            if not isinstance(end_face, str) or len(end_face) == 0:
                return self.__return_error(f"Invalid end_face value")
            if operation not in self.feature_operations:
                return self.__return_error(f"Invalid operation value")
        command_data = {
            "actions": actions,
            "revert": revert
        }
        return self.send_command("add_extrudes_by_target_face", command_data)

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def mesh(self, file):
        """Retreive a mesh in .obj or .stl format
            and write it to a local file"""
        if isinstance(file, str):
            file = Path(file)            
        suffix = file.suffix
        valid_formats = [".obj", ".stl"]
        if suffix not in valid_formats:
            return self.__return_error(f"Invalid file format: {suffix}")
        command_data = {
            "file": file.name
        }
        r = self.send_command("mesh", data=command_data, stream=True)
        self.__write_file(r, file)
        return r

    def brep(self, file):
        """Retreive a brep in a .step, .smt, or .f3d format
            and write it to a local file"""
        if isinstance(file, str):
            file = Path(file)
        suffix = file.suffix
        valid_formats = [".step", ".smt", ".f3d"]
        if suffix not in valid_formats:
            return self.__return_error(f"Invalid file format: {suffix}")
        command_data = {
            "file": file.name
        }
        r = self.send_command("brep", data=command_data, stream=True)
        self.__write_file(r, file)
        return r

    def sketches(self, dir, format=".png"):
        """Retreive each sketch in a given format (e.g. .png, .dxf)
            and save to a local directory"""
        if not dir.is_dir():
            return self.__return_error(f"Not an existing directory")
        valid_formats = [".png", ".dxf"]
        if format not in valid_formats:
            return self.__return_error(f"Invalid file format: {format}")
        command_data = {
            "format": format
        }
        r = self.send_command("sketches", data=command_data, stream=True)
        if r.status_code != 200:
            return r
        # Save out the zip file with the sketch data
        temp_file_handle, temp_file_path = tempfile.mkstemp(suffix=".zip")
        zip_file = Path(temp_file_path)
        self.__write_file(r, zip_file)
        # Extract all the files to the given directory
        with ZipFile(zip_file, "r") as zipObj:
            zipObj.extractall(dir)
        zip_file.unlink()
        return r

    def screenshot(self, file, width=512, height=512, fit_camera=True):
        """Retreive a screenshot of the current design as a png image"""
        if isinstance(file, str):
            file = Path(file)
        suffix = file.suffix
        if suffix != ".png":
            return self.__return_error(f"Invalid file format: {suffix}")
        if not isinstance(width, int) or not isinstance(height, int):
            return self.__return_error("Invalid width/height")
        if not isinstance(fit_camera, bool):
            return self.__return_error("Invalid value for fit_camera")
        command_data = {
            "file": file.name,
            "width": width,
            "height": height,
            "fit_camera": fit_camera
        }
        r = self.send_command("screenshot", data=command_data, stream=True)
        self.__write_file(r, file)
        return r

    def graph(self, file, dir, format="PerFace"):
        """Retreive a face adjacency graph in a given format"""
        if isinstance(file, str):
            file = Path(file)
        if not dir.is_dir():
            return self.__return_error(f"Not an existing directory")
        valid_formats = ["PerFace", "PerExtrude"]
        if format not in valid_formats:
            return self.__return_error(f"Invalid graph format: {format}")
        command_data = {
            "file": file.name,
            "format": format
        }
        r = self.send_command("graph", data=command_data, stream=True)
        if r.status_code != 200:
            return r
        # Save out the zip file with the graph data
        temp_file_handle, temp_file_path = tempfile.mkstemp(suffix=".zip")
        zip_file = Path(temp_file_path)
        self.__write_file(r, zip_file)
        # Extract all the files to the given directory
        with ZipFile(zip_file, "r") as zipObj:
            zipObj.extractall(dir)
        os.close(temp_file_handle)
        zip_file.unlink()
        return r

    # -------------------------------------------------------------------------
    # UTILITY
    # -------------------------------------------------------------------------

    def ping(self):
        """Ping for debugging"""
        return self.send_command("ping")

    def refresh(self):
        """Refresh the active viewport"""
        return self.send_command("refresh")

    def detach(self):
        """Detach the server from Fusion, taking it offline,
            allowing the Fusion UI to become responsive again"""
        return self.send_command("detach")

    def commands(self, command_list, dir=None):
        """Send a series of commands to the server"""
        if dir is not None:
            if not dir.is_dir():
                return self.__return_error(f"Not an existing directory")
        if (command_list is None or not isinstance(command_list, list) or
           len(command_list) == 0):
            return self.__return_error(
                "Command list argument missing or not a populated list")
        # Flag to mark down if we will get a binary back
        binary_response = False
        # Check that each command_set has a command
        for command_set in command_list:
            if "command" not in command_set:
                return self.__return_error(
                    "Command list command argument missing")
            command = command_set["command"]
            if command in ["mesh", "brep", "sketches"]:
                binary_response = True
        # We are getting a file back
        if binary_response:
            r = self.send_command("commands", data=command_list, stream=True)
            if r.status_code != 200:
                return r
            temp_file_handle, temp_file_path = tempfile.mkstemp(suffix=".zip")
            zip_file = Path(temp_file_path)
            self.__write_file(r, zip_file)
            # Extract all the files to the given directory
            with ZipFile(zip_file, "r") as zipObj:
                zipObj.extractall(dir)
            zip_file.unlink()
            return r
        else:
            return self.send_command("commands", command_list)

    # -------------------------------------------------------------------------
    # PRIVATE
    # -------------------------------------------------------------------------

    def __return_error(self, message):
        print(message)
        return None

    def __write_file(self, r, file):
        if r.status_code == 200:
            with open(file, "wb") as file_handle:
                for chunk in r.iter_content(chunk_size=128):
                    file_handle.write(chunk)
