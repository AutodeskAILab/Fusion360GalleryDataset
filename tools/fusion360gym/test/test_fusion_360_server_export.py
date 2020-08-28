"""

Test export functionality of the Fusion 360 Server

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

from fusion_360_client import Fusion360Client

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


class TestFusion360ServerExport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")
        # Clear all documents so we start with a clean slate
        cls.client.clear()
        # ------------------------------------------
        # TEST FILES
        cls.data_dir = Path(__file__).parent.parent.parent / "testdata"
        box_design = "SingleSketchExtrude_RootComponent"
        hex_design = "Z0HexagonCutJoin_RootComponent"
        # Box json reconstruction file
        cls.box_design_json_file = cls.data_dir / f"{box_design}.json"
        # Hex shape json reconstruction file
        cls.hex_design_json_file = cls.data_dir / f"{hex_design}.json"
        #
        # OUTPUT FILES
        # Mesh stl file
        cls.test_mesh_stl_file = cls.data_dir / f"{box_design}.stl"
        # Mesh obj file
        cls.test_mesh_obj_file = cls.data_dir / f"{box_design}.obj"
        # BRep step file
        cls.test_brep_step_file = cls.data_dir / f"{box_design}.step"
        # BRep smt file
        cls.test_brep_smt_file = cls.data_dir / f"{box_design}.smt"
        # Sketch temp folder
        cls.sketch_dir = cls.data_dir / "sketches"
        # Make sure it is empty first
        if cls.sketch_dir.exists():
            shutil.rmtree(cls.sketch_dir)
        # ------------------------------------------

    def test_mesh_invalid_format(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the mesh
        test_invalid_mesh_file = self.data_dir / "file.obj"
        r = self.client.mesh(test_invalid_mesh_file)
        self.assertIsNone(r, msg="mesh response is None")
        r = self.client.clear()

    def test_mesh_stl(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the mesh
        r = self.client.mesh(self.test_mesh_stl_file)
        self.assertIsNotNone(r, msg="mesh response is not None")
        self.assertEqual(r.status_code, 200, msg="mesh status code")
        self.assertTrue(self.test_mesh_stl_file.exists())
        self.__test_box_mesh(self.test_mesh_stl_file)
        # Clear
        r = self.client.clear()
        self.test_mesh_stl_file.unlink()

    def test_mesh_obj(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the mesh
        r = self.client.mesh(self.test_mesh_obj_file)
        self.assertIsNotNone(r, msg="mesh response is not None")
        self.assertEqual(r.status_code, 200, msg="mesh status code")
        self.assertTrue(self.test_mesh_obj_file.exists())
        # Clear
        r = self.client.clear()
        self.test_mesh_obj_file.unlink()

    def test_mesh_invalid_format(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the mesh
        test_invalid_file = self.data_dir / "file.off"
        r = self.client.mesh(test_invalid_file)
        self.assertIsNone(r, msg="mesh response is None")
        # Clear
        r = self.client.clear()

    def test_brep_step(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
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
        r = self.client.reconstruct(self.box_design_json_file)
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
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the mesh
        test_invalid_file = self.data_dir / "file.sat"
        r = self.client.brep(test_invalid_file)
        self.assertIsNone(r, msg="brep response is None")
        # Clear
        r = self.client.clear()

    def test_sketches_png(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Make the folder
        if not self.sketch_dir.exists():
            self.sketch_dir.mkdir()
        # Save out the sketches
        r = self.client.sketches(self.sketch_dir)
        self.assertIsNotNone(r, msg="sketches response is not None")
        self.assertEqual(r.status_code, 200, msg="sketch status code")
        for i in range(1):
            sketch_file = self.sketch_dir / f"Sketch{i+1}.png"
            self.assertTrue(sketch_file.exists())
            self.assertGreater(sketch_file.stat().st_size, 0, msg="sketch image file size greater than 0")
        # Clear
        r = self.client.clear()
        shutil.rmtree(self.sketch_dir)

    def test_sketches_png_multiple(self):
        # Reconstruct first
        r = self.client.reconstruct(self.hex_design_json_file)
        # Make the folder
        if not self.sketch_dir.exists():
            self.sketch_dir.mkdir()
        # Save out the sketches
        r = self.client.sketches(self.sketch_dir)
        self.assertIsNotNone(r, msg="sketches response is not None")
        self.assertEqual(r.status_code, 200, msg="sketch status code")
        for i in range(3):
            sketch_file = self.sketch_dir / f"Sketch{i+1}.png"
            self.assertTrue(sketch_file.exists())
            self.assertGreater(sketch_file.stat().st_size, 0, msg="sketch image file size greater than 0")
            sketch_file.unlink()
        # Clear
        r = self.client.clear()
        self.sketch_dir.rmdir()

    def test_sketches_dxf(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Make the folder
        if not self.sketch_dir.exists():
            self.sketch_dir.mkdir()
        # Save out the sketches
        r = self.client.sketches(self.sketch_dir, ".dxf")
        self.assertIsNotNone(r, msg="sketches response is not None")
        self.assertEqual(r.status_code, 200, msg="sketch status code")
        for i in range(1):
            sketch_file = self.sketch_dir / f"Sketch{i+1}.dxf"
            self.assertTrue(sketch_file.exists())
            self.assertGreater(sketch_file.stat().st_size, 0, msg="sketch dxf file size greater than 0")
        # Clear
        r = self.client.clear()
        shutil.rmtree(self.sketch_dir)

    def test_sketches_dxf_multiple(self):
        # Reconstruct first
        r = self.client.reconstruct(self.hex_design_json_file)
        # Make the folder
        if not self.sketch_dir.exists():
            self.sketch_dir.mkdir()
        # Save out the sketches
        r = self.client.sketches(self.sketch_dir, ".dxf")
        self.assertIsNotNone(r, msg="sketches response is not None")
        self.assertEqual(r.status_code, 200, msg="sketch status code")
        for i in range(3):
            sketch_file = self.sketch_dir / f"Sketch{i+1}.dxf"
            self.assertTrue(sketch_file.exists())
            self.assertGreater(sketch_file.stat().st_size, 0, msg="sketch dxf file size greater than 0")
        # Clear
        r = self.client.clear()
        shutil.rmtree(self.sketch_dir)

    def test_sketches_invalid_format(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the mesh
        test_invalid_dir = self.data_dir / "yo"
        r = self.client.sketches(test_invalid_dir)
        self.assertIsNone(r, msg="sketch response is None")
        # Clear
        r = self.client.clear()

    def __test_box_mesh(self, mesh_file):
        # Check the mesh data
        local_mesh = mesh.Mesh.from_file(mesh_file)
        volume, cog, inertia = local_mesh.get_mass_properties()
        self.assertAlmostEqual(volume, 12.5)
        self.assertAlmostEqual(cog[0], 2.5)
        self.assertAlmostEqual(cog[1], 0.5)
        self.assertAlmostEqual(cog[2], 1.25)
        self.assertEqual(len(local_mesh.points), 12)

    # @classmethod
    # def tearDownClass(cls):
    #     cls.client.detach()

if __name__ == "__main__":
    unittest.main()
