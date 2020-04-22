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
        with open(file) as f:
            json_data = json.load(f)
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
            "format": suffix
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
            "format": suffix
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
        # Save out the zip file with the sketch data
        temp_file = tempfile.NamedTemporaryFile(suffix=".zip")
        temp_file.close()
        self.__write_file(r, temp_file.name)
        # Extract all the files to the given directory
        with ZipFile(temp_file.name, "r") as zipObj:
            zipObj.extractall(dir)
        return r

    def detach(self):
        """Detach the server from Fusion, taking it offline, allowing the Fusion UI to become responsive again"""
        return self.send_command("detach")

    def __return_error(self, message):
        print(message)
        return None

    def __write_file(self, r, file):
        if r.status_code == 200:
            with open(file, "wb") as file_handle:
                for chunk in r.iter_content(chunk_size=128):
                    file_handle.write(chunk)
