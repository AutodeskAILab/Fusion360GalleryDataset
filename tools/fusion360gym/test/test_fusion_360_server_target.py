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
        # Box json reconstruction file
        cls.couch_design_json_file = cls.data_dir / f"{couch_design}.json"
        cls.couch_design_smt_file = cls.data_dir / f"{couch_design}.smt"
        cls.couch_design_step_file = cls.data_dir / f"{couch_design}.step"

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
        self.check_graph_format(response_json["data"])
        r = self.client.clear()

    def test_set_target_step(self):
        r = self.client.set_target(self.couch_design_step_file)
        self.assertIsNotNone(r, msg="set_target response is not None")
        self.assertEqual(r.status_code, 200, msg="set_target status code")
        response_json = r.json()
        self.check_graph_format(response_json["data"])
        r = self.client.clear()

    def check_graph_format(self, response_data):
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
