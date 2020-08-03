"""

Reconstruct Sketch Test

"""

import adsk.core
import adsk.fusion
import traceback
import os
import sys
import importlib
from pathlib import Path
import random
import time
from importlib import reload


# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "common")
)
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)
import name
import sketch_extrude_importer
reload(sketch_extrude_importer)
from sketch_extrude_importer import SketchExtrudeImporter


def run(context):
    try:
        app = adsk.core.Application.get()

        # Fusion requires an absolute path
        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "testdata"
        json_file = data_dir / "Couch.json"
        importer = SketchExtrudeImporter(json_file)
        importer.reconstruct_sketch("ed84457a-965f-11ea-911a-acde48001122")

    except:
        print(traceback.format_exc())
