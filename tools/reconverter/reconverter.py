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
import sketch_extrude_importer
importlib.reload(sketch_extrude_importer)
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
        self.importer = SketchExtrudeImporter(self.json_file)
        self.importer.reconstruct(self.inc_export)

    def inc_export(self, data):
        """Callback function called whenever a the design changes
            i.e. when a curve is added or an extrude
            This enables us to save out incremental data"""
        if "extrude" in data:
            self.inc_export_extrude(data)
        self.inc_action_index += 1

    def inc_export_extrude(self, data):
        """Save out incremental extrude data as reconstruction takes place"""
        extrude = data["extrude"]
        extrude_index = data["extrude_index"]
        extrude_data = data["extrude_data"]
        extrude_uuid = data["extrude_id"]
        sketch_profiles = data["sketch_profiles"]

        # Second extrude
        # Create a new body this time
        extrude_data["operation"] = "NewBodyFeatureOperation"
        extrude = self.importer.reconstruct_extrude_feature(
            extrude_data,
            extrude_uuid,
            extrude_index,
            sketch_profiles,
            second_extrude=True
        )

        # TODO: Support export of multiple bodies
        step_file = f"{self.json_file.stem}_{extrude_index:04}.step"
        step_file_path = self.output_dir / step_file
        exporter.export_step_from_body(step_file_path, extrude.bodies[0])

        # Rollback the timeline to before the last extrude
        extrude.timelineObject.rollTo(True)
        # Delete everything after that
        self.design.timeline.deleteAllAfterMarker()


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

            except Exception as ex:
                logger.log(f"Error reconstructing: {ex}, {ex.args}")
            finally:
                # Close the document
                # Fusion automatically opens a new window
                # after the last one is closed
                app.activeDocument.close(False)

    except:
        print(traceback.format_exc())
