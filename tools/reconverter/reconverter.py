import adsk.core
import adsk.fusion
import traceback
import json
import os
import sys
import time
from pathlib import Path
import importlib
import random


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

    def __init__(self, json_file, logger):
        self.json_file = json_file
        self.logger = logger
        # Export data to this directory
        self.output_dir = json_file.parent / "output"
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True)
        # References to the Fusion design
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.root_comp = self.design.rootComponent 
        self.home_camera = self.app.activeViewport.camera
        self.home_camera.isSmoothTransition = False
        self.home_camera.isFitView = True
        self.length = 0.5

    def reconstruct(self):
        """Reconstruct the design from the json file"""
        importer = SketchExtrudeImporter(self.json_file)
        sketches = self.root_comp.sketches
        sketch = sketches.addWithoutEdges(self.root_comp.xYConstructionPlane)
        sketch_data = importer.data
        curves_data = sketch_data["curves"]
        points_data = sketch_data["points"]
        sketch.isComputeDeferred = True
        for curve_uuid in curves_data:
            curve_data = curves_data[curve_uuid]
            importer.reconstruct_sketch_curve(sketch, curve_data, curve_uuid, points_data)
        sketch.isComputeDeferred = False
        constructed_profiles = sketch.profiles
        print(f"{len(constructed_profiles)} profiles")
        sketch_box = sketch.boundingBox
        dx = sketch_box.maxPoint.x - sketch_box.minPoint.x
        dy = sketch_box.maxPoint.y - sketch_box.minPoint.y
        max_box_length = dx
        if dy > max_box_length:
            max_box_length = dy
        self.create_extrude_feature(constructed_profiles, max_box_length)

    def export(self):
        """Export the final design in a different format"""
        # Meshes
        obj_file = self.output_dir / f"{self.json_file.stem}.obj"
        exporter.export_obj_from_component(obj_file, self.design.rootComponent)
        # B-Reps
        smt_file = self.output_dir / f"{self.json_file.stem}.smt"
        exporter.export_smt_from_component(smt_file, self.design.rootComponent)
        f3d_file = self.output_dir / f"{self.json_file.stem}.f3d"
        exporter.export_f3d(f3d_file)
        # Screenshot
        png_file = self.output_dir / f"{self.json_file.stem}.png"
        exporter.export_png_from_component(png_file, self.root_comp)


    def get_profile_properties(self, sketch_profiles):
        profile_properties = []
        for profile in sketch_profiles:
            props = profile.areaProperties(adsk.fusion.CalculationAccuracy.HighCalculationAccuracy)
            prop = {
                "profile": profile,
                "area": props.area,
                "centroid": props.centroid,
                "perimeter": props.perimeter
            }
            profile_properties.append(prop)
        # Sort so the first profile has the largest area
        profile_properties = sorted(profile_properties, key=lambda i: i["area"], reverse=True)
        return profile_properties

    def create_extrude_feature(self, sketch_profiles, max_box_length):
        extrudes = self.root_comp.features.extrudeFeatures
        profile_properties = self.get_profile_properties(sketch_profiles)

        # Extrude all the profiles as a base extrude
        all_profiles = adsk.core.ObjectCollection.create()
        for profile in profile_properties:
            all_profiles.add(profile["profile"])
        operation = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        distance = adsk.core.ValueInput.createByReal(max_box_length * self.length)
        base_extrude = extrudes.addSimple(all_profiles, distance, operation)

        # The largest profile
        largest_profile = profile_properties[0]["profile"]

        # Then extrude all of the smaller profiles next
        for profile in profile_properties[1:]:
            
            distance_float = max_box_length * self.length * random.uniform(0.15, 0.25)

            # Cut down if we are inside the larger profile
            if largest_profile.boundingBox.contains(profile["centroid"]) and len(base_extrude.endFaces) > 0:
                operation = adsk.fusion.FeatureOperations.CutFeatureOperation
                extrude_input = extrudes.createInput(profile["profile"], operation)
                distance = adsk.core.ValueInput.createByReal(-distance_float)
                extent_distance = adsk.fusion.DistanceExtentDefinition.create(distance)
                taper_angle = adsk.core.ValueInput.createByReal(0)
                extrude_input.setOneSideExtent(extent_distance, adsk.fusion.ExtentDirections.PositiveExtentDirection, taper_angle)

                # Use the first end face to extrude from
                entity = base_extrude.endFaces[0]
                offset_distance = adsk.core.ValueInput.createByReal(0)
                entity_start_def = adsk.fusion.FromEntityStartDefinition.create(entity, offset_distance)
                extrude_input.startExtent = entity_start_def
                extrudes.add(extrude_input)
            
            # Else just do a normal extrude and try to join
            else:
                operation = adsk.fusion.FeatureOperations.JoinFeatureOperation
                distance = adsk.core.ValueInput.createByReal(distance_float)
                extrudes.addSimple(profile["profile"], distance, operation)            


def run(context):
    try:
        app = adsk.core.Application.get()
        # Logger to print to the text commands window in Fusion
        logger = Logger()
        # Fusion requires an absolute path
        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "testdata/sketchdl"

        # Get all the files in the data folder
        # json_files = [
        #     data_dir / "wire-00002.json",
        #     # data_dir / "Hexagon.json"
        # ]
        json_files = [f for f in data_dir.glob("*.json")]

        json_count = len(json_files)
        for i, json_file in enumerate(json_files, start=1):
            try:
                logger.log(f"[{i}/{json_count}] Reconstructing {json_file}")
                reconverter = Reconverter(json_file, logger)
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
