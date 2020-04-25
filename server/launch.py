import os
import sys
from pathlib import Path
import subprocess
import argparse
import json
import time
import importlib

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SERVER_DIR)
CLIENT_DIR = os.path.join(ROOT_DIR, "client")

# Add the client folder to sys.path
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)
import fusion_360_client
importlib.reload(fusion_360_client)
from fusion_360_client import Fusion360Client
sys.path.remove(CLIENT_DIR)

LAUNCH_JSON_FILE = Path(SERVER_DIR) / "launch.json"

parser = argparse.ArgumentParser()
parser.add_argument("--detach", dest="detach", default=False, action="store_true", help="Detach the launched Fusion 360 instances [default: False]")
parser.add_argument("--ping", dest="ping", default=False, action="store_true", help="Ping the launched Fusion 360 instances [default: False]")
parser.add_argument("--host", type=str, default="127.0.0.1", help="Host name as an IP address [default: 127.0.0.1]")
parser.add_argument("--start_port", type=int, default=8080, help="The starting port for the first Fusion 360 instance [default: 8080]")
parser.add_argument("--instances", type=int, default=2, help="The number of Fusion 360 instances to start [default: 2]")
args = parser.parse_args()


def create_launch_json(host, start_port, instances):
    """Launch instruction file to be read by the server on startup"""
    launch_data = {
        "host": host,
        "start_port": start_port,
        "instances": instances,
        "servers": []
    }
    with open(LAUNCH_JSON_FILE, "w") as file_handle:
        json.dump(launch_data, file_handle, indent=4)

def start_fusion():
    """Opens a new instance of Fusion 360"""
    if sys.platform == "darwin":
        # Shortcut location that links to the latest version
        # /Users/username/Library/Application Support/Autodesk/webdeploy/production/Autodesk Fusion 360.app
        user_path = Path(os.path.expanduser("~"))
        fusion_app = user_path / "Library/Application Support/Autodesk/webdeploy/production/Autodesk Fusion 360.app"
        fusion_path = str(fusion_app.resolve())
        args = ["open", "-n", fusion_path]
        subprocess.call(args)

    elif sys.platform == "win32":
        # Shortcut location that links to the latest version
        # C:\Users\username\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Autodesk
        # Actual location
        # C:\Users\username\AppData\Local\Autodesk\webdeploy\production\6a0c9611291d45bb9226980209917c3d\FusionLauncher.exe
        fusion_path = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Autodesk", "Autodesk Fusion 360.lnk")
        os.startfile(fusion_path)

    print("Fusion launched from:", fusion_path)


def launch_instances(host, start_port, instances):
    """Launch multiple instances of Fusion 360"""
    for port in range(start_port, start_port + instances):
        print(f"Launching Fusion 360 instance: {host}:{port}")
        start_fusion()
        time.sleep(5)


def detach():
    """Detach the launched servers to make the Fusion UI responsive"""
    with open(LAUNCH_JSON_FILE) as file_handle:
        launch_data = json.load(file_handle)
        for server in launch_data["servers"]:
            try:
                endpoint = f"http://{server['host']}:{server['port']}"
                print(f"Detaching {endpoint}...")
                client = Fusion360Client(endpoint)
                client.detach()
            except Exception as ex:
                print(f"Error detaching server {endpoint}: {ex}")
            

def ping():
    """Ping the launched servers to see if they respond"""
    with open(LAUNCH_JSON_FILE) as file_handle:
        launch_data = json.load(file_handle)
        for server in launch_data["servers"]:
            try:
                endpoint = f"http://{server['host']}:{server['port']}"
                client = Fusion360Client(endpoint)
                r = client.ping()
                print(f"Ping response from {endpoint}: {r.status_code}")
            except Exception as ex:
                print(f"Error pinging server {endpoint}: {ex}")


if __name__ == "__main__":
    if args.ping:
        ping()
    elif args.detach:
        detach()
    else:
        create_launch_json(args.host, args.start_port, args.instances)
        launch_instances(args.host, args.start_port, args.instances)

