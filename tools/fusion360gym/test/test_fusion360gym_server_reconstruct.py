"""

Test reconstruction functionality of the Fusion 360 Server

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

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)

from fusion360gym_client import Fusion360GymClient

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


class TestFusion360ServerReconstruct(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")
        # Clear all documents so we start with a clean slate
        cls.client.clear()
        # ------------------------------------------
        # TEST FILES
        cls.data_dir = Path(__file__).parent.parent.parent / "testdata"
        box_design = "SingleSketchExtrude_RootComponent"
        hex_design = "Z0HexagonCutJoin_RootComponent"
        # Box json reconstruction file
        cls.box_design_json_file = cls.data_dir / f"{box_design}.json"
        cls.hex_design_json_file = cls.data_dir / f"{hex_design}.json"
        # Invalid json reconstruction file
        cls.test_json_invalid_file = cls.data_dir / f"{box_design}_Invalid.json"
        # ------------------------------------------

    def test_clear(self):
        r = self.client.clear()
        self.assertEqual(r.status_code, 200, msg="clear status code")

    def test_reconstruct_non_file(self):
        bad_data_dir = Path("datazzzz")
        json_file = bad_data_dir / "not_a_file.json"
        r = self.client.reconstruct(json_file)
        self.assertIsNone(r, msg="reconstruct response is None")

    def test_reconstruct(self):
        r = self.client.reconstruct(self.box_design_json_file)
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        r = self.client.clear()

    def test_reconstruct_invalid_file(self):
        r = self.client.reconstruct(self.test_json_invalid_file)
        self.assertIsNone(r, msg="reconstruct response is not None")
        r = self.client.clear()

    def test_reconstruct_sketch_invalid(self):
        self.client.clear()
        with open(self.hex_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        sketch_id = json_data["timeline"][0]["entity"]
        sketch_data = json_data["entities"][sketch_id]
        # Bad JSON
        r = self.client.reconstruct_sketch({})
        self.assertIsNone(r, msg="reconstruct_sketch response is None")
        # Bad plane
        r = self.client.reconstruct_sketch(sketch_data, sketch_plane="XXX")
        self.assertIsNone(r, msg="reconstruct_sketch response is None")
        # Bad scale
        r = self.client.reconstruct_sketch(
            sketch_data,
            sketch_plane="XY",
            scale={}
        )
        self.assertIsNone(r, msg="reconstruct_sketch response is None")
        # Bad translate
        r = self.client.reconstruct_sketch(
            sketch_data,
            sketch_plane="XY",
            translate={}
        )
        self.assertIsNone(r, msg="reconstruct_sketch response is None")

    def test_reconstruct_sketch(self):
        self.client.clear()
        with open(self.hex_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        sketch_id = json_data["timeline"][0]["entity"]
        sketch_data = json_data["entities"][sketch_id]
        # reconstruct sketch
        r = self.client.reconstruct_sketch(sketch_data)
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"])

    def test_reconstruct_sketch_transform(self):
        self.client.clear()
        with open(self.hex_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        sketch_id = json_data["timeline"][0]["entity"]
        sketch_data = json_data["entities"][sketch_id]

        # reconstruct sketch with some extra bells and whistles
        r = self.client.reconstruct_sketch(
            sketch_data,
            sketch_plane="YZ"
        )
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"])
        self.client.clear()

        scale = {"x": 2, "y": 2, "z": 1}
        translate = {"x": 5, "y": 0, "z": 0}
        rotate = {"x": 0, "y": 0, "z": 30}

        r = self.client.reconstruct_sketch(
            sketch_data,
            sketch_plane="XY",
            rotate=rotate
        )
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"])

        self.client.clear()
        r = self.client.reconstruct_sketch(
            sketch_data,
            sketch_plane="YZ",
            scale=scale,
            translate=translate
        )
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"])

        self.client.clear()
        r = self.client.reconstruct_sketch(
            sketch_data,
            sketch_plane="XY",
            scale=scale,
            translate=translate,
            rotate=rotate
        )
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"])

    def test_reconstruct_profile_invalid(self):
        self.client.clear()
        with open(self.hex_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        sketch_id = json_data["timeline"][0]["entity"]
        sketch_data = json_data["entities"][sketch_id]
        profile_keys = list(sketch_data["profiles"].keys())
        profile_id = profile_keys[0]

        # Create a sketch
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]

        # No data
        r = self.client.reconstruct_profile({}, sketch_name, profile_id)
        self.assertIsNone(r, msg="reconstruct_profile response is None")
        # Bad sketch name
        r = self.client.reconstruct_profile(sketch_data, "Sketchxxxx", profile_id)
        self.assertEqual(r.status_code, 500, msg="reconstruct_profile status code")
        # Bad profile id
        r = self.client.reconstruct_profile(sketch_data, sketch_name, "foo")
        self.assertIsNone(r, msg="reconstruct_profile response is None")

    def test_reconstruct_profile(self):
        self.client.clear()
        with open(self.hex_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        sketch_id = json_data["timeline"][0]["entity"]
        sketch_data = json_data["entities"][sketch_id]
        profile_keys = list(sketch_data["profiles"].keys())
        profile_id = profile_keys[0]

        # Create a sketch
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]

        # Draw the profile on the sketch
        r = self.client.reconstruct_profile(sketch_data, sketch_name, profile_id)
        self.assertIsNotNone(r, msg="reconstruct profile response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct profile status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"])

        sketch_id = json_data["timeline"][4]["entity"]
        sketch_data = json_data["entities"][sketch_id]
        profile_keys = list(sketch_data["profiles"].keys())
        profile_id = profile_keys[1]

        # Draw another profile on the sketch
        r = self.client.reconstruct_profile(sketch_data, sketch_name, profile_id)
        self.assertIsNotNone(r, msg="reconstruct profile response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct profile status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"])

    def test_reconstruct_profile_transform(self):
        self.client.clear()
        with open(self.hex_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        sketch_id = json_data["timeline"][0]["entity"]
        sketch_data = json_data["entities"][sketch_id]
        profile_keys = list(sketch_data["profiles"].keys())
        profile_id = profile_keys[0]

        # Create a sketch
        r = self.client.add_sketch("XY")
        response_json = r.json()
        response_data = response_json["data"]
        sketch_name = response_data["sketch_name"]

        scale = {"x": 2, "y": 2, "z": 1}
        translate = {"x": 5, "y": 0, "z": 0}
        rotate = {"x": 0, "y": 0, "z": 30}

        # Draw the profile on the sketch
        r = self.client.reconstruct_profile(sketch_data, sketch_name, profile_id, scale=scale)
        self.assertIsNotNone(r, msg="reconstruct profile response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct profile status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"])

        r = self.client.reconstruct_profile(sketch_data, sketch_name, profile_id, translate=translate)
        self.assertIsNotNone(r, msg="reconstruct profile response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct profile status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"])

        r = self.client.reconstruct_profile(sketch_data, sketch_name, profile_id, rotate=rotate)
        self.assertIsNotNone(r, msg="reconstruct profile response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct profile status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"])

    def test_reconstruct_curve_invalid(self):
        self.client.clear()
        # Add sketch
        r = self.client.add_sketch("XY")
        self.assertEqual(r.status_code, 200, msg="add_sketch status code")
        response_json = r.json()
        response_data = response_json["data"]
        self.assertIn("sketch_name", response_data, msg="add_sketch response has sketch_name")
        sketch_name = response_data["sketch_name"]

        r = self.client.reconstruct_curve({}, sketch_name, "xxx")
        self.assertIsNone(r, msg="reconstruct_curve response is None")

        r = self.client.reconstruct_curve({"curves": {}}, sketch_name, "xxx")
        self.assertIsNone(r, msg="reconstruct_curve response is None")

    def test_reconstruct_curve(self):
        self.client.clear()
        with open(self.hex_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        sketch_id = json_data["timeline"][0]["entity"]
        sketch_data = json_data["entities"][sketch_id]
        curve_ids = list(sketch_data["curves"].keys())

        # Add sketch
        r = self.client.add_sketch("XY")
        self.assertEqual(r.status_code, 200, msg="add_sketch status code")
        response_json = r.json()
        response_data = response_json["data"]
        self.assertIn("sketch_name", response_data, msg="add_sketch response has sketch_name")
        sketch_name = response_data["sketch_name"]

        # reconstruct all curves one by one
        for curve_id in curve_ids:
            r = self.client.reconstruct_curve(sketch_data, sketch_name, curve_id)
            self.assertIsNotNone(r, msg="reconstruct response is not None")
            self.assertEqual(r.status_code, 200, msg="reconstruct status code")
            response_json = r.json()
            self.__test_sketch_response(response_json["data"], False)
        self.__test_sketch_response(response_json["data"])

    def test_reconstruct_curve_transform(self):
        self.client.clear()
        with open(self.hex_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        sketch_id = json_data["timeline"][0]["entity"]
        sketch_data = json_data["entities"][sketch_id]
        curve_ids = list(sketch_data["curves"].keys())

        # Add sketch
        r = self.client.add_sketch("XY")
        self.assertEqual(r.status_code, 200, msg="add_sketch status code")
        response_json = r.json()
        response_data = response_json["data"]
        self.assertIn("sketch_name", response_data, msg="add_sketch response has sketch_name")
        sketch_name = response_data["sketch_name"]

        scale = {"x": 2, "y": 2, "z": 1}
        translate = {"x": 5, "y": 0, "z": 0}
        rotate = {"x": 0, "y": 0, "z": 30}

        r = self.client.reconstruct_curve(sketch_data, sketch_name,
                                          curve_ids[0], scale=scale)
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"], False)

        r = self.client.reconstruct_curve(sketch_data, sketch_name,
                                          curve_ids[0], scale=scale,
                                          translate=translate)
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"], False)

        r = self.client.reconstruct_curve(sketch_data, sketch_name,
                                          curve_ids[0], scale=scale,
                                          translate=translate, rotate=rotate)
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        response_json = r.json()
        self.__test_sketch_response(response_json["data"], False)

    def __test_sketch_response(self, response_data, has_profiles=True):
        """Check that the sketch response is valid"""
        # self.assertIn("sketch_id", response_data, msg="reconstruct_sketch response has sketch_id")
        # self.assertIsInstance(response_data["sketch_id"], str, msg="sketch_id is str")
        self.assertIn("sketch_name", response_data, msg="reconstruct_sketch response has sketch_name")
        self.assertIsInstance(response_data["sketch_name"], str, msg="sketch_name is str")
        self.assertIn("profiles", response_data, msg="reconstruct_sketch response has profiles")
        self.assertIsInstance(response_data["profiles"], dict, msg="profiles is dict")
        if has_profiles:
            self.assertGreater(len(response_data["profiles"]), 0, msg="profiles len > 0")

    # @classmethod
    # def tearDownClass(cls):
    #     cls.client.detach()

if __name__ == "__main__":
    unittest.main()
