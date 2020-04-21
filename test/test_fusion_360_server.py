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
        cls.data_path = Path(TEST_DIR) / "data"
        # Good json reconstruction file
        cls.test_json_file = cls.data_path / "SingleSketchExtrude_RootComponent.json"
        # Invalid json reconstruction file
        cls.test_json_invalid_file = cls.data_path / "SingleSketchExtrude_Invalid.json"
        # Mesh stl file
        cls.test_mesh_file = cls.data_path / "SingleSketchExtrude_RootComponent.stl"
        # Clear all documents so we start with a clean slate
        cls.client.clear()

    def test_ping(self):
        r = self.client.ping()
        self.assertEqual(r.status_code, 200, msg="ping status code")

    def test_reconstruct_non_file(self):
        bad_data_path = Path("datazzzz")
        json_file = bad_data_path / "not_a_file.json"
        r = self.client.reconstruct(json_file)
        self.assertIsNone(r, msg="reconstruct response is None")

    def test_reconstruct(self):
        r = self.client.reconstruct(self.test_json_file)
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        r = self.client.clear()
        self.assertEqual(r.status_code, 200, msg="clear status code")

    def test_reconstruct_invalid_file(self):
        r = self.client.reconstruct(self.test_json_invalid_file)
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 500, msg="reconstruct status code is 500")
        r = self.client.clear()

    def test_mesh(self):
        # Reconstruct first
        r = self.client.reconstruct(self.test_json_file)
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        # Save out the mesh
        r = self.client.mesh(self.test_mesh_file)
        self.assertEqual(r.status_code, 200, msg="mesh status code")
        self.assertTrue(self.test_mesh_file.exists())
        self.assertGreater(self.test_mesh_file.stat().st_size, 0, msg="mesh file size greater than 0")
        r = self.client.clear()
        self.assertEqual(r.status_code, 200, msg="clear status code")

    @unittest.skip("Skipping detach")
    def test_detach(self):
        r = self.client.detach()
        self.assertEqual(r.status_code, 200)

    # @classmethod
    # def tearDownClass(cls):
    #     cls.client.detach()


if __name__ == '__main__':
    unittest.main()
