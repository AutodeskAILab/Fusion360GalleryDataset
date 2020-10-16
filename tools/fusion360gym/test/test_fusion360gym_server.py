"""

Test basic functionality of the Fusion 360 Server
Including reconstruction

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


class TestFusion360Server(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")

    def test_ping(self):
        r = self.client.ping()
        self.assertEqual(r.status_code, 200, msg="ping status code")

    def test_refresh(self):
        r = self.client.refresh()
        self.assertEqual(r.status_code, 200, msg="refresh status code")

    def test_clear(self):
        r = self.client.clear()
        self.assertEqual(r.status_code, 200, msg="clear status code")

    # @classmethod
    # def tearDownClass(cls):
    #     cls.client.detach()


if __name__ == "__main__":
    unittest.main()
