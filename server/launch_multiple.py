import os
import sys
from pathlib import Path
import subprocess
import argparse
import json
import time


parser = argparse.ArgumentParser()
parser.add_argument("--host", type=str, default="127.0.0.1", help="Host name [default: 127.0.0.1]")
parser.add_argument("--start_port", type=int, default=8080, help="The starting port [default: 8080]")
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
    launch_json_file = Path(os.path.dirname(__file__)) / "launch.json"
    with open(launch_json_file, "w") as file_handle:
        json.dump(launch_data, file_handle, indent=4)
    return launch_json_file

def start_fusion():
    """Opens a new instance of Fusion 360"""
    if sys.platform == "darwin":
        # Shortcut location that links to the latest version
        # /Users/username/Library/Application Support/Autodesk/webdeploy/production/Autodesk Fusion 360.app
        USER_PATH = Path(os.path.expanduser("~"))
        FUSION_PATH = USER_PATH / "Library/Application Support/Autodesk/webdeploy/production/Autodesk Fusion 360.app"
        args = ["open", "-n", str(FUSION_PATH.resolve())]

    elif sys.platform == "win32":
        # Shortcut location that links to the latest version
        # C:\Users\username\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Autodesk
        # Actual location
        # C:\Users\username\AppData\Local\Autodesk\webdeploy\production\6a0c9611291d45bb9226980209917c3d\FusionLauncher.exe
        roaming_dir = Path(os.environ["APPDATA"])
        FUSION_PATH = roaming_dir / "Microsoft/Windows/Start Menu/Programs/Autodesk/Autodesk Fusion 360.lnk"
        args = ["start", str(FUSION_PATH.resolve())]

    print("Fusion path set to:", str(FUSION_PATH.resolve()))
    subprocess.call(args)


def launch_instances(host, start_port, instances):
    for port in range(start_port, start_port + instances):
        print(f"Launching Fusion 360 instance: {host}:{port}")
        start_fusion()
        time.sleep(5)



if __name__ == "__main__":
    launch_json_file = create_launch_json(args.host, args.start_port, args.instances)
    launch_instances(args.host, args.start_port, args.instances)
    # launch_json_file.unlink()
