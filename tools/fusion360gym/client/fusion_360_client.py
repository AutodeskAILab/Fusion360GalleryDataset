import requests
import json
from pathlib import Path
import shutil
import tempfile
from zipfile import ZipFile


class Fusion360Client():

    def __init__(self, url="http://127.0.0.1:8080"):
        self.url = url

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

    def ping(self):
        """Ping for debugging"""
        return self.send_command("ping")

    def refresh(self):
        """Refresh the active viewport"""
        return self.send_command("refresh")

    def reconstruct(self, file):
        """Reconstruct a design from the provided json file"""
        if isinstance(file, str):
            file = Path(file)
        if not file.exists():
            return self.__return_error("JSON file does not exist")
        with open(file) as file_handle:
            json_data = json.load(file_handle)
        return self.send_command("reconstruct", json_data)

    def clear(self):
        """Clear (i.e. close) all open designs in Fusion"""
        return self.send_command("clear")

    def mesh(self, file):
        """Retreive a mesh in .obj or .stl format
            and write it to a local file"""
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
        """Retreive a brep in a .step or .smt format
            and write it to a local file"""
        suffix = file.suffix
        valid_formats = [".step", ".smt"]
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
        if not isinstance(sketch_name, str):
            return self.__return_error(f"Invalid sketch_name value")
        if not isinstance(profile_id, str):
            return self.__return_error(f"Invalid profile_id value")
        if not isinstance(distance, (int, float, complex)):
            return self.__return_error(f"Invalid distance value")
        if not isinstance(operation, str):
            return self.__return_error(f"Invalid operation value")
        command_data = {
            "sketch_name": sketch_name,
            "profile_id": profile_id,
            "distance": distance,
            "operation": operation
        }
        return self.send_command("add_extrude", data=command_data)

    def __return_error(self, message):
        print(message)
        return None

    def __write_file(self, r, file):
        if r.status_code == 200:
            with open(file, "wb") as file_handle:
                for chunk in r.iter_content(chunk_size=128):
                    file_handle.write(chunk)
