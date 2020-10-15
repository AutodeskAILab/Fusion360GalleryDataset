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

import common_test

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)

from fusion360gym_client import Fusion360GymClient

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


class TestFusion360ServerExport(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")
        # Clear all documents so we start with a clean slate
        cls.client.clear()
        # ------------------------------------------
        # TEST FILES
        cls.data_dir = Path(__file__).parent.parent.parent / "testdata"
        cls.output_dir = cls.data_dir / "output"
        box_design = "SingleSketchExtrude"
        hex_design = "Hexagon"
        couch_design = "Couch"
        # Box json reconstruction file
        cls.box_design_json_file = cls.data_dir / f"{box_design}.json"
        # Hex shape json reconstruction file
        cls.hex_design_json_file = cls.data_dir / f"{hex_design}.json"
        # Couch design
        cls.couch_design_json_file = cls.data_dir / f"{couch_design}.json"
        #
        # OUTPUT FILES
        # Mesh stl file
        cls.test_mesh_stl_file = cls.output_dir / f"{box_design}.stl"
        # Mesh obj file
        cls.test_mesh_obj_file = cls.output_dir / f"{box_design}.obj"
        # BRep step file
        cls.test_brep_step_file = cls.output_dir / f"{box_design}.step"
        # BRep smt file
        cls.test_brep_smt_file = cls.output_dir / f"{box_design}.smt"
        # BRep f3d file
        cls.test_brep_f3d_file = cls.output_dir / f"{box_design}.f3d"
        # Screenshot png file
        cls.test_screenshot_png_file = cls.output_dir / f"{box_design}.png"
        # Test output temp folder
        cls.test_output_dir = cls.output_dir / "test_output"
        # Make sure it is empty first
        if cls.output_dir.exists():
            shutil.rmtree(cls.output_dir)
        if not cls.output_dir.exists():
            cls.output_dir.mkdir()
        if cls.test_output_dir.exists():
            shutil.rmtree(cls.test_output_dir)
        # Clean up after ourselves
        cls.clean_output = True
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
        if self.clean_output:
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
        if self.clean_output:
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
        if self.clean_output:
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
        # self.test_brep_smt_file.unlink()

    def test_brep_f3d(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the brep
        r = self.client.brep(self.test_brep_f3d_file)
        self.assertIsNotNone(r, msg="brep response is not None")
        self.assertEqual(r.status_code, 200, msg="brep status code")
        self.assertTrue(self.test_brep_f3d_file.exists())
        self.assertGreater(self.test_brep_f3d_file.stat().st_size, 0, msg="brep file size greater than 0")
        # Clear
        r = self.client.clear()
        if self.clean_output:
            self.test_brep_f3d_file.unlink()

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
        if not self.test_output_dir.exists():
            self.test_output_dir.mkdir()
        # Save out the sketches
        r = self.client.sketches(self.test_output_dir)
        self.assertIsNotNone(r, msg="sketches response is not None")
        self.assertEqual(r.status_code, 200, msg="sketch status code")
        for i in range(1):
            sketch_file = self.test_output_dir / f"Sketch{i+1}.png"
            self.assertTrue(sketch_file.exists())
            self.assertGreater(sketch_file.stat().st_size, 0, msg="sketch image file size greater than 0")
        # Clear
        r = self.client.clear()
        if self.clean_output:
            shutil.rmtree(self.test_output_dir)

    def test_sketches_png_multiple(self):
        # Reconstruct first
        r = self.client.reconstruct(self.hex_design_json_file)
        # Make the folder
        if not self.test_output_dir.exists():
            self.test_output_dir.mkdir()
        # Save out the sketches
        r = self.client.sketches(self.test_output_dir)
        self.assertIsNotNone(r, msg="sketches response is not None")
        self.assertEqual(r.status_code, 200, msg="sketch status code")
        for i in range(3):
            sketch_file = self.test_output_dir / f"Sketch{i+1}.png"
            self.assertTrue(sketch_file.exists())
            self.assertGreater(sketch_file.stat().st_size, 0, msg="sketch image file size greater than 0")
        # Clear
        r = self.client.clear()
        if self.clean_output:
            shutil.rmtree(self.test_output_dir)

    def test_sketches_dxf(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Make the folder
        if not self.test_output_dir.exists():
            self.test_output_dir.mkdir()
        # Save out the sketches
        r = self.client.sketches(self.test_output_dir, ".dxf")
        self.assertIsNotNone(r, msg="sketches response is not None")
        self.assertEqual(r.status_code, 200, msg="sketch status code")
        for i in range(1):
            sketch_file = self.test_output_dir / f"Sketch{i+1}.dxf"
            self.assertTrue(sketch_file.exists())
            self.assertGreater(sketch_file.stat().st_size, 0, msg="sketch dxf file size greater than 0")
        # Clear
        r = self.client.clear()
        if self.clean_output:
            shutil.rmtree(self.test_output_dir)

    def test_sketches_dxf_multiple(self):
        # Reconstruct first
        r = self.client.reconstruct(self.hex_design_json_file)
        # Make the folder
        if not self.test_output_dir.exists():
            self.test_output_dir.mkdir()
        # Save out the sketches
        r = self.client.sketches(self.test_output_dir, ".dxf")
        self.assertIsNotNone(r, msg="sketches response is not None")
        self.assertEqual(r.status_code, 200, msg="sketch status code")
        for i in range(3):
            sketch_file = self.test_output_dir / f"Sketch{i+1}.dxf"
            self.assertTrue(sketch_file.exists())
            self.assertGreater(sketch_file.stat().st_size, 0, msg="sketch dxf file size greater than 0")
        # Clear
        r = self.client.clear()
        if self.clean_output:
            shutil.rmtree(self.test_output_dir)

    def test_sketches_invalid_format(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the mesh
        test_invalid_dir = self.data_dir / "yo"
        r = self.client.sketches(test_invalid_dir)
        self.assertIsNone(r, msg="sketch response is None")
        # Clear
        r = self.client.clear()

    def test_screenshot(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the brep
        r = self.client.screenshot(self.test_screenshot_png_file)
        self.assertIsNotNone(r, msg="screenshot response is not None")
        self.assertEqual(r.status_code, 200, msg="screenshot status code")
        self.assertTrue(self.test_screenshot_png_file.exists(), msg="screenshot exists")
        self.assertGreater(self.test_screenshot_png_file.stat().st_size, 0, msg="screenshot file size greater than 0")
        # Clear
        r = self.client.clear()
        if self.clean_output:
            self.test_screenshot_png_file.unlink()

    def test_screenshot_with_args(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        # Save out the brep
        r = self.client.screenshot(self.test_screenshot_png_file, 100, 100, False)
        self.assertIsNotNone(r, msg="screenshot response is not None")
        self.assertEqual(r.status_code, 200, msg="screenshot status code")
        self.assertTrue(self.test_screenshot_png_file.exists(), msg="screenshot exists")
        self.assertGreater(self.test_screenshot_png_file.stat().st_size, 0, msg="screenshot file size greater than 0")
        # Clear
        r = self.client.clear()
        if self.clean_output:
            self.test_screenshot_png_file.unlink()

    def test_screenshot_invalid_format(self):
        # Reconstruct first
        r = self.client.reconstruct(self.box_design_json_file)
        test_invalid_file = self.data_dir / "file.gif"
        r = self.client.screenshot(test_invalid_file)
        self.assertIsNone(r, msg="screenshot response is None")
        # Clear
        r = self.client.clear()

    def test_graph_per_face(self):
        # Reconstruct first
        r = self.client.reconstruct(self.couch_design_json_file)
        # Get the graph
        r = self.client.graph(
            format="PerFace",
            sequence=False
        )
        self.assertIsNotNone(r, msg="graph response is not None")
        self.assertEqual(r.status_code, 200, msg="graph status code")
        response_json = r.json()
        common_test.check_graph_format(self, response_json["data"], mode="PerFace")
        common_test.check_bounding_box(self, response_json["data"])
        r = self.client.clear()

    def test_graph_per_face_labels(self):
        # Reconstruct first
        r = self.client.reconstruct(self.couch_design_json_file)
        r = self.client.graph(
            format="PerFace",
            sequence=False,
            labels=True
        )
        self.assertIsNotNone(r, msg="graph response is not None")
        self.assertEqual(r.status_code, 200, msg="graph status code")
        response_json = r.json()
        common_test.check_graph_format(
            self, response_json["data"],mode="PerFace", labels=True)
        common_test.check_bounding_box(self, response_json["data"])
        r = self.client.clear()

    def test_graph_per_extrude(self):
        # Reconstruct first
        r = self.client.reconstruct(self.couch_design_json_file)
        # Get the graph
        r = self.client.graph(
            format="PerExtrude",
            sequence=False
        )
        self.assertIsNotNone(r, msg="graph response is not None")
        self.assertEqual(r.status_code, 200, msg="graph status code")
        response_json = r.json()
        common_test.check_graph_format(self, response_json["data"], mode="PerExtrude")
        common_test.check_bounding_box(self, response_json["data"])
        r = self.client.clear()

    def test_graph_per_extrude_labels(self):
        # Reconstruct first
        r = self.client.reconstruct(self.couch_design_json_file)
        r = self.client.graph(
            format="PerExtrude",
            sequence=False,
            labels=True
        )
        self.assertIsNotNone(r, msg="graph response is not None")
        self.assertEqual(r.status_code, 200, msg="graph status code")
        response_json = r.json()
        common_test.check_graph_format(
            self, response_json["data"], mode="PerExtrude", labels=True)
        common_test.check_bounding_box(self, response_json["data"])
        r = self.client.clear()

    def test_graph_sequence_per_face(self):
        # Reconstruct first
        r = self.client.reconstruct(self.couch_design_json_file)
        # Make the folder
        if not self.test_output_dir.exists():
            self.test_output_dir.mkdir()
        # Save out the graphs
        r = self.client.graph(
            self.couch_design_json_file,
            self.test_output_dir,
            format="PerFace",
            sequence=True
        )
        self.assertIsNotNone(r, msg="graph response is not None")
        self.assertEqual(r.status_code, 200, msg="graph status code")
        graph_file = self.test_output_dir / f"{self.couch_design_json_file.stem}_0000.json"
        self.assertTrue(graph_file.exists(), msg="graph file exists")
        self.assertGreater(graph_file.stat().st_size, 0, msg="graph file size greater than 0")
        common_test.check_graph_format(self, graph_file, mode="PerFace")

        graph_file = self.test_output_dir / f"{self.couch_design_json_file.stem}_0001.json"
        self.assertTrue(graph_file.exists(), msg="graph file exists")
        self.assertGreater(graph_file.stat().st_size, 0, msg="graph file size greater than 0")
        common_test.check_graph_format(self, graph_file, mode="PerFace")

        seq_file = self.test_output_dir / f"{self.couch_design_json_file.stem}_sequence.json"
        self.assertTrue(seq_file.exists(), msg="sequence file exists")
        self.assertGreater(seq_file.stat().st_size, 0, msg="sequence file size greater than 0")
        # Clear
        r = self.client.clear()
        if self.clean_output:
            shutil.rmtree(self.test_output_dir)

    def test_graph_sequence_per_face_labels(self):
        # Reconstruct first
        r = self.client.reconstruct(self.couch_design_json_file)
        # Make the folder
        if not self.test_output_dir.exists():
            self.test_output_dir.mkdir()
        # Save out the graphs
        r = self.client.graph(
            self.couch_design_json_file,
            self.test_output_dir,
            format="PerFace",
            sequence=True,
            labels=True
        )
        self.assertIsNotNone(r, msg="graph response is not None")
        self.assertEqual(r.status_code, 200, msg="graph status code")
        graph_file = self.test_output_dir / f"{self.couch_design_json_file.stem}_0000.json"
        self.assertTrue(graph_file.exists(), msg="graph file exists")
        self.assertGreater(graph_file.stat().st_size, 0, msg="graph file size greater than 0")
        common_test.check_graph_format(self, graph_file, mode="PerFace", labels=True)

        graph_file = self.test_output_dir / f"{self.couch_design_json_file.stem}_0001.json"
        self.assertTrue(graph_file.exists(), msg="graph file exists")
        self.assertGreater(graph_file.stat().st_size, 0, msg="graph file size greater than 0")
        common_test.check_graph_format(self, graph_file, mode="PerFace", labels=True)

        seq_file = self.test_output_dir / f"{self.couch_design_json_file.stem}_sequence.json"
        self.assertTrue(seq_file.exists(), msg="sequence file exists")
        self.assertGreater(seq_file.stat().st_size, 0, msg="sequence file size greater than 0")
        # Clear
        r = self.client.clear()
        if self.clean_output:
            shutil.rmtree(self.test_output_dir)

    def test_graph_sequence_per_extrude(self):
        # Reconstruct first
        r = self.client.reconstruct(self.hex_design_json_file)
        # Make the folder
        if not self.test_output_dir.exists():
            self.test_output_dir.mkdir()
        # Save out the graphs
        r = self.client.graph(
            self.hex_design_json_file,
            self.test_output_dir,
            format="PerExtrude",
            sequence=True
        )
        self.assertIsNotNone(r, msg="graph response is not None")
        self.assertEqual(r.status_code, 200, msg="graph status code")
        graph_file = self.test_output_dir / f"{self.hex_design_json_file.stem}_0000.json"
        self.assertTrue(graph_file.exists(), msg="graph file exists")
        self.assertGreater(graph_file.stat().st_size, 0, msg="graph file size greater than 0")
        common_test.check_graph_format(self, graph_file, mode="PerExtrude")

        graph_file = self.test_output_dir / f"{self.hex_design_json_file.stem}_0001.json"
        self.assertTrue(graph_file.exists(), msg="graph file exists")
        self.assertGreater(graph_file.stat().st_size, 0, msg="graph file size greater than 0")
        common_test.check_graph_format(self, graph_file, mode="PerExtrude")

        graph_file = self.test_output_dir / f"{self.hex_design_json_file.stem}_0002.json"
        self.assertTrue(graph_file.exists(), msg="graph file exists")
        self.assertGreater(graph_file.stat().st_size, 0, msg="graph file size greater than 0")
        common_test.check_graph_format(self, graph_file, mode="PerExtrude")

        # Clear
        r = self.client.clear()
        if self.clean_output:
            shutil.rmtree(self.test_output_dir)

    def test_graph_sequence_per_extrude_labels(self):
        # Reconstruct first
        r = self.client.reconstruct(self.hex_design_json_file)
        # Make the folder
        if not self.test_output_dir.exists():
            self.test_output_dir.mkdir()
        # Save out the graphs
        r = self.client.graph(
            self.hex_design_json_file,
            self.test_output_dir,
            format="PerExtrude",
            sequence=True,
            labels=True
        )
        self.assertIsNotNone(r, msg="graph response is not None")
        self.assertEqual(r.status_code, 200, msg="graph status code")
        graph_file = self.test_output_dir / f"{self.hex_design_json_file.stem}_0000.json"
        self.assertTrue(graph_file.exists(), msg="graph file exists")
        self.assertGreater(graph_file.stat().st_size, 0, msg="graph file size greater than 0")
        common_test.check_graph_format(self, graph_file, mode="PerExtrude", labels=True)

        graph_file = self.test_output_dir / f"{self.hex_design_json_file.stem}_0001.json"
        self.assertTrue(graph_file.exists(), msg="graph file exists")
        self.assertGreater(graph_file.stat().st_size, 0, msg="graph file size greater than 0")
        common_test.check_graph_format(self, graph_file, mode="PerExtrude", labels=True)

        graph_file = self.test_output_dir / f"{self.hex_design_json_file.stem}_0002.json"
        self.assertTrue(graph_file.exists(), msg="graph file exists")
        self.assertGreater(graph_file.stat().st_size, 0, msg="graph file size greater than 0")
        common_test.check_graph_format(self, graph_file, mode="PerExtrude", labels=True)

        # Clear
        r = self.client.clear()
        if self.clean_output:
            shutil.rmtree(self.test_output_dir)

    def test_graph_sequence_invalid_dir(self):
        # Save out the graphs
        r = self.client.graph(
            self.box_design_json_file,
            Path("xksksksl"),
            format="PerExtrude",
            sequence=True
        )
        self.assertIsNone(r, msg="graph response is None")

    def test_graph_empty(self):
        # Save out the graphs
        r = self.client.graph()
        self.assertIsNotNone(r, msg="graph response is not None")
        self.assertEqual(r.status_code, 200, msg="graph status code")
        response_json = r.json()
        common_test.check_empty_graph_format(self, response_json["data"])
        common_test.check_bounding_box(self, response_json["data"])

    def __test_box_mesh(self, mesh_file):
        # Check the mesh data
        local_mesh = mesh.Mesh.from_file(mesh_file)
        volume, cog, inertia = local_mesh.get_mass_properties()
        self.assertAlmostEqual(volume, 12.5)
        self.assertAlmostEqual(cog[0], 2.5)
        self.assertAlmostEqual(cog[1], 0.5)
        self.assertAlmostEqual(cog[2], 1.25)
        self.assertEqual(len(local_mesh.points), 12)

    @classmethod
    def tearDownClass(cls):
        if cls.clean_output:
            if cls.output_dir.exists():
                shutil.rmtree(cls.output_dir)


if __name__ == "__main__":
    unittest.main()
