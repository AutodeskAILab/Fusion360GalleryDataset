
import sys
import os
from pathlib import Path

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "fusion360gym", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)

from fusion_360_client import Fusion360Client


class BaseSearch():

    def __init__(self):
        self.current_dir = Path(__file__).resolve().parent
        self.testdata_dir = self.current_dir.parent / "testdata"
        self.client = None
        self.target_graph = None
        self.current_graph = None
        self.current_iou = None

    def setup(self, target_file, host="127.0.0.1", port=8080):
        """Setup search and connect to the Fusion Gym"""
        # Target design file we are trying to recover
        self.target_file = target_file
        if isinstance(target_file, str):
            self.target_file = Path(target_file)
        assert self.target_file.exists()
        self.host = host
        self.port = port
        self.client = Fusion360Client(f"http://{self.host}:{self.port}")
        # Set the target
        r = self.client.set_target(self.target_file)
        assert r is not None
        assert r.status_code == 200
        response_json = r.json()
        assert "data" in response_json
        assert "graph" in response_json["data"]
        self.target_graph = response_json["data"]["graph"]
        return self.target_graph

    def extrude(self, start_face, end_face, operation):
        """Extrude wrapper around the gym client"""
        assert self.client is not None
        r = self.client.add_extrude_by_target_face(
            start_face, end_face, operation)
        if r is None:
            return None, None
        if r.status_code != 200:
            return None, None
        response_json = r.json()
        assert "data" in response_json
        assert "graph" in response_json["data"]
        assert "iou" in response_json["data"]
        self.current_graph = response_json["data"]["graph"]
        self.current_iou = response_json["data"]["iou"]
        return self.current_graph, self.current_iou
