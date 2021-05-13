#Author-
#Description-Creates f3d files based on metadata and smt files.

import os
import sys
from pathlib import Path
import adsk.core, adsk.fusion, adsk.cam, traceback

# Add the common folder to sys.path
COMMON_DIR = os.path.join(os.path.dirname(__file__), "..", "common")
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

# utilities comming from common dir
from assembly_importer import AssemblyImporter
import exporter

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        assembly_file = Path(os.path.join(os.path.dirname(__file__), "assembly_data/assembly.json")) 
        assembly_importer = AssemblyImporter(assembly_file)
        assembly_importer.reconstruct()
        reconstructed_file = Path(os.path.join(os.path.dirname(__file__), "reconstructed.f3d"))
        exporter.export_f3d(reconstructed_file)
        if ui:
            ui.messageBox('Construction Succeded:\n{}'.format(str(reconstructed_file)))
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
