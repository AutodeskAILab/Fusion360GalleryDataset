
import sys
import os
import json
from pathlib import Path

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "fusion360gym", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)

from fusion_360_client import Fusion360Client


class BaseSearch():

    def __init__(self, host="127.0.0.1", port=8080):
        self.host = host
        self.port = port
        self.client = Fusion360Client(f"http://{self.host}:{self.port}")
        self.current_dir = Path(__file__).resolve().parent
        self.log_dir = Path(__file__).resolve().parent / "log"
        if not self.log_dir.exists():
            self.log_dir.mkdir()
        self.testdata_dir = self.current_dir.parent / "testdata"
        self.steps = 0
        self.target_graph = None
        self.current_graph = None
        self.current_iou = None
        self.first_extrude_complete = False
        self.log = None

    def setup(self, target_file):
        """Setup search and connect to the Fusion Gym"""
        assert self.client is not None
        # Target design file we are trying to recover
        self.target_file = target_file
        if isinstance(target_file, str):
            self.target_file = Path(target_file)
        assert self.target_file.exists()
        self.steps = 0
        self.first_extrude_complete = False
        self.log = []
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
                self.current_graph = response_json["data"]["graph"]
                self.current_iou = response_json["data"]["iou"]
                if self.current_iou is not None:
                    # Set a flag to indicate we have geometry created
                    self.first_extrude_complete = True
                return_graph = self.current_graph
                return_iou = self.current_iou

        self.log.append({
            "step": self.steps,
            "start_face": start_face,
            "end_face": end_face,
            "operation": operation,
            "iou": return_iou
        })
        self.steps += 1
        return return_graph, return_iou

    def save_log(self):
        """Save out a log of the search sequence"""
        if self.log is not None and len(self.log) > 0:
            log_file = self.log_dir / f"{self.target_file.name}_log.json"
            with open(log_file, "w", encoding="utf8") as f:
                json.dump(self.log, f, indent=4)
