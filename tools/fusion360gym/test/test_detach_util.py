"""

Test utility for detaching the server

"""
import unittest
import requests
import sys
import os
import importlib


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


class TestDetachUtil(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")

    # @unittest.skip("Skipping detach")
    def test_detach(self):
        r = self.client.detach()
        self.assertEqual(r.status_code, 200)


if __name__ == "__main__":
    unittest.main()
