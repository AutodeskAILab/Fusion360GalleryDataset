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

import common_test

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)

from fusion360gym_client import Fusion360GymClient

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


class TestFusion360ServerSketchExtrusion(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")
        # Clear all documents so we start with a clean slate
        cls.client.clear()
        # ------------------------------------------
        # TEST FILES
        cls.data_dir = Path(__file__).parent.parent.parent / "testdata"
        cls.output_dir = cls.data_dir / "output"
        hex_design = "Hexagon"
        cls.hex_design_json_file = cls.data_dir / f"{hex_design}.json"
        cls.box_design_smt_file = cls.data_dir / "Box.smt"

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
        # curve_id
        self.assertIn("curve_id", response_data, msg="add_line response has curve_id")
        self.assertIsInstance(response_data["curve_id"], str, msg="add_line curve_id is string")
        self.assertEqual(len(response_data["curve_id"]), 36, msg="add_line curve_id length equals 36")
        # profiles
        self.assertIn("profiles", response_data, msg="add_line response has profiles")
        self.assertIsInstance(response_data["profiles"], dict, msg="add_line profiles are dict")
        self.assertEqual(len(response_data["profiles"]), 0, msg="add_line profiles length equals 0")

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
        curve_ids = []
        sketch_ids = []
        sketch_names = []
        profiles = []
        for index in range(4):
            r = self.client.add_line(sketch_name, pts[index], pts[index + 1])
            self.assertEqual(r.status_code, 200, msg="add_line status code")
            response_json = r.json()
            response_data = response_json["data"]
            curve_ids.append(response_data["curve_id"])
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

        # curve_id
        ids_unique = len(curve_ids) == len(set(curve_ids))
        self.assertEqual(ids_unique, True, msg="add_line ids are unique")
        for curve_id in curve_ids:
            self.assertIsInstance(curve_id, str, msg="add_line curve_id is string")
            self.assertEqual(len(curve_id), 36, msg="add_line curve_id length equals 36")

        for profile in profiles:
            self.assertIsInstance(profile, dict, msg="add_line profiles are dict")

        # The last profile response should contain some information
        self.assertEqual(len(profiles[3]), 1, msg="add_line profiles length equals 1")

        # self.client.clear()
        # r = self.client.detach()

    def test_add_circle(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]
        pt1 = {"x": 0, "y": 0}
        r = self.client.add_circle(sketch_name, pt1, 5)
        self.assertEqual(r.status_code, 200, msg="add_circle status code")
        response_json = r.json()
        self.assertIn("data", response_json, msg="add_circle response has data")
        response_data = response_json["data"]
        # sketch_id
        self.assertIn("sketch_id", response_data, msg="add_circle response has sketch_id")
        self.assertIsInstance(response_data["sketch_id"], str, msg="add_circle sketch_id is string")
        # sketch_name
        self.assertIn("sketch_name", response_data, msg="add_circle response has sketch_name")
        self.assertIsInstance(response_data["sketch_name"], str, msg="add_circle sketch_name is string")
        # curve_id
        self.assertIn("curve_id", response_data, msg="add_circle response has curve_id")
        self.assertIsInstance(response_data["curve_id"], str, msg="add_circle curve_id is string")
        self.assertEqual(len(response_data["curve_id"]), 36, msg="add_circle curve_id length equals 36")
        # profiles
        self.assertIn("profiles", response_data, msg="add_circle response has profiles")
        self.assertIsInstance(response_data["profiles"], dict, msg="add_circle profiles are dict")
        self.assertEqual(len(response_data["profiles"]), 1, msg="add_circle profiles length equals 1")

    def test_add_arc(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]
        # Start of arc
        pt1 = {"x": 10, "y": 0}
        # Center of arc
        pt2 = {"x": 0, "y": 0} 
        r = self.client.add_arc(sketch_name, pt1, pt2, 90)
        self.assertEqual(r.status_code, 200, msg="add_arc status code")
        response_json = r.json()
        self.assertIn("data", response_json, msg="add_arc response has data")
        response_data = response_json["data"]
        # sketch_id
        self.assertIn("sketch_id", response_data, msg="add_arc response has sketch_id")
        self.assertIsInstance(response_data["sketch_id"], str, msg="add_arc sketch_id is string")
        # sketch_name
        self.assertIn("sketch_name", response_data, msg="add_arc response has sketch_name")
        self.assertIsInstance(response_data["sketch_name"], str, msg="add_arc sketch_name is string")
        # curve_id
        self.assertIn("curve_id", response_data, msg="add_arc response has curve_id")
        self.assertIsInstance(response_data["curve_id"], str, msg="add_arc curve_id is string")
        self.assertEqual(len(response_data["curve_id"]), 36, msg="add_arc curve_id length equals 36")
        # profiles
        self.assertIn("profiles", response_data, msg="add_arc response has profiles")
        self.assertIsInstance(response_data["profiles"], dict, msg="add_arc profiles are dict")
        self.assertEqual(len(response_data["profiles"]), 0, msg="add_arc profiles length equals 0")

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
        common_test.check_extrude_data(self, response_data)

    def test_set_target_add_extrude(self):
        # Set target box
        r = self.client.set_target(self.box_design_smt_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        common_test.check_graph_format(self, response_json["data"])
        common_test.check_bounding_box(self, response_json["data"])

        # Sketch
        r = self.client.add_sketch("XY")
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        self.assertIsInstance(sketch_name, str, msg="sketch_name is string")
        pts = [
            {"x": -1, "y": 0},
            {"x": 1, "y": 0},
            {"x": 1, "y": 1},
            {"x": -1, "y": 1},
            {"x": -1, "y": 0}
        ]
        for index in range(4):
            r = self.client.add_line(sketch_name, pts[index], pts[index + 1])
            self.assertEqual(r.status_code, 200, msg="add_line status code")

        response_json = r.json()
        response_data = response_json["data"]
        # Pull out the first profile id
        profile_id = next(iter(response_data["profiles"]))

        # Extrude
        r = self.client.add_extrude(sketch_name, profile_id, 1.0, "NewBodyFeatureOperation")
        self.assertEqual(r.status_code, 200, msg="add_extrude status code")
        response_json = r.json()
        response_data = response_json["data"]
        common_test.check_extrude_data(self, response_data, has_iou=True)
        self.assertAlmostEqual(response_data["iou"], 0.5, places=2, msg="iou ~= 0.5")
        r = self.client.clear()

    def test_add_double_extrude_by_id(self):
        self.client.clear()

        # Create an empty sketch on the XY plane
        r = self.client.add_sketch("XY")
        # Get the unique name of the sketch created
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        # Add four lines to the sketch to make a square
        pts = [
            {"x": 0, "y": 0},
            {"x": 10, "y": 0},
            {"x": 10, "y": 10},
            {"x": 0, "y": 10},
            {"x": 0, "y": 0}
        ]
        for index in range(4):
            r = self.client.add_line(sketch_name, pts[index], pts[index + 1])

        # Pull out the first profile id
        response_json = r.json()
        response_data = response_json["data"]
        profile_id = next(iter(response_data["profiles"]))
        # Extrude by a given distance to make a new body
        r = self.client.add_extrude(sketch_name, profile_id, 5.0, "NewBodyFeatureOperation")
        response_json = r.json()
        response_data = response_json["data"]
        common_test.check_extrude_data(self, response_data)
        # Find the end face
        faces = response_data["extrude"]["faces"]
        for face in faces:
            if face["location_in_feature"] == "EndFace":
                xy_face = face
        # Create a second sketch on the end face
        r = self.client.add_sketch(xy_face["face_id"])
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        # Draw the second smaller square
        pts = [
            {"x": 2.5, "y": 2.5},
            {"x": 7.5, "y": 2.5},
            {"x": 7.5, "y": 7.5},
            {"x": 2.5, "y": 7.5},
            {"x": 2.5, "y": 2.5}
        ]
        for index in range(4):
            r = self.client.add_line(sketch_name, pts[index], pts[index + 1])

        # Pull out the first profile id
        response_json = r.json()
        response_data = response_json["data"]
        profile_id = next(iter(response_data["profiles"]))
        # Extrude by a given distance, adding to the existing body
        r = self.client.add_extrude(sketch_name, profile_id, 2.0, "JoinFeatureOperation")
        response_json = r.json()
        response_data = response_json["data"]
        common_test.check_extrude_data(self, response_data)

    def test_add_double_extrude_by_point(self):
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
        common_test.check_extrude_data(self, response_data)
        faces = response_data["extrude"]["faces"]

        # Start the second sketch with a point on the end face
        r = self.client.add_sketch({
            "x": 5.0,
            "y": 5.0,
            "z": 5.0
        })
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
        common_test.check_extrude_data(self, response_data)

    def test_add_point(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]
        pt1 = {"x": 0, "y": 0}
        r = self.client.add_point(sketch_name, pt1)
        self.assertEqual(r.status_code, 200, msg="add_point status code")
        response_json = r.json()
        self.assertIn("data", response_json, msg="add_point response has data")
        response_data = response_json["data"]
        # sketch_id
        self.assertIn("sketch_id", response_data, msg="add_point response has sketch_id")
        self.assertIsInstance(response_data["sketch_id"], str, msg="add_point sketch_id is string")
        # sketch_name
        self.assertIn("sketch_name", response_data, msg="add_point response has sketch_name")
        self.assertIsInstance(response_data["sketch_name"], str, msg="add_point sketch_name is string")
        # curve_id
        self.assertNotIn("curve_id", response_data, msg="add_point response has no curve_id")
        # profiles
        self.assertIn("profiles", response_data, msg="add_point response has profiles")

    def test_add_points(self):
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
        curve_ids = []
        sketch_ids = []
        sketch_names = []
        profiles = []
        for index, pt in enumerate(pts):
            r = self.client.add_point(sketch_name, pt)
            self.assertEqual(r.status_code, 200, msg="add_point status code")
            response_json = r.json()
            response_data = response_json["data"]
            # There won't always be a curve id
            curve_id = response_data["curve_id"] if "curve_id" in response_data else None
            curve_ids.append(curve_id)
            sketch_ids.append(response_data["sketch_id"])
            sketch_names.append(response_data["sketch_name"])
            profiles.append(response_data["profiles"])

        # sketch_id
        self.assertEqual(len(set(sketch_ids)), 1, msg="add_point sketch_ids are all the same")
        for sketch_id in sketch_ids:
            self.assertIsInstance(sketch_id, str, msg="add_point sketch_id is string")
            self.assertEqual(len(sketch_id), 36, msg="add_point sketch_id length equals 36")

        # sketch_name
        self.assertEqual(len(set(sketch_names)), 1, msg="add_point sketch_name are all the same")
        for sketch_name in sketch_names:
            self.assertIsInstance(sketch_name, str, msg="add_point sketch_name is string")

        # curve_id
        ids_unique = len(curve_ids) == len(set(curve_ids))
        self.assertEqual(ids_unique, True, msg="add_point ids are unique")
        for index, curve_id in enumerate(curve_ids):
            if index == 0:
                self.assertIsNone(curve_id)
            else:
                self.assertIsNotNone(curve_id)
                self.assertIsInstance(curve_id, str, msg="add_point curve_id is string")
                self.assertEqual(len(curve_id), 36, msg="add_point curve_id length equals 36")

        for profile in profiles:
            self.assertIsInstance(profile, dict, msg="add_point profiles are dict")

        # The last profile response should contain some information
        self.assertEqual(len(profiles[-1]), 1, msg="add_point profiles length equals 1")

    def test_add_points_close(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        pts = [
            {"x": 0, "y": 0},
            {"x": 10, "y": 0},
            {"x": 10, "y": 10},
            None
        ]
        curve_ids = []
        sketch_ids = []
        sketch_names = []
        profiles = []
        for index, pt in enumerate(pts):
            if index < len(pts) - 1:
                r = self.client.add_point(sketch_name, pt)
                self.assertEqual(r.status_code, 200, msg="add_point status code")
            else:
                r = self.client.close_profile(sketch_name)
                self.assertEqual(r.status_code, 200, msg="close_profile status code")
            response_json = r.json()
            response_data = response_json["data"]
            # There won't always be a curve id
            curve_id = response_data["curve_id"] if "curve_id" in response_data else None
            curve_ids.append(curve_id)
            sketch_ids.append(response_data["sketch_id"])
            sketch_names.append(response_data["sketch_name"])
            profiles.append(response_data["profiles"])

        # sketch_id
        self.assertEqual(len(set(sketch_ids)), 1, msg="add_point sketch_ids are all the same")
        for sketch_id in sketch_ids:
            self.assertIsInstance(sketch_id, str, msg="add_point sketch_id is string")
            self.assertEqual(len(sketch_id), 36, msg="add_point sketch_id length equals 36")

        # sketch_name
        self.assertEqual(len(set(sketch_names)), 1, msg="add_point sketch_name are all the same")
        for sketch_name in sketch_names:
            self.assertIsInstance(sketch_name, str, msg="add_point sketch_name is string")

        # curve_id
        ids_unique = len(curve_ids) == len(set(curve_ids))
        self.assertEqual(ids_unique, True, msg="add_point ids are unique")
        for index, curve_id in enumerate(curve_ids):
            if index == 0:
                self.assertIsNone(curve_id)
            else:
                self.assertIsNotNone(curve_id)
                self.assertIsInstance(curve_id, str, msg="add_point curve_id is string")
                self.assertEqual(len(curve_id), 36, msg="add_point curve_id length equals 36")

        for profile in profiles:
            self.assertIsInstance(profile, dict, msg="add_point profiles are dict")

        # The last profile response should contain some information
        self.assertEqual(len(profiles[-1]), 1, msg="add_point profiles length equals 1")

    def test_add_one_point_close(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]
        pt1 = {"x": 0, "y": 0}
        r = self.client.add_point(sketch_name, pt1)
        self.assertEqual(r.status_code, 200, msg="add_point status code")
        r = self.client.close_profile(sketch_name)
        self.assertEqual(r.status_code, 500, msg="close_profile status code")

    def test_add_two_point_close(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]
        pt1 = {"x": 0, "y": 0}
        r = self.client.add_point(sketch_name, pt1)
        self.assertEqual(r.status_code, 200, msg="add_point status code")
        pt2 = {"x": 0, "y": 10}
        r = self.client.add_point(sketch_name, pt2)
        self.assertEqual(r.status_code, 200, msg="add_point status code")
        r = self.client.close_profile(sketch_name)
        self.assertEqual(r.status_code, 500, msg="close_profile status code")

    def test_add_three_point_close(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]
        pt1 = {"x": 0, "y": 0}
        r = self.client.add_point(sketch_name, pt1)
        self.assertEqual(r.status_code, 200, msg="add_point status code")
        pt2 = {"x": 0, "y": 10}
        r = self.client.add_point(sketch_name, pt2)
        self.assertEqual(r.status_code, 200, msg="add_point status code")
        pt3 = {"x": 10, "y": 10}
        r = self.client.add_point(sketch_name, pt3)
        self.assertEqual(r.status_code, 200, msg="add_point status code")
        r = self.client.close_profile(sketch_name)
        self.assertEqual(r.status_code, 200, msg="close_profile status code")
        response_json = r.json()
        response_data = response_json["data"]
        profiles = response_data["profiles"]
        self.assertEqual(len(profiles), 1, msg="add_point profiles length equals 1")

    def test_add_three_point_close_extrude(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]
        pt1 = {"x": 0, "y": 0}
        pt2 = {"x": 0, "y": 10}
        pt3 = {"x": 10, "y": 10}
        r = self.client.add_point(sketch_name, pt1)
        r = self.client.add_point(sketch_name, pt2)
        r = self.client.add_point(sketch_name, pt3)
        r = self.client.close_profile(sketch_name)
        response_json = r.json()
        response_data = response_json["data"]
        profile_id = next(iter(response_data["profiles"]))

        # Extrude
        r = self.client.add_extrude(sketch_name, profile_id, 5.0, "NewBodyFeatureOperation")
        self.assertEqual(r.status_code, 200, msg="add_extrude status code")
        response_json = r.json()
        response_data = response_json["data"]
        common_test.check_extrude_data(self, response_data)

    def test_add_point_world(self):
        self.client.clear()
        r = self.client.add_sketch("XY")
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        pts = [
            {"x": 0, "y": 0},
            {"x": 10, "y": 0},
            {"x": 10, "y": 10},
            {"x": 0, "y": 10}
        ]
        for pt in pts:
            r = self.client.add_point(sketch_name, pt)
        r = self.client.close_profile(sketch_name)
        response_json = r.json()
        response_data = response_json["data"]
        # Pull out the first profile id
        profile_id = next(iter(response_data["profiles"]))

        # Extrude
        r = self.client.add_extrude(sketch_name, profile_id, 10.0, "NewBodyFeatureOperation")
        response_json = r.json()
        response_data = response_json["data"]
        common_test.check_extrude_data(self, response_data)
        faces = response_data["extrude"]["faces"]

        # Start the second sketch with a point on the side face
        r = self.client.add_sketch({
            "x": 10.0,
            "y": 5.0,
            "z": 5.0
        })
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        # Global points on the side face
        pts = [
            {"x": 10.0, "y": 2.5, "z": 2.5},
            {"x": 10.0, "y": 2.5, "z": 7.5},
            {"x": 10.0, "y": 7.5, "z": 7.5},
            {"x": 10.0, "y": 7.5, "z": 2.5}
        ]
        for pt in pts:
            r = self.client.add_point(sketch_name, pt, transform="world")
        r = self.client.close_profile(sketch_name)
        response_json = r.json()
        response_data = response_json["data"]
        # Pull out the first profile id
        profile_id = next(iter(response_data["profiles"]))

        # Extrude2
        r = self.client.add_extrude(sketch_name, profile_id, 2.0, "JoinFeatureOperation")
        response_json = r.json()
        response_data = response_json["data"]
        common_test.check_extrude_data(self, response_data)

    def test_add_line_world(self):
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
        for index in range(4):
            r = self.client.add_line(sketch_name, pts[index], pts[index + 1])
        response_json = r.json()
        response_data = response_json["data"]
        # Pull out the first profile id
        profile_id = next(iter(response_data["profiles"]))

        # Extrude
        r = self.client.add_extrude(
            sketch_name, profile_id, 10.0, "NewBodyFeatureOperation")
        response_json = r.json()
        response_data = response_json["data"]
        common_test.check_extrude_data(self, response_data)
        faces = response_data["extrude"]["faces"]

        # Start the second sketch with a point on the side face
        r = self.client.add_sketch({
            "x": 10.0,
            "y": 5.0,
            "z": 5.0
        })
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        # Global points on the side face
        pts = [
            {"x": 10.0, "y": 2.5, "z": 2.5},
            {"x": 10.0, "y": 2.5, "z": 7.5},
            {"x": 10.0, "y": 7.5, "z": 7.5},
            {"x": 10.0, "y": 7.5, "z": 2.5},
            {"x": 10.0, "y": 2.5, "z": 2.5}
        ]
        for index in range(4):
            r = self.client.add_line(
                sketch_name, pts[index], pts[index + 1], transform="world")
        response_json = r.json()
        response_data = response_json["data"]
        # Pull out the first profile id
        profile_id = next(iter(response_data["profiles"]))

        # Extrude2
        r = self.client.add_extrude(
            sketch_name, profile_id, 2.0, "JoinFeatureOperation")
        response_json = r.json()
        response_data = response_json["data"]
        common_test.check_extrude_data(self, response_data)


if __name__ == "__main__":
    unittest.main()
