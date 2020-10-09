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
                    "file": self.test_mesh_stl_file.name
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
        output_model = self.sketch_dir / self.test_mesh_stl_file.name
        self.assertTrue(output_model.exists())
        self.assertGreater(output_model.stat().st_size, 0, msg="stl file size greater than 0")
        self.__test_hex_mesh(output_model)
        shutil.rmtree(self.sketch_dir)

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

    # @classmethod
    # def tearDownClass(cls):
    #     cls.client.detach()


if __name__ == "__main__":
    unittest.main()
