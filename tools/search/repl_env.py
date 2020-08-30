
import sys
import os
import json
import time
from pathlib import Path
from requests.exceptions import ConnectionError


# Add the client folder to sys.path
COMMON_DIR = os.path.join(os.path.dirname(__file__), "..", "common")
GYM_DIR = os.path.join(os.path.dirname(__file__), "..", "fusion360gym")
CLIENT_DIR = os.path.join(GYM_DIR, "client")
SERVER_DIR = os.path.join(GYM_DIR, "server")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

from fusion_360_client import Fusion360Client
from launcher import Launcher


class ReplEnv():

    def __init__(self, host="127.0.0.1", port=8080, launch_gym=False):
        self.host = host
        self.port = port
        self.client = Fusion360Client(f"http://{self.host}:{self.port}")
        # Fusion subprocess
        self.p = None
        if launch_gym:
            self.launch_gym()

    def set_target(self, target_file):
        """Setup search and connect to the Fusion Gym"""
        # Set the target
        r = self.client.set_target(target_file)
        self.__check_response("set_target", r)
        response_json = r.json()
        if "data" not in response_json or "graph" not in response_json["data"]:
            raise Exception("[set_target] response graph missing")
        return response_json["data"]["graph"]

    def revert_to_target(self):
        """Revert to the target to start the search again"""
        r = self.client.revert_to_target()
        self.__check_response("revert_to_target", r)
        response_json = r.json()
        if "data" not in response_json or "graph" not in response_json["data"]:
            raise Exception("[revert_to_target] response graph missing")
        return response_json["data"]["graph"]

    def get_empty_graph(self):
        """Get an empty graph to kick things off"""
        return {
            "directed": False,
            "multigraph": False,
            "graph": {},
            "nodes": [],
            "links": []
        }

    def extrude(self, start_face, end_face, operation):
        """Extrude wrapper around the gym client"""
        is_invalid = False
        return_graph = None
        return_iou = None
        r = self.client.add_extrude_by_target_face(
            start_face, end_face, operation)
        if r is not None and r.status_code == 200:
            response_json = r.json()
            if ("data" in response_json and
                    "graph" in response_json["data"] and
                    "iou" in response_json["data"]):
                return_graph = response_json["data"]["graph"]
                return_iou = response_json["data"]["iou"]
        return return_graph, return_iou

    def screenshot(self, file):
        """Save out a screenshot"""
        r = self.client.screenshot(file)
        return r is not None and r.status_code == 200

    def launch_gym(self):
        """Launch the Fusion 360 Gym on the given host/port"""
        if self.p is not None:
            # Kill the process if it exists
            self.p.kill()
            self.p = None
        self.__write_launch_file()
        return self.__launch_gym()

    def __write_launch_file(self):
        """Write the launch file that the gym reads to connect"""
        gym_server_dir = Path(SERVER_DIR)
        launch_json_file = gym_server_dir / "launch.json"
        launch_data = {}
        if launch_json_file.exists():
            with open(launch_json_file, "r") as f:
                launch_data = json.load(f)
        url = f"http://{self.host}:{self.port}"
        launch_data[url] = {
            "host": self.host,
            "port": self.port,
            "connected": False
        }
        with open(launch_json_file, "w") as f:
            json.dump(launch_data, f, indent=4)

    def __launch_gym(self):
        """Launch the Fusion 360 Gym on the given host/port"""
        launcher = Launcher()
        self.p = launcher.launch()
        # We wait for Fusion to start responding to pings
        result = self.__wait_for_fusion()
        if result is False:
            # Fusion is awake but not responding so restart
            self.p.kill()
            self.p = None
            self.__launch_fusion()
        else:
            return result

    def __wait_for_fusion(self):
        """Wait until Fusion has launched"""
        if self.p is None:
            print("Fusion 360 process is None")
            return
        print("Waiting for Fusion to launch...")
        attempts = 0
        max_attempts = 60
        time.sleep(1)
        while attempts < max_attempts:
            # return_code = self.p.poll()
            print(f"Attempting to ping Fusion")
            # if return_code is not None:
            #     return return_code
            try:
                r = self.client.ping()
                if r is not None and r.status_code == 200:
                    print("Ping response received")
                    return True
                else:
                    print("No ping response received")
            except ConnectionError as ex:
                print(f"Ping raised {type(ex).__name__}")
            attempts += 1
            time.sleep(5)
        return False

    def __check_response(self, call, r):
        """Check the response is valid and raise exceptions if not"""
        if r is None:
            raise Exception(f"[{call}] response is None")
        if r.status_code != 200:
            response_data = r.json()
            raise Exception(f"[{call}] {r.status_code}: {response_data['message']}")
