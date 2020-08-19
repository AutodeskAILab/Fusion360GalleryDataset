"""

Sketch++
Draw sketches on a given plane, at a location, with scale

"""

import adsk.core
import adsk.fusion
import traceback
import os
import sys
import importlib
from pathlib import Path
import json
from collections import OrderedDict
from importlib import reload


# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "common")
)
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

import sketch_extrude_importer
reload(sketch_extrude_importer)
from logger import Logger
from sketch_extrude_importer import SketchExtrudeImporter


def get_scale_translation_matrix(scale=None, translation=None):
    """Get a transformation matrix that scales and translates"""
    transform = adsk.core.Matrix3D.create()
    if scale is not None:
        # We don't have a Matrix3D.scale() function
        # so we set this manually
        transform.setWithArray([
            scale.x, 0, 0, 0,
            0, scale.y, 0, 0,
            0, 0, scale.z, 0,
            0, 0, 0, 1
        ])
    if translation is not None:
        # We do have a shortcut to set the translation
        transform.translation = translation
    return transform


def run(context):
    try:
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        product = app.activeProduct
        timeline = app.activeProduct.timeline

        # Logger to print to the text commands window in Fusion
        logger = Logger()
        # Fusion requires an absolute path
        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "testdata"
        # Load the json ourselves
        json_file = data_dir / "Z0HexagonCutJoin_RootComponent.json"
        with open(json_file, encoding="utf8") as f:
            json_data = json.load(f, object_pairs_hook=OrderedDict)
        importer = SketchExtrudeImporter(json_data)

        # Pick the first sketch
        sketch_uuid = json_data["timeline"][0]["entity"]
        # We create and pass in a transform matrix that we can manipulate
        # to change the location and scale of the sketch
        # Scale the sketch
        scale = adsk.core.Vector3D.create(2, 2, 2)
        # Move the sketch
        translation = adsk.core.Vector3D.create(2, 2, 0)
        transform = get_scale_translation_matrix(scale, translation)

        # The sketch plane to draw on, this can also be a B-RepFace
        sketch_plane = design.rootComponent.xZConstructionPlane
        # sketch_plane = design.rootComponent.xYConstructionPlane
        # We pass in a couple optional arguments when we reconstruct
        # to set the sketch plane and the transform
        importer.reconstruct_sketch(
            sketch_uuid,
            sketch_plane=sketch_plane,
            transform=transform
        )

    except:
        print(traceback.format_exc())
