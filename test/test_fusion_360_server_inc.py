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
import time

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
        self.assertIn("sketch_id", response_data, msg="add_sketch response has sketch_id")
        self.assertIsInstance(response_data["sketch_id"], str, msg="add_sketch sketch_id is string")
        self.assertIn("sketch_name", response_data, msg="add_sketch response has sketch_name")
        self.assertIsInstance(response_data["sketch_name"], str, msg="add_sketch sketch_name is string")

    def test_add_sketch_invalid(self):
        self.client.clear()
        # Pass in something other than a string or dict
        r = self.client.add_sketch(Path())
        self.assertIsNone(r, msg="add_sketch response is None")
        r = self.client.add_sketch("some random string")
        self.assertEqual(r.status_code, 500, msg="add_sketch status code")

    def test_add_line(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]
        pt1 = {"x": 0, "y": 0}
        pt2 = {"x": 10, "y": 10}
        r = self.client.add_line(sketch_name, pt1, pt2)
        self.assertEqual(r.status_code, 200, msg="add_line status code")
        response_json = r.json()
        self.assertIn("data", response_json, msg="add_line response has data")
        response_data = response_json["data"]
        # sketch_id
        self.assertIn("sketch_id", response_data, msg="add_line response has sketch_id")
        self.assertIsInstance(response_data["sketch_id"], str, msg="add_line sketch_id is string")
        # sketch_name
        self.assertIn("sketch_name", response_data, msg="add_line response has sketch_name")
        self.assertIsInstance(response_data["sketch_name"], str, msg="add_line sketch_name is string")
        # line_id
        self.assertIn("line_id", response_data, msg="add_line response has line_id")
        self.assertIsInstance(response_data["line_id"], str, msg="add_line line_id is string")
        self.assertEqual(len(response_data["line_id"]), 36, msg="add_line line_id length equals 36")
        # profiles
        self.assertIn("profiles", response_data, msg="add_line response has profiles")
        self.assertIsInstance(response_data["profiles"], dict, msg="add_line profiles are dict")
        self.assertEqual(len(response_data["profiles"]), 0, msg="add_line profiles length equals 0")

        # self.client.clear()
        # r = self.client.detach()

    def test_add_lines(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        pts = [
            {"x": 0, "y": 0},
            {"x": 10, "y": 0},
            {"x": 10, "y": 10},
            {"x": 0, "y": 10},
            {"x": 0, "y": 0}
        ]
        line_ids = []
        sketch_ids = []
        sketch_names = []
        profiles = []
        for index in range(4):
            r = self.client.add_line(sketch_name, pts[index], pts[index + 1])
            self.assertEqual(r.status_code, 200, msg="add_line status code")
            response_json = r.json()
            response_data = response_json["data"]
            print(response_data)
            line_ids.append(response_data["line_id"])
            sketch_ids.append(response_data["sketch_id"])
            sketch_names.append(response_data["sketch_name"])
            profiles.append(response_data["profiles"])

        # sketch_id
        self.assertEqual(len(set(sketch_ids)), 1, msg="add_line sketch_ids are all the same")
        for sketch_id in sketch_ids:
            self.assertIsInstance(sketch_id, str, msg="add_line sketch_id is string")
            self.assertEqual(len(sketch_id), 36, msg="add_line sketch_id length equals 36")

        # sketch_name
        self.assertEqual(len(set(sketch_names)), 1, msg="add_line sketch_name are all the same")
        for sketch_name in sketch_names:
            self.assertIsInstance(sketch_name, str, msg="add_line sketch_name is string")

        # line_id
        ids_unique = len(line_ids) == len(set(line_ids))
        self.assertEqual(ids_unique, True, msg="add_line ids are unique")
        for line_id in line_ids:
            self.assertIsInstance(line_id, str, msg="add_line line_id is string")
            self.assertEqual(len(line_id), 36, msg="add_line line_id length equals 36")

        for profile in profiles:
            self.assertIsInstance(profile, dict, msg="add_line profiles are dict")

        # The last profile response should contain some information
        self.assertEqual(len(profiles[3]), 1, msg="add_line profiles length equals 1")

        # self.client.clear()
        # r = self.client.detach()

    def test_add_extrude(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        self.assertIsInstance(sketch_name, str, msg="sketch_name is string")
        pts = [
            {"x": 0, "y": 0},
            {"x": 10, "y": 0},
            {"x": 10, "y": 10},
            {"x": 0, "y": 10},
            {"x": 0, "y": 0}
        ]
        for index in range(4):
            r = self.client.add_line(sketch_name, pts[index], pts[index + 1])
            self.assertEqual(r.status_code, 200, msg="add_line status code")

        response_json = r.json()
        response_data = response_json["data"]
        # Pull out the first profile id
        profile_id = next(iter(response_data["profiles"]))
        self.assertIsInstance(profile_id, str, msg="profile_id is string")
        self.assertEqual(len(profile_id), 36, msg="profile_id length equals 36")

        # Extrude
        r = self.client.add_extrude(sketch_name, profile_id, 5.0, "NewBodyFeatureOperation")
        self.assertEqual(r.status_code, 200, msg="add_extrude status code")
        response_json = r.json()
        response_data = response_json["data"]

        self.assertIn("type", response_data, msg="add_extrude response has type")
        self.assertIn("faces", response_data, msg="add_extrude response has faces")
        self.assertIsInstance(response_data["faces"], list, msg="add_extrude faces is list")
        self.assertGreater(len(response_data["faces"]), 0, msg="add_extrude faces length greater than 0")

    def test_add_double_extrude_by_id(self):
        self.client.clear()
        time.sleep(10)
        r = self.client.add_sketch("XY")
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        pts = [
            {"x": 0, "y": 0},
            {"x": 10, "y": 0},
            {"x": 10, "y": 10},
            {"x": 0, "y": 10},
            {"x": 0, "y": 0}
        ]
        for index in range(4):
            r = self.client.add_line(sketch_name, pts[index], pts[index + 1])
        response_json = r.json()
        response_data = response_json["data"]
        # Pull out the first profile id
        profile_id = next(iter(response_data["profiles"]))

        # Extrude
        r = self.client.add_extrude(sketch_name, profile_id, 5.0, "NewBodyFeatureOperation")
        response_json = r.json()
        response_data = response_json["data"]
        faces = response_data["faces"]

        # Find the end face
        xy_face = None
        for face in faces:
            if face["location_in_feature"] == "EndFace":
                xy_face = face

        # Start the second sketch and extrude
        r = self.client.add_sketch(xy_face["face_id"])
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        pts = [
            {"x": 2.5, "y": 2.5},
            {"x": 7.5, "y": 2.5},
            {"x": 7.5, "y": 7.5},
            {"x": 2.5, "y": 7.5},
            {"x": 2.5, "y": 2.5}
        ]
        for index in range(4):
            r = self.client.add_line(sketch_name, pts[index], pts[index + 1])
        response_json = r.json()
        response_data = response_json["data"]
        # Pull out the first profile id
        profile_id = next(iter(response_data["profiles"]))

        # Extrude2
        r = self.client.add_extrude(sketch_name, profile_id, 2.0, "JoinFeatureOperation")
        response_json = r.json()
        response_data = response_json["data"]

        self.assertIn("type", response_data, msg="add_extrude response has type")
        self.assertIn("faces", response_data, msg="add_extrude response has faces")
        self.assertIsInstance(response_data["faces"], list, msg="add_extrude faces is list")
        self.assertGreater(len(response_data["faces"]), 0, msg="add_extrude faces length greater than 0")

        # self.client.clear()
        # r = self.client.detach()


if __name__ == "__main__":
    unittest.main()
