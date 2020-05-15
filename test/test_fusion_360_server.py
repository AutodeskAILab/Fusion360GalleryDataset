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


class TestFusion360Server(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")
        # Clear all documents so we start with a clean slate
        cls.client.clear()
        # ------------------------------------------
        # TEST FILES
        cls.data_dir = Path(ROOT_DIR) / "data"
        box_design = "SingleSketchExtrude_RootComponent"
        hex_design = "Z0HexagonCutJoin_RootComponent"
        # Box json reconstruction file
        cls.box_design_json_file = cls.data_dir / f"{box_design}.json"
        # Hex shape json reconstruction file
        cls.hex_design_json_file = cls.data_dir / f"{hex_design}.json"
        # Invalid json reconstruction file
        cls.test_json_invalid_file = cls.data_dir / f"{box_design}_Invalid.json"
        #
        # OUTPUT FILES
        # Mesh stl file
        cls.test_mesh_file = cls.data_dir / f"{box_design}.stl"
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

    def test_ping(self):
        r = self.client.ping()
        self.assertEqual(r.status_code, 200, msg="ping status code")

    def test_refresh(self):
        r = self.client.refresh()
        self.assertEqual(r.status_code, 200, msg="refresh status code")

    def test_clear(self):
        r = self.client.clear()
        self.assertEqual(r.status_code, 200, msg="clear status code")

    def test_reconstruct_non_file(self):
        bad_data_dir = Path("datazzzz")
        json_file = bad_data_dir / "not_a_file.json"
        r = self.client.reconstruct(json_file)
        self.assertIsNone(r, msg="reconstruct response is None")

    def test_reconstruct(self):
        r = self.client.reconstruct(self.box_design_json_file)
        self.assertIsNotNone(r, msg="reconstruct response is not None")
        self.assertEqual(r.status_code, 200, msg="reconstruct status code")
        r = self.client.clear()

    def test_reconstruct_invalid_file(self):
        r = self.client.reconstruct(self.test_json_invalid_file)
        self.assertIsNone(r, msg="reconstruct response is not None")
        r = self.client.clear()

    def test_mesh_invalid_format(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the mesh
        test_invalid_mesh_file = self.data_dir / "file.obj"
        r = self.client.mesh(test_invalid_mesh_file)
        self.assertIsNone(r, msg="mesh response is None")
        r = self.client.clear()

    def test_mesh(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the mesh
        r = self.client.mesh(self.test_mesh_file)
        self.assertIsNotNone(r, msg="mesh response is not None")
        self.assertEqual(r.status_code, 200, msg="mesh status code")
        self.__test_box_mesh(self.test_mesh_file)
        # Clear
        r = self.client.clear()
        self.test_mesh_file.unlink()

    def test_mesh_invalid_format(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the mesh
        test_invalid_file = self.data_dir / "file.obj"
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

    def test_commands_clear_ping(self):
        command_list = [
            {"command": "clear"},
            {"command": "ping"}
        ]
        r = self.client.commands(command_list)
        self.assertIsNotNone(r, msg="commands response is not None")
        self.assertEqual(r.status_code, 200, msg="commands status code")

    def test_commands_reconstruct_mesh_clear(self):
        self.__test_commands_reconstruct_model("mesh", ".stl")

    def test_commands_reconstruct_brep_step_clear(self):
        self.__test_commands_reconstruct_model("brep", ".step")

    def test_commands_reconstruct_brep_smt_clear(self):
        self.__test_commands_reconstruct_model("brep", ".smt")

    def test_commands_reconstruct_sketches_dxf_clear(self):
        self.__test_commands_reconstruct_sketches(".dxf")

    def test_commands_reconstruct_sketches_png_clear(self):
        self.__test_commands_reconstruct_sketches(".png")

    def test_commands_reconstruct_sketches_png_mesh_clear(self):
        # Prepare the whole json file
        with open(self.hex_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        # Construct the command list
        command_list = [
            {
                "command": "reconstruct",
                "data": json_data
            },
            {
                "command": "sketches",
                "data": {
                    "format": ".png"
                }
            },
            {
                "command": "mesh",
                "data": {
                    "file": self.test_mesh_file.name
                }
            },
            {"command": "clear"}
        ]
        # Make the folder
        if not self.sketch_dir.exists():
            self.sketch_dir.mkdir()
        r = self.client.commands(command_list, self.sketch_dir)
        self.assertIsNotNone(r, msg="commands response is not None")
        self.assertEqual(r.status_code, 200, msg="commands status code")
        for i in range(3):
            sketch_file = self.sketch_dir / f"Sketch{i+1}.png"
            self.assertTrue(sketch_file.exists())
            self.assertGreater(sketch_file.stat().st_size, 0, msg="sketch png file size greater than 0")
        output_model = self.sketch_dir / self.test_mesh_file.name
        self.assertTrue(output_model.exists())
        self.assertGreater(output_model.stat().st_size, 0, msg="stl file size greater than 0")
        self.__test_hex_mesh(output_model)
        shutil.rmtree(self.sketch_dir)

    def __test_box_mesh(self, mesh_file):
        # Check the mesh data
        local_mesh = mesh.Mesh.from_file(mesh_file)
        volume, cog, inertia = local_mesh.get_mass_properties()
        self.assertAlmostEqual(volume, 12.5)
        self.assertAlmostEqual(cog[0], 2.5)
        self.assertAlmostEqual(cog[1], 0.5)
        self.assertAlmostEqual(cog[2], 1.25)
        self.assertEqual(len(local_mesh.points), 12)

    def __test_hex_mesh(self, mesh_file):
        # Check the mesh data
        local_mesh = mesh.Mesh.from_file(mesh_file)
        volume, cog, inertia = local_mesh.get_mass_properties()
        self.assertAlmostEqual(volume, 20.648000439008076)
        self.assertAlmostEqual(cog[0], 1.0659047)
        self.assertAlmostEqual(cog[1], 1.99999998)
        self.assertAlmostEqual(cog[2], 0.99999999)
        self.assertEqual(len(local_mesh.points), 64)

    def __test_commands_reconstruct_model(self, command, suffix):
        # Prepare the whole json file
        with open(self.box_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        output_model = self.sketch_dir / self.box_design_json_file.with_suffix(suffix).name
        # Construct the command list
        command_list = [
            {
                "command": "reconstruct",
                "data": json_data
            },
            {
                "command": command,
                "data": {
                    "file": output_model.name
                }
            },
            {"command": "clear"}
        ]
        # Make the folder
        if not self.sketch_dir.exists():
            self.sketch_dir.mkdir()
        r = self.client.commands(command_list, self.sketch_dir)
        self.assertIsNotNone(r, msg="commands response is not None")
        self.assertEqual(r.status_code, 200, msg="commands status code")
        self.assertTrue(output_model.exists())
        self.assertGreater(output_model.stat().st_size, 0, msg=f"{suffix} file size greater than 0")
        if suffix == ".stl":
            self.__test_box_mesh(output_model)
        shutil.rmtree(self.sketch_dir)

    def __test_commands_reconstruct_sketches(self, suffix):
        # Prepare the whole json file
        with open(self.hex_design_json_file) as file_handle:
            json_data = json.load(file_handle)
        # Construct the command list
        command_list = [
            {
                "command": "reconstruct",
                "data": json_data
            },
            {
                "command": "sketches",
                "data": {
                    "format": suffix
                }
            },
            {"command": "clear"}
        ]
        # Make the folder
        if not self.sketch_dir.exists():
            self.sketch_dir.mkdir()
        r = self.client.commands(command_list, self.sketch_dir)
        self.assertIsNotNone(r, msg="commands response is not None")
        self.assertEqual(r.status_code, 200, msg="commands status code")
        for i in range(3):
            sketch_file = self.sketch_dir / f"Sketch{i+1}{suffix}"
            self.assertTrue(sketch_file.exists())
            self.assertGreater(sketch_file.stat().st_size, 0, msg=f"sketch {suffix} file size greater than 0")
        shutil.rmtree(self.sketch_dir)

    # @classmethod
    # def tearDownClass(cls):
    #     cls.client.detach()



if __name__ == "__main__":
    unittest.main()
