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
from logger import Logger


class GymPlusPlus():

    def __init__(self, goal_smt_file, logger):
        self.goal_smt_file = goal_smt_file
        self.logger = logger
        # References to the Fusion design
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.product = self.app.activeProduct
        self.timeline = self.app.activeProduct.timeline

    def setup_goal(self):
        """Setup the goal design"""
        # Import the B-Rep without any construction information
        smt_options = self.app.importManager.createSMTImportOptions(str(self.goal_smt_file.resolve()))
        smt_options.isViewFit = False
        imported_designs = self.app.importManager.importToTarget2(smt_options, self.design.rootComponent)
        # We do a little bit of clean up here so the goal design
        # is in the root of the document
        for occ in imported_designs:
            for body in occ.bRepBodies:
                # Rename it as the goal so we don't get confused
                body.name = f"Goal-{body.name}"
                body.moveToComponent(self.design.rootComponent)
            occ.deleteMe()
        # Update the display
        adsk.doEvents()

    def reconstruct(self):
        """Reconstruct the goal design by selecting and extruding
            faces in the goal design"""
        # Create a reconstruction component that we create geometry in
        self.reconstruction = self.design.rootComponent.occurrences.addNewComponent(
            adsk.core.Matrix3D.create()
        )
        self.reconstruction.component.name = "Reconstruction"

        # TODO: We need to loop until the design matches the target
        #       This means somehow matching faces and edges
        for i in range(4):
            # We get some random faces
            start_face = self.get_random_planar_face()
            # TODO: Here we need to generate a graph that has the start face represented in it
            end_face = self.get_random_parallel_face(start_face)
            extrude = self.add_extrude(start_face, end_face)
            # TODO: Here we need to generate a graph that has the latest extrude data in
            adsk.doEvents()
            # time.sleep(0.2)

    def add_extrude(self, start_face, end_face):
        """Create an extrude from a start face to an end face"""
        self.logger.log(f"Extruding from start face: {start_face.tempId} to end face: {end_face.tempId}")
        # We generate the extrude bodies in the reconstruction component
        extrudes = self.reconstruction.component.features.extrudeFeatures
        operation = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        extrude_input = extrudes.createInput(start_face, operation)
        extent = adsk.fusion.ToEntityExtentDefinition.create(end_face, False)
        extrude_input.setOneSideExtent(extent, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        extrude = extrudes.add(extrude_input)
        # The Fusion API  doesn't seem to be able to do join extrudes
        # that don't join to the goal body
        # so we make the bodies separate and then join them after the fact
        if self.reconstruction.component.bRepBodies.count > 1:
            combines = self.reconstruction.component.features.combineFeatures
            first_body = self.reconstruction.component.bRepBodies[0]
            tools = adsk.core.ObjectCollection.create()
            for body in extrude.bodies:
                tools.add(body)
            combine_input = combines.createInput(first_body, tools)
            combine = combines.add(combine_input)
        return extrude

    def get_random_planar_face(self):
        """Get a random planar face from the goal"""
        faces = []
        # We look for a face in the root bodies, which contains the goal
        for body in self.design.rootComponent.bRepBodies:
            for face in body.faces:
                if isinstance(face.geometry, adsk.core.Plane):
                    faces.append(face)
        return random.choice(faces)

    def get_random_parallel_face(self, face):
        """Get a random planar face parallel to the given face"""
        faces = []
        # We look for a face in the root bodies, which contains the goal
        for body in self.design.rootComponent.bRepBodies:
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
        smt_file = data_dir / "Couch.smt"
        gympp = GymPlusPlus(smt_file, logger)
        gympp.setup_goal()
        gympp.reconstruct()

    except:
        print(traceback.format_exc())
