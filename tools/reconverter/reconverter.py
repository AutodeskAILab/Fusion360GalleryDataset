import adsk.core
import adsk.fusion
import traceback
import json
import os
import sys
import time
from pathlib import Path
import importlib


# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

import exporter
importlib.reload(exporter)
import view_control
from logger import Logger
from sketch_extrude_importer import SketchExtrudeImporter


class Reconverter():
    """Reconstruction Converter
        Takes a reconstruction json file and converts it
        to different formats"""

    def __init__(self, json_file):
        self.json_file = json_file
        # Export data to this directory
        self.output_dir = json_file.parent / "output"
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True)
        # References to the Fusion design
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Counter for the number of design actions that have taken place
        self.inc_action_index = 0
        # Size of the images to export
        self.width = 1024
        self.height = 1024

    def reconstruct(self):
        """Reconstruct the design from the json file"""
        self.home_camera = self.app.activeViewport.camera
        self.home_camera.isSmoothTransition = False
        self.home_camera.isFitView = True
        importer = SketchExtrudeImporter(self.json_file)
        importer.reconstruct(self.inc_export)
        

    def inc_export(self, data):
        """Callback function called whenever a the design changes
            i.e. when a curve is added or an extrude
            This enables us to save out incremental data"""
        if "curve" in data:
            self.inc_export_curve(data)
        elif "sketch" in data:
            # No new geometry is added
            pass
        elif "extrude" in data:
            self.inc_export_extrude(data)
        self.inc_action_index += 1

    def inc_export_curve(self, data):
        """Save out incremental sketch data as reconstruction takes place"""
        png_file = f"{self.json_file.stem}_{self.inc_action_index:04}.png"
        png_file_path = self.output_dir / png_file
        # Show all geometry
        view_control.set_geometry_visible(True, True, True)
        exporter.export_png_from_sketch(
            png_file_path,
            data["sketch"],  # Reference to the sketch object that was updated
            reset_camera=True,  # Zoom to fit the sketch
            width=self.width,
            height=self.height
        )

    def inc_export_extrude(self, data):
        """Save out incremental extrude data as reconstruction takes place"""
        png_file = f"{self.json_file.stem}_{self.inc_action_index:04}.png"
        png_file_path = self.output_dir / png_file
        # Show bodies, sketches, and hide profiles
        view_control.set_geometry_visible(True, True, False)
        # Restore the home camera
        self.app.activeViewport.camera = self.home_camera
        # save view of bodies enabled, sketches turned off
        exporter.export_png_from_component(
            png_file_path,
            self.design.rootComponent,
            reset_camera=False,
            width=self.width,
            height=self.height
        )
        # Save out just obj file geometry at each extrude
        obj_file = f"{self.json_file.stem}_{self.inc_action_index:04}.obj"
        obj_file_path = self.output_dir / obj_file
        exporter.export_obj_from_component(obj_file_path, self.design.rootComponent)

    def export(self):
        """Export the final design in a different format"""
        # Meshes
        stl_file = self.output_dir / f"{self.json_file.stem}.stl"
        exporter.export_stl_from_component(stl_file, self.design.rootComponent)
        obj_file = self.output_dir / f"{self.json_file.stem}.obj"
        exporter.export_obj_from_component(obj_file, self.design.rootComponent)
        # B-Reps
        step_file = self.output_dir / f"{self.json_file.stem}.step"
        exporter.export_step_from_component(
            step_file, self.design.rootComponent)
        smt_file = self.output_dir / f"{self.json_file.stem}.smt"
        exporter.export_smt_from_component(smt_file, self.design.rootComponent)
        # Image
        png_file = self.output_dir / f"{self.json_file.stem}.png"
        # Hide sketches
        view_control.set_geometry_visible(True, False, False)
        exporter.export_png_from_component(
            png_file,
            self.design.rootComponent,
            reset_camera=False,
            width=1024,
            height=1024
        )


def run(context):
    try:
        app = adsk.core.Application.get()
        # Logger to print to the text commands window in Fusion
        logger = Logger()
        # Fusion requires an absolute path
        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "testdata"

        # Get all the files in the data folder
        json_files = [
            data_dir / "Couch.json",
            # data_dir / "Hexagon.json"
        ]

        json_count = len(json_files)
        for i, json_file in enumerate(json_files, start=1):
            try:
                logger.log(f"[{i}/{json_count}] Reconstructing {json_file}")
                reconverter = Reconverter(json_file)
                reconverter.reconstruct()
                # At this point the final design
                # should be available in Fusion
                reconverter.export()
            except Exception as ex:
                logger.log(f"Error reconstructing: {ex}")
            finally:
                # Close the document
                # Fusion automatically opens a new window
                # after the last one is closed
                app.activeDocument.close(False)

    except:
        print(traceback.format_exc())
