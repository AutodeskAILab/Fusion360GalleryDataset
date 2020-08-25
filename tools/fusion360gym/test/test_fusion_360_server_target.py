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
        print(response_json)
        r = self.client.clear()
