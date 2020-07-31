"""

Gym++ Prototype

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


# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "common")
)
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)
import name
import sketch_extrude_importer
importlib.reload(sketch_extrude_importer)
from sketch_extrude_importer import SketchExtrudeImporter
from logger import Logger


class GymPlusPlus():

    def __init__(self, goal_json_file, logger):
        self.goal_json_file = goal_json_file
        self.logger = logger
        # References to the Fusion design
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.product = self.app.activeProduct
        self.timeline = self.app.activeProduct.timeline

    def setup_goal(self):
        """Setup the goal design"""
        importer = SketchExtrudeImporter(self.goal_json_file)
        # We will reconstruct the design in this goal occurrence
        self.goal = self.design.rootComponent.occurrences.addNewComponent(
            adsk.core.Matrix3D.create()
        )
        self.goal.component.name = "Goal"
        importer.reconstruct(target_component=self.goal.component)
        adsk.doEvents()
        # self.app.activeViewport.fit()
        time.sleep(1)
        # Hide the target for now
        for body in self.goal.component.bRepBodies:
            body.isLightBulbOn = False
        # Update the display
        adsk.doEvents()

    def reconstruct(self):
        """Reconstruct the goal design by selecting and extruding
            faces in the goal design"""
        # Create a reconstruction occurrence that we create geometry in
        # self.reconstruction = self.design.rootComponent.occurrences.addNewComponent(
        #     adsk.core.Matrix3D.create()
        # )
        # self.reconstruction.component.name = "Reconstruction"

        # TODO: We need to loop until the design matches the target
        #       This means somehow matching faces and edges
        for i in range(10):
            # We get some random faces
            start_face = self.get_random_planar_face()
            end_face = self.get_random_parallel_face(start_face)
            extrude = self.add_extrude(start_face, end_face)
            adsk.doEvents()
            time.sleep(0.2)

    def add_extrude(self, start_face, end_face):
        """Create an extrude from a start face to an end face"""
        print(f"Start face: {start_face.tempId} End face: {end_face.tempId}")
        # TODO: Try use profiles from the start face: Component.createBRepEdgeProfile
        extrudes = self.goal.component.features.extrudeFeatures
        # extrudes = self.reconstruction.component.features.extrudeFeatures
        extrude_input = extrudes.createInput(start_face, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extent = adsk.fusion.ToEntityExtentDefinition.create(end_face, False)
        extrude_input.setOneSideExtent(extent, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        extrude = extrudes.add(extrude_input)
        # for body in extrude.bodies:
        #     body.name = f"Reconstruction{body.name}"
        return extrude

    def get_random_planar_face(self):
        """Get a random planar face from the goal"""
        faces = []
        for body in self.goal.component.bRepBodies:
            for face in body.faces:
                if isinstance(face.geometry, adsk.core.Plane):
                    faces.append(face)
        return random.choice(faces)

    def get_random_parallel_face(self, face):
        """Get a random planar face parallel to the given face"""
        faces = []
        for body in self.goal.component.bRepBodies:
            for f in body.faces:
                if (f.tempId != face.tempId and
                   isinstance(f.geometry, adsk.core.Plane) and
                   f.geometry.isParallelToPlane(face.geometry) and
                   not f.geometry.isCoPlanarTo(face.geometry)):
                        faces.append(f)
        return random.choice(faces)


def run(context):
    try:
        app = adsk.core.Application.get()

        # Logger to print to the text commands window in Fusion
        logger = Logger()
        # Fusion requires an absolute path
        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent.parent / "testdata"
        # json_file = data_dir / "SingleSketchExtrude_RootComponent.json"
        json_file = data_dir / "Couch.json"
        
        gympp = GymPlusPlus(json_file, logger)
        gympp.setup_goal()
        gympp.reconstruct()

    except:
        print(traceback.format_exc())
