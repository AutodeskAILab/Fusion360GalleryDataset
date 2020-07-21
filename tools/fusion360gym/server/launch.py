"""

Launcher for multiple Fusion 360 server instances

"""
import os
import sys
from pathlib import Path
import subprocess
import argparse
import json
import time
import importlib

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)
import fusion_360_client
importlib.reload(fusion_360_client)
from fusion_360_client import Fusion360Client

COMMON_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)
import launcher
importlib.reload(launcher)
from launcher import Launcher

LAUNCH_JSON_FILE = Path("launch.json")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

parser = argparse.ArgumentParser()
parser.add_argument("--detach", dest="detach", default=False, action="store_true", help="Detach the launched Fusion 360 instances [default: False]")
parser.add_argument("--ping", dest="ping", default=False, action="store_true", help="Ping the launched Fusion 360 instances [default: False]")
parser.add_argument("--host", type=str, default=DEFAULT_HOST, help="Host name as an IP address [default: 127.0.0.1]")
parser.add_argument("--start_port", type=int, default=DEFAULT_PORT, help="The starting port for the first Fusion 360 instance [default: 8080]")
parser.add_argument("--instances", type=int, default=1, help="The number of Fusion 360 instances to start [default: 1]")
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


def launch_instances(host, start_port, instances):
    """Launch multiple instances of Fusion 360"""
    launcher = Launcher()
    for port in range(start_port, start_port + instances):
        print(f"Launching Fusion 360 instance: {host}:{port}")
        launcher.launch()
        time.sleep(5)


def detach_endpoint(host, port):
    """Detach an endpoint"""
    try:
        endpoint = f"http://{host}:{port}"
        client = Fusion360Client(endpoint)
        print(f"Detaching {endpoint}...")
        client.detach()
    except Exception as ex:
        print(f"Error detaching server {endpoint}: {ex}")


def detach():
    """Detach the launched servers to make the Fusion UI responsive"""
    if LAUNCH_JSON_FILE.exists():
        with open(LAUNCH_JSON_FILE) as file_handle:
            launch_data = json.load(file_handle)
            for server in launch_data["servers"]:
                detach_endpoint(server["host"], server["port"])
    else:
        detach_endpoint(DEFAULT_HOST, DEFAULT_PORT)


def ping_endpoint(host, port):
    """Ping an endpoint"""
    try:
        endpoint = f"http://{host}:{port}"
        client = Fusion360Client(endpoint)
        r = client.ping()
        print(f"Ping response from {endpoint}: {r.status_code}")
    except Exception as ex:
        print(f"Error pinging server {endpoint}: {ex}")


def ping():
    """Ping the launched servers to see if they respond"""
    if LAUNCH_JSON_FILE.exists():
        with open(LAUNCH_JSON_FILE) as file_handle:
            launch_data = json.load(file_handle)
            for server in launch_data["servers"]:
                ping_endpoint(server["host"], server["port"])
    else:
        ping_endpoint(DEFAULT_HOST, DEFAULT_PORT)


if __name__ == "__main__":
    if args.ping:
        ping()
    elif args.detach:
        detach()
    else:
        create_launch_json(args.host, args.start_port, args.instances)
        launch_instances(args.host, args.start_port, args.instances)
