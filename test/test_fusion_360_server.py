import unittest
import requests
from pathlib import Path
import sys
import os

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TEST_DIR)
CLIENT_DIR = os.path.join(ROOT_DIR, "client")

# Add the client folder to sys.path
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)
from fusion_360_client import Fusion360Client
sys.path.remove(CLIENT_DIR)

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


class TestFusion360Server(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")
        cls.data_path = Path("data")

    def test_ping(self):
        r = self.client.ping()
        self.assertEqual(r.status_code, 200)
        # print(r.json())
        # self.client.detach()
        # self.assertEqual(r.status_code, 200)

    # def test_reconstruct(self):
    #     json_file = self.data_path / "SingleSketchExtrude_RootComponent.json"
    #     r = self.client.reconstruct(json_file)
    #     self.assertEqual(r.status_code, 200)

    def test_detactch(self):
        r = self.client.detach()
        self.assertEqual(r.status_code, 200)

    # @classmethod
    # def tearDownClass(cls):
    #     cls.client.detach()


if __name__ == '__main__':
    unittest.main()
