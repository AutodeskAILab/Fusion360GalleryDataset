"""

Face Reconstructor
Reconstruct via face extrusion to match a target design

"""

import adsk.core
import adsk.fusion
from importlib

import name
import deserialize


class FaceReconstructor():

    def __init__(self, target_design, reconstruction_design):
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.target_design = target_design
        self.reconstruction_design = reconstruction_design
        self.target_uuid_to_face_map = {}
        self.use_temp_id = True

    def setup(self):
        """Setup for reconstruction"""
        # Create a reconstruction component that we create geometry in
        self.create_component()
        # Populate the cache with a map from uuids to face indices
        self.target_uuid_to_face_map = self.get_target_uuid_to_face_map()

    def reset(self):
        """Reset the reconstructor"""
        self.remove()
        self.create_component()

    def remove(self):
        """Remove the reconstructed component"""
        self.reconstruction.deleteMe()

    def reconstruct(self, graph_data):
        """Reconstruct from the sequence of faces"""
        self.sequence = graph_data["sequences"][0]
        self.setup()
        for seq in self.sequence["sequence"]:
            self.add_extrude_from_uuid(
                seq["start_face"],
                seq["end_face"],
                seq["operation"]
            )

    def get_face_from_uuid(self, face_uuid):
        """Get a face from an index in the sequence"""
        if face_uuid not in self.target_uuid_to_face_map:
            return None
        uuid_data = self.target_uuid_to_face_map[face_uuid]
        # body_index = indices["body_index"]
        # face_index = indices["face_index"]
        # body = self.target_design.bRepBodies[body_index]
        # face = body.faces[face_index]
        return uuid_data["face"]

    def get_target_uuid_to_face_map(self):
        """As we have to find faces multiple times we first
            make a map between uuids and face indices"""
        target_uuid_to_face_map = {}
        for body_index, body in enumerate(self.target_design.bRepBodies):
            for face_index, face in enumerate(body.faces):
                face_uuid = face.tempId
                assert face_uuid is not None
                target_uuid_to_face_map[face_uuid] = {
                    "body_index": body_index,
                    "face_index": face_index,
                    "body": body,
                    "face": face
                }
        return target_uuid_to_face_map

    def add_extrude_from_uuid(self, start_face_uuid, end_face_uuid, operation):
        """Create an extrude from a start face uuid to an end face uuid"""
        start_face = self.get_face_from_uuid(start_face_uuid)
        end_face = self.get_face_from_uuid(end_face_uuid)
        operation = deserialize.feature_operations(operation)
        return self.add_extrude(start_face, end_face, operation)

    def add_extrude(self, start_face, end_face, operation):
        """Create an extrude from a start face to an end face"""
        # If there are no bodies to cut or intersect, do nothing
        if ((operation == adsk.fusion.FeatureOperations.CutFeatureOperation or
           operation == adsk.fusion.FeatureOperations.IntersectFeatureOperation) and
           self.reconstruction.bRepBodies.count == 0):
            return None
        # We generate the extrude bodies in the reconstruction component
        extrudes = self.reconstruction.component.features.extrudeFeatures
        extrude_input = extrudes.createInput(start_face, operation)
        extent = adsk.fusion.ToEntityExtentDefinition.create(end_face, False)
        extrude_input.setOneSideExtent(extent, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        extrude_input.creationOccurrence = self.reconstruction
        tools = []
        for body in self.reconstruction.bRepBodies:
            tools.append(body)
        extrude_input.participantBodies = tools
        extrude = extrudes.add(extrude_input)
        return extrude
