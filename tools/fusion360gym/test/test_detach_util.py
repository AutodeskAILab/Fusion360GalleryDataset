"""

Test utility for detaching the server

"""
import unittest
import requests
import sys
import os
import importlib

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)
from fusion360gym_client import Fusion360GymClient

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


class TestDetachUtil(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")

    @unittest.skip("Skipping detach")
    def test_detach(self):
        r = self.client.detach()
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
