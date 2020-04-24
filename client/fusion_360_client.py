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
        return requests.post(url=self.url, data=json.dumps(command_data), stream=stream)

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
        """Retreive a mesh in .stl format and write it to a local file"""
        suffix = file.suffix
        valid_formats = [".stl"]
        if suffix not in valid_formats:
            return self.__return_error(f"Invalid file format: {suffix}")
        command_data = {
            "file": file.name
        }
        r = self.send_command("mesh", data=command_data, stream=True)
        self.__write_file(r, file)
        return r

    def brep(self, file):
        """Retreive a brep in a format (step/smt) and write it to a local file"""
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
        """Retreive each sketch in a given format (e.g. .png, .dxf) and save to a local directory"""
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
        """Detach the server from Fusion, taking it offline, allowing the Fusion UI to become responsive again"""
        return self.send_command("detach")

    def commands(self, command_list, dir=None):
        """Send a series of commands to the server"""
        if dir is not None:
            if not dir.is_dir():
                return self.__return_error(f"Not an existing directory")
        if command_list is None or not isinstance(command_list, list) or len(command_list) == 0:
            return self.__return_error("Command list argument missing or not a populated list")
        # Flag to mark down if we will get a binary back
        binary_response = False
        # Check that each command_set has a command
        for command_set in command_list:
            if "command" not in command_set:
                return self.__return_error("Command list command argument missing")
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

    def __return_error(self, message):
        print(message)
        return None

    def __write_file(self, r, file):
        if r.status_code == 200:
            with open(file, "wb") as file_handle:
                for chunk in r.iter_content(chunk_size=128):
                    file_handle.write(chunk)
