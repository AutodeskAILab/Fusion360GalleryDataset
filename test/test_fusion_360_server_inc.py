"""

Test incremental design creation functionality of the Fusion 360 Server

"""


import unittest
import requests
from pathlib import Path
import sys
import os
import numpy
from stl import mesh
import importlib
import json
import shutil

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TEST_DIR)
CLIENT_DIR = os.path.join(ROOT_DIR, "client")

# Add the client folder to sys.path
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)
import fusion_360_client
importlib.reload(fusion_360_client)
from fusion_360_client import Fusion360Client
sys.path.remove(CLIENT_DIR)

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


class TestFusion360Server(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")
        # Clear all documents so we start with a clean slate
        cls.client.clear()
        # ------------------------------------------
        # TEST FILES
        cls.data_dir = Path(ROOT_DIR) / "data"
        box_design = "SingleSketchExtrude_RootComponent"
        hex_design = "Z0HexagonCutJoin_RootComponent"

    def test_add_sketch(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        self.assertEqual(r.status_code, 200, msg="add_sketch status code")
        response_json = r.json()
        self.assertIn("data", response_json, msg="add_sketch response has data")
        response_data = response_json["data"]
        self.assertIn("id", response_data, msg="add_sketch response has id")
        self.assertIsInstance(response_data["id"], str, msg="add_sketch id is string")
        self.client.clear()

    def test_add_sketch_invalid(self):
        self.client.clear()
        # Pass in something other than a string or dict
        r = self.client.add_sketch(Path())
        self.assertIsNone(r, msg="add_sketch response is None")
        r = self.client.add_sketch("some random string")
        self.assertEqual(r.status_code, 500, msg="add_sketch status code")
        self.client.clear()

    def test_add_line(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_id = response_data["id"]
        pt1 = {"x": 0, "y": 0}
        pt2 = {"x": 10, "y": 10}
        r = self.client.add_line(sketch_id, pt1, pt2)
        self.assertEqual(r.status_code, 200, msg="add_line status code")
        response_json = r.json()
        self.assertIn("data", response_json, msg="add_line response has data")
        response_data = response_json["data"]
        self.assertIn("id", response_data, msg="add_line response has id")
        self.assertIsInstance(response_data["id"], str, msg="add_line id is string")        
        self.client.clear()


if __name__ == "__main__":
    unittest.main()
