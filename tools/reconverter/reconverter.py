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
        # References to the Fusion design
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.timeline = self.design.timeline

    def reconstruct(self):
        """Reconstruct the design from the json file"""
        self.home_camera = self.app.activeViewport.camera
        self.home_camera.isSmoothTransition = False
        self.home_camera.isFitView = True
        importer = SketchExtrudeImporter(self.json_file)
        importer.reconstruct()

    def analyze(self):
        """Find the labels in the design"""
        # Traverse the timeline and process extrudes
        extrude_index = 0
        prev_bodies = []
        # Used for creating temporary copies of the brep
        temp_brep_mgr = adsk.fusion.TemporaryBRepManager.get()
        for timeline_object in self.timeline:
            if isinstance(timeline_object.entity, adsk.fusion.ExtrudeFeature):
                # Move the timeline to after this extrude 
                timeline_object.rollTo(False)
                extrude = timeline_object.entity
                
                extrude_index += 1

    def find_labels(self, extrude, prev_bodies):
        """Find the labels"""


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
            # finally:
            #     # If we want to process multiple files...
            #     # Close the document
            #     # Fusion automatically opens a new window
            #     # after the last one is closed
            #     app.activeDocument.close(False)

    except:
        print(traceback.format_exc())
