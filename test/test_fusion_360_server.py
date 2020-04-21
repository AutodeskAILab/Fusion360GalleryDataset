import unittest
import requests
from pathlib import Path
import sys
import os
import numpy
from stl import mesh

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
        # TEST FILES
        cls.data_path = Path(TEST_DIR) / "data"
        filename = "SingleSketchExtrude_RootComponent"
        # Good json reconstruction file
        cls.test_json_file = cls.data_path / f"{filename}.json"
        # Invalid json reconstruction file
        cls.test_json_invalid_file = cls.data_path / f"{filename}_Invalid.json"
        # Mesh stl file
        cls.test_mesh_file = cls.data_path / f"{filename}.stl"
        # BRep step file
        cls.test_brep_step_file = cls.data_path / f"{filename}.step"
        # BRep smt file
        cls.test_brep_smt_file = cls.data_path / f"{filename}.smt"
        # Clear all documents so we start with a clean slate
        cls.client.clear()

    def test_ping(self):
        r = self.client.ping()
        self.assertEqual(r.status_code, 200, msg="ping status code")

    def test_clear(self):
        r = self.client.clear()
        self.assertEqual(r.status_code, 200, msg="clear status code")

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

    def test_reconstruct_invalid_file(self):
        r = self.client.reconstruct(self.test_json_invalid_file)
        self.assertIsNone(r, msg="reconstruct response is not None")
        r = self.client.clear()

    def test_mesh_invalid_format(self):
        # Reconstruct first
        r = self.client.reconstruct(self.test_json_file)
        # Save out the mesh
        test_invalid_mesh_file = self.data_path / "file.obj"
        r = self.client.mesh(test_invalid_mesh_file)
        self.assertIsNone(r, msg="mesh response is None")
        r = self.client.clear()

    def test_mesh(self):
        # Reconstruct first
        r = self.client.reconstruct(self.test_json_file)
        # Save out the mesh
        r = self.client.mesh(self.test_mesh_file)
        self.assertIsNotNone(r, msg="mesh response is not None")
        self.assertEqual(r.status_code, 200, msg="mesh status code")
        self.assertTrue(self.test_mesh_file.exists())
        self.assertGreater(self.test_mesh_file.stat().st_size, 0, msg="mesh file size greater than 0")
        # Check the mesh data
        local_mesh = mesh.Mesh.from_file(self.test_mesh_file)
        volume, cog, inertia = local_mesh.get_mass_properties()
        self.assertAlmostEqual(volume, 12.5)
        self.assertAlmostEqual(cog[0], 2.5)
        self.assertAlmostEqual(cog[1], 0.5)
        self.assertAlmostEqual(cog[2], 1.25)
        self.assertEqual(len(local_mesh.points), 12)
        # Clear
        r = self.client.clear()
        self.test_mesh_file.unlink()

    def test_mesh_invalid_format(self):
        # Reconstruct first
        r = self.client.reconstruct(self.test_json_file)
        # Save out the mesh
        test_invalid_file = self.data_path / "file.obj"
        r = self.client.mesh(test_invalid_file)
        self.assertIsNone(r, msg="mesh response is None")
        # Clear
        r = self.client.clear()

    def test_brep_step(self):
        # Reconstruct first
        r = self.client.reconstruct(self.test_json_file)
        # Save out the brep
        r = self.client.brep(self.test_brep_step_file)
        self.assertIsNotNone(r, msg="brep response is not None")
        self.assertEqual(r.status_code, 200, msg="brep status code")
        self.assertTrue(self.test_brep_step_file.exists())
        self.assertGreater(self.test_brep_step_file.stat().st_size, 0, msg="brep file size greater than 0")
        # Clear
        r = self.client.clear()
        self.test_brep_step_file.unlink()

    def test_brep_smt(self):
        # Reconstruct first
        r = self.client.reconstruct(self.test_json_file)
        # Save out the brep
        r = self.client.brep(self.test_brep_smt_file)
        self.assertIsNotNone(r, msg="brep response is not None")
        self.assertEqual(r.status_code, 200, msg="brep status code")
        self.assertTrue(self.test_brep_smt_file.exists())
        self.assertGreater(self.test_brep_smt_file.stat().st_size, 0, msg="brep file size greater than 0")
        # Clear
        r = self.client.clear()
        self.test_brep_smt_file.unlink()

    def test_brep_invalid_format(self):
        # Reconstruct first
        r = self.client.reconstruct(self.test_json_file)
        # Save out the mesh
        test_invalid_file = self.data_path / "file.sat"
        r = self.client.brep(test_invalid_file)
        self.assertIsNone(r, msg="brep response is None")
        # Clear
        r = self.client.clear()

    @unittest.skip("Skipping detach")
    def test_detach(self):
        r = self.client.detach()
        self.assertEqual(r.status_code, 200)

    # @classmethod
    # def tearDownClass(cls):
    #     cls.client.detach()


if __name__ == '__main__':
    unittest.main()
