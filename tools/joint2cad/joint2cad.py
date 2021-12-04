"""

Construct a Fusion 360 CAD model from a joint set file
provided with the Fusion 360 Gallery Assembly Dataset joint data

"""


import os
import sys
from pathlib import Path
import adsk.core
import traceback

# Add the common folder to sys.path
COMMON_DIR = os.path.join(os.path.dirname(__file__), "..", "common")
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

from joint_importer import JointImporter
import exporter


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        # Turn on component color cycling first
        ui = app.userInterface
        ui.commandDefinitions.itemById("ViewColorCyclingOnCmd").execute()
        adsk.doEvents()

        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "testdata/joint_examples"
        joint_file = data_dir / "joint_set_00119.json"

        joint_importer = JointImporter(joint_file)
        joint_importer.reconstruct(joint_index=0)
        
        png_file = current_dir / f"{joint_file.stem}.png"
        exporter.export_png_from_component(png_file, app.activeProduct.rootComponent)
        
        f3d_file = current_dir / f"{joint_file.stem}.f3d"
        exporter.export_f3d(f3d_file)

        if ui:
            if f3d_file.exists():
                ui.messageBox(f"Exported to: {f3d_file}")
            else:
                ui.messageBox(f"Failed to export: {f3d_file}")

    except:
        if ui:
            ui.messageBox(f"Failed to export: {traceback.format_exc()}")

