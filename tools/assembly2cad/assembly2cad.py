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

from assembly_importer import AssemblyImporter
import exporter


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "testdata/assembly_examples"
        assembly_file = data_dir / "assembly.json"

        assembly_importer = AssemblyImporter(assembly_file)
        assembly_importer.reconstruct()
        output_file = current_dir / "output.f3d"
        exporter.export_f3d(output_file)
        if ui:
            if output_file.exists():
                ui.messageBox(f"Exported to: {output_file}")
            else:
                ui.messageBox(f"Failed to export: {output_file}")
    except:
        if ui:
            ui.messageBox(f"Failed to export: {traceback.format_exc()}")
