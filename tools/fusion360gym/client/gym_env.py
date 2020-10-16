"""

Abstract Fusion 360 Gym Environment
for launching and interacting with the gym

"""
import sys
import os
import json
import time
from pathlib import Path
from requests.exceptions import ConnectionError
import psutil

from fusion360gym_client import Fusion360GymClient

# Add the common folder to sys.path
COMMON_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "common")
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

from launcher import Launcher


class GymEnv():

    def __init__(self, host="127.0.0.1", port=8080, launch_gym=False):
        self.host = host
        self.port = port
        self.client = Fusion360GymClient(f"http://{self.host}:{self.port}")
        # Fusion subprocess
        self.p = None
        if launch_gym:
            self.launch_gym()

    def launch_gym(self):
        """Launch the Fusion 360 Gym on the given host/port"""
        print("Launching Gym...")
        if self.p is not None:
            # Give a second for Fusion to crash
            time.sleep(2)
            return_code = self.p.poll()
            print(f"Poll response is: {return_code}")
            # Kill the process if it is active
            if return_code is None:
                self.p.kill()
            self.p = None
        self.__write_launch_file()
        return self.__launch_gym()

    def kill_gym(self, including_parent=True):
        """Kill this instance of the Fusion 360 Gym"""
        print("Killing Gym...")
        if self.p is not None:
            try:
                parent = psutil.Process(self.p.pid)
                children = parent.children(recursive=True)
                for child in children:
                    child.kill()
                gone, still_alive = psutil.wait_procs(children, timeout=5)
                if including_parent:
                    parent.kill()
                    parent.wait(5)
            except:
                print("Warning: Failed to kill Gym process tree")
        else:
            print("Warning: Gym process is None")

    def __write_launch_file(self):
        """Write the launch file that the gym reads to connect"""
        current_dir = Path(__file__).resolve().parent
        gym_server_dir = current_dir.parent / "server"
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
        print(f"Writing Launch file for: {url}")
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
            self.__launch_gym()
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
            print(f"Attempting to ping Fusion")
            try:
                r = self.client.ping()
                if r is not None and r.status_code == 200:
                    print("Ping response received")
                    r.close()
                    return True
                else:
                    print("No ping response received")
                r.close()
            except ConnectionError as ex:
                print(f"Ping raised {type(ex).__name__}")
            attempts += 1
            time.sleep(5)
        return False

    def check_response(self, call, r):
        """Check the response is valid and raise exceptions if not"""
        if r is None:
            raise Exception(f"[{call}] response is None")
        if r.status_code != 200:
            response_data = r.json()
            raise Exception(f"[{call}] {r.status_code}: {response_data['message']}")
