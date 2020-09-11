"""

Test reconstruction from a target design using the Fusion 360 Server

"""

import unittest
import requests
from pathlib import Path
import sys
import os
import importlib
import json
import shutil
import time
import math

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)

from fusion_360_client import Fusion360Client

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


class TestFusion360ServerTarget(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")
        # Clear all documents so we start with a clean slate
        cls.client.clear()
        # ------------------------------------------
        # TEST FILES
        cls.data_dir = Path(__file__).parent.parent.parent / "testdata"
        couch_design = "Couch"
        cls.couch_design_json_file = cls.data_dir / f"{couch_design}.json"
        cls.couch_design_smt_file = cls.data_dir / f"{couch_design}.smt"
        cls.couch_design_step_file = cls.data_dir / f"{couch_design}.step"
        cls.box_design_smt_file = cls.data_dir / "Box.smt"
        cls.boxes_design_smt_file = cls.data_dir / "Boxes.smt"

    def test_set_target_invalid_file_suffix(self):
        r = self.client.set_target(self.couch_design_json_file)
        self.assertIsNone(r, msg="set_target response is None")

    def test_set_target_non_file(self):
        bad_data_dir = Path("datazzzz")
        smt_file = bad_data_dir / "not_a_file.smt"
        r = self.client.reconstruct(smt_file)
        self.assertIsNone(r, msg="set_target response is None")

    def test_set_target_smt(self):
        r = self.client.set_target(self.couch_design_smt_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        self.__check_graph_format(response_json["data"])
        self.__check_bounding_box(response_json["data"])
        r = self.client.clear()

    def test_set_target_step(self):
        r = self.client.set_target(self.couch_design_step_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        self.__check_graph_format(response_json["data"])
        self.__check_bounding_box(response_json["data"])
        r = self.client.clear()

    def test_set_target_box(self):
        r = self.client.set_target(self.box_design_smt_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        self.__check_graph_format(response_json["data"])
        self.__check_bounding_box(response_json["data"])
        # Check the bounding box result is correct
        bbox = response_json["data"]["bounding_box"]
        maxp = bbox["max_point"]
        minp = bbox["min_point"]
        x = math.fabs(maxp["x"] - minp["x"])
        y = math.fabs(maxp["y"] - minp["y"])
        z = math.fabs(maxp["z"] - minp["z"])
        self.assertAlmostEqual(x, 1, places=2, msg="bbox x ~= 1")
        self.assertAlmostEqual(y, 1, places=2, msg="bbox y ~= 1")
        self.assertAlmostEqual(z, 1, places=2, msg="bbox z ~= 1")
        r = self.client.clear()

    def test_set_target_boxes(self):
        r = self.client.set_target(self.boxes_design_smt_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        self.__check_graph_format(response_json["data"])
        self.__check_bounding_box(response_json["data"])
        bbox = response_json["data"]["bounding_box"]
        # Check the bounding box result is correct
        bbox = response_json["data"]["bounding_box"]
        maxp = bbox["max_point"]
        minp = bbox["min_point"]
        x = math.fabs(maxp["x"] - minp["x"])
        y = math.fabs(maxp["y"] - minp["y"])
        z = math.fabs(maxp["z"] - minp["z"])
        self.assertAlmostEqual(x, 4, places=2, msg="bbox x ~= 4")
        self.assertAlmostEqual(y, 4, places=2, msg="bbox y ~= 4")
        self.assertAlmostEqual(z, 2, places=2, msg="bbox z ~= 2")
        r = self.client.clear()

    def test_add_extrude_by_target_face(self):
        r = self.client.set_target(self.box_design_smt_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        graph = response_json["data"]["graph"]
        nodes = graph["nodes"]
        # Guessing these based on the order
        start_face = nodes[0]["id"]
        end_face = nodes[2]["id"]
        r = self.client.add_extrude_by_target_face(
            start_face,
            end_face,
            "NewBodyFeatureOperation"
        )
        self.assertIsNotNone(r, msg="add_extrude_by_target_face response is not None")
        self.assertEqual(r.status_code, 200, msg="add_extrude_by_target_face status code")
        response_json = r.json()
        response_data = response_json["data"]
        self.__check_graph_format(response_data)
        self.assertIn("iou", response_data, msg="response has iou")
        self.assertIsInstance(response_data["iou"], float, msg="iou is float")
        self.assertAlmostEqual(response_data["iou"], 1, places=4, msg="iou ~= 1")

    def test_add_extrude_by_target_face_invalid_end_face(self):
        r = self.client.set_target(self.box_design_smt_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        graph = response_json["data"]["graph"]
        nodes = graph["nodes"]
        # Choose an invalid end face that is not parallel to start face
        start_face = nodes[0]["id"]
        end_face = nodes[1]["id"]
        r = self.client.add_extrude_by_target_face(
            start_face,
            end_face,
            "NewBodyFeatureOperation"
        )
        self.assertIsNotNone(r, msg="add_extrude_by_target_face response is not None")
        self.assertEqual(r.status_code, 500, msg="add_extrude_by_target_face status code")

    def test_add_extrude_by_target_face_invalid_inputs(self):
        r = self.client.add_extrude_by_target_face(
            "",
            "okok",
            "NewBodyFeatureOperation"
        )
        self.assertIsNone(r, msg="add_extrude_by_target_face response is None")
        r = self.client.add_extrude_by_target_face(
            "ok",
            1,
            "NewBodyFeatureOperation"
        )
        self.assertIsNone(r, msg="add_extrude_by_target_face response is None")
        r = self.client.add_extrude_by_target_face(
            "ok",
            "yo",
            "ss"
        )
        self.assertIsNone(r, msg="add_extrude_by_target_face response is None")

    def test_set_extrude_reset_extrude(self):
        r = self.client.set_target(self.box_design_smt_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        graph = response_json["data"]["graph"]
        nodes = graph["nodes"]
        # Guessing these based on the order
        start_face = nodes[0]["id"]
        end_face = nodes[2]["id"]
        r = self.client.add_extrude_by_target_face(
            start_face,
            end_face,
            "NewBodyFeatureOperation"
        )
        # Revert to target
        r = self.client.revert_to_target()
        self.assertIsNotNone(r, msg="revert_to_target response is not None")
        self.assertEqual(r.status_code, 200, msg="revert_to_target status code")
        start_face = nodes[0]["id"]
        end_face = nodes[2]["id"]
        r = self.client.add_extrude_by_target_face(
            start_face,
            end_face,
            "NewBodyFeatureOperation"
        )
        self.assertIsNotNone(r, msg="add_extrude_by_target_face response is not None")
        self.assertEqual(r.status_code, 200, msg="add_extrude_by_target_face status code")
        response_json = r.json()
        response_data = response_json["data"]
        self.__check_graph_format(response_data)
        self.assertIn("iou", response_data, msg="response has iou")
        self.assertIsInstance(response_data["iou"], float, msg="iou is float")
        self.assertAlmostEqual(response_data["iou"], 1, places=4, msg="iou ~= 1")

    def test_add_extrudes_by_target_face(self):
        r = self.client.set_target(self.couch_design_smt_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        graph = response_json["data"]["graph"]
        nodes = graph["nodes"]
        # Guessing these based on the order
        r = self.client.add_extrudes_by_target_face([
            {
                "start_face": nodes[0]["id"],
                "end_face": nodes[9]["id"],
                "operation": "NewBodyFeatureOperation"
            },
            {
                "start_face": nodes[1]["id"],
                "end_face": nodes[3]["id"],
                "operation": "CutFeatureOperation"
            }
        ])
        self.assertIsNotNone(r, msg="add_extrudes_by_target_face response is not None")
        self.assertEqual(r.status_code, 200, msg="add_extrudes_by_target_face status code")
        response_json = r.json()
        response_data = response_json["data"]
        self.__check_graph_format(response_data)
        self.assertIn("iou", response_data, msg="response has iou")
        self.assertIsInstance(response_data["iou"], float, msg="iou is float")
        self.assertGreater(response_data["iou"], 0, msg="iou > 0")

    def test_add_extrudes_by_target_face_revert(self):
        r = self.client.set_target(self.couch_design_smt_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        graph = response_json["data"]["graph"]
        nodes = graph["nodes"]
        actions = [
            {
                "start_face": nodes[0]["id"],
                "end_face": nodes[9]["id"],
                "operation": "NewBodyFeatureOperation"
            },
            {
                "start_face": nodes[1]["id"],
                "end_face": nodes[3]["id"],
                "operation": "CutFeatureOperation"
            }
        ]
        r = self.client.add_extrudes_by_target_face(actions)
        response_json = r.json()
        response_data = response_json["data"]
        prev_iou = response_data["iou"]
        r = self.client.add_extrudes_by_target_face(actions, revert=True)
        self.assertIsNotNone(r, msg="add_extrudes_by_target_face response is not None")
        self.assertEqual(r.status_code, 200, msg="add_extrudes_by_target_face status code")
        response_json = r.json()
        response_data = response_json["data"]
        self.__check_graph_format(response_data)
        self.assertIn("iou", response_data, msg="response has iou")
        self.assertIsInstance(response_data["iou"], float, msg="iou is float")
        self.assertEqual(response_data["iou"], prev_iou, msg="iou == prev_iou")

    def test_add_extrudes_by_target_face_invalid_inputs(self):
        r = self.client.add_extrudes_by_target_face(
            "okok",
            "NewBodyFeatureOperation"
        )
        self.assertIsNone(r, msg="add_extrudes_by_target_face response is None")
        r = self.client.add_extrudes_by_target_face([{
            "start_face": None,
            "end_face": "ok",
            "operation": "NewBodyFeatureOperation"
        }])
        self.assertIsNone(r, msg="add_extrudes_by_target_face response is None")
        r = self.client.add_extrudes_by_target_face([])
        self.assertIsNone(r, msg="add_extrudes_by_target_face response is None")

    def __check_graph_format(self, response_data):
        """Check the graph data that comes back is in the right format"""
        self.assertIn("graph", response_data, msg="graph in response_data")
        graph = response_data["graph"]
        # Metadata check
        self.assertIsNotNone(graph, msg="Graph is not None")
        self.assertIn("directed", graph, msg="Graph has directed")
        self.assertFalse(graph["directed"], msg="Directs is false")
        self.assertIn("multigraph", graph, msg="Graph has multigraph")
        self.assertIn("graph", graph, msg="Graph has graph")
        self.assertFalse(graph["multigraph"], msg="Multigraph is false")
        self.assertIsInstance(graph["graph"], dict, msg="Graph graph is dict")
        # Node and link check
        self.assertIn("nodes", graph, msg="Graph has nodes")
        self.assertIsInstance(graph["nodes"], list, msg="Nodes is list")
        self.assertIn("links", graph, msg="Graph has links")
        self.assertIsInstance(graph["links"], list, msg="Links is list")
        self.assertGreaterEqual(len(graph["nodes"]), 3, msg="Graph nodes >= 3")
        self.assertGreaterEqual(len(graph["links"]), 2, msg="Graph links >= 3")
        node_set = set()
        node_list = []
        for node in graph["nodes"]:
            self.assertIn("id", node, msg="Graph node has id")
            node_set.add(node["id"])
            node_list.append(node["id"])
        self.assertEqual(len(node_set), len(node_list), msg="Graph nodes are unique")
        for link in graph["links"]:
            self.assertIn("id", link, msg="Graph link has id")
            # Check that the edges refer to existing faces
            self.assertIn("source", link, msg="Graph link has source")
            self.assertIn(link["source"], node_set, msg="Graph link source in node set")
            self.assertIn("target", link, msg="Graph link has target")
            self.assertIn(link["target"], node_set, msg="Graph link target in node set")

    def __check_bounding_box(self, response_data):
        """Check the bounding box data that comes back is in the right format"""
        self.assertIn("bounding_box", response_data, msg="bounding_box in response_data")
        bbox = response_data["bounding_box"]

        self.assertIn("max_point", bbox, msg="max_point in bounding_box")
        self.assertIn("x", bbox["max_point"], msg="x in max_point")
        self.assertIn("y", bbox["max_point"], msg="y in max_point")
        self.assertIn("z", bbox["max_point"], msg="z in max_point")
        self.assertIsInstance(bbox["max_point"]["x"], float, msg="max_point x is float")
        self.assertIsInstance(bbox["max_point"]["y"], float, msg="max_point y is float")
        self.assertIsInstance(bbox["max_point"]["z"], float, msg="max_point z is float")

        self.assertIn("min_point", bbox, msg="min_point in bounding_box")
        self.assertIn("x", bbox["min_point"], msg="x in min_point")
        self.assertIn("y", bbox["min_point"], msg="y in min_point")
        self.assertIn("z", bbox["min_point"], msg="z in min_point")
        self.assertIsInstance(bbox["min_point"]["x"], float, msg="min_point x is float")
        self.assertIsInstance(bbox["min_point"]["y"], float, msg="min_point y is float")
        self.assertIsInstance(bbox["min_point"]["z"], float, msg="min_point z is float")

        self.assertFalse(
            math.isinf(bbox["max_point"]["x"]),
            msg="bounding_box_max_x != inf"
        )
        self.assertFalse(
            math.isinf(bbox["max_point"]["y"]),
            msg="bounding_box_max_y != inf"
        )
        self.assertFalse(
            math.isinf(bbox["max_point"]["z"]),
            msg="bounding_box_max_z != inf"
        )
        self.assertFalse(
            math.isinf(bbox["min_point"]["x"]),
            msg="bounding_box_min_x != inf"
        )
        self.assertFalse(
            math.isinf(bbox["min_point"]["y"]),
            msg="bounding_box_min_y != inf"
        )
        self.assertFalse(
            math.isinf(bbox["min_point"]["z"]),
            msg="bounding_box_min_z != inf"
        )
