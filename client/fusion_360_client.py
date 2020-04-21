import requests
import json
from pathlib import Path
import shutil


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

    def reconstruct(self, json_file):
        """Reconstruct a design from the provided json file"""
        if isinstance(json_file, str):
            json_file = Path(json_file)
        if not json_file.exists():
            return self.__return_error("JSON file does not exist")
        with open(json_file) as f:
            json_data = json.load(f)
        return self.send_command("reconstruct", json_data)

    def clear(self):
        """Clear (i.e. close) all open designs in Fusion"""
        return self.send_command("clear")

    def mesh(self, file):
        """Retreive a mesh in .stl format and write it to a local file"""
        command_data = {
            "format": "stl"
        }
        r = self.send_command("mesh", data=command_data, stream=True)
        self.__write_file(r, file)
        return r

    def sketch_images(self, folder):
        """Retreive each sketch as an image and save to a local folder"""
        pass

    def detach(self):
        """Detach the server from Fusion, taking it offline"""
        return self.send_command("detach")

    def __return_error(self, message):
        print(message)
        return None

    def __write_file(self, r, file):
        if r.status_code == 200:
            with open(file, "wb") as file_handle:
                for chunk in r.iter_content(chunk_size=128):
                    file_handle.write(chunk)
