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
import name
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

    def export_labels(self):
        """Export the labels in the design"""
        # First add a uuid to all bodies
        # We keep a map to speed things up a bit
        face_map = {}
        body_map = {}
        for body in self.design.rootComponent.bRepBodies:
            body_uuid = name.set_uuid(body)
            body_map[body.entityToken] = body_uuid
            for face in body.faces:
                uuid = name.set_uuid(face)
                face_map[face.entityToken] = uuid
        extrude_labels = []
        # Traverse the timeline and find the labels
        for timeline_object in self.timeline:
            if isinstance(timeline_object.entity, adsk.fusion.ExtrudeFeature):
                # We purposefully don't roll back the timeline
                # so we keep the geometry at the end of the timeline
                # in the final state of the design
                # timeline_object.rollTo(False)
                extrude = timeline_object.entity
                extrude_data = {
                    "name": extrude.name,
                    "index": timeline_object.index
                }
                extrude_data["extrude_bodies"] = self.get_uuid_collection(body_map, extrude.bodies)
                extrude_data["extrude_faces"] = self.get_uuid_collection(face_map, extrude.faces)
                extrude_data["extrude_start_faces"] = self.get_uuid_collection(face_map, extrude.startFaces)
                extrude_data["extrude_side_faces"] = self.get_uuid_collection(face_map, extrude.sideFaces)
                extrude_data["extrude_end_faces"] = self.get_uuid_collection(face_map, extrude.endFaces)
                extrude_labels.append(extrude_data)
        
        labels_json_file = self.json_file.parent / f"{self.json_file.stem}_labels.json"
        labels_obj_file = self.json_file.parent / f"{self.json_file.stem}_labels.obj"
        exporter.export_json(labels_json_file, extrude_labels)
        self.export_obj_with_face_uuid_labels(labels_obj_file, self.design.rootComponent, face_map)

    def get_uuid_collection(self, entity_map, entities):
        """Get a list of uuids from a collection of entities"""
        uuids = []
        for entity in entities:
            uuid = entity_map[entity.entityToken]
            assert uuid is not None
            uuids.append(uuid)
        return uuids   
    
    def export_obj_with_face_uuid_labels(self, file, component, face_map):
        """Export a component as an OBJ
            with labels on the faces created by the feature"""
        try:
            face_meshes = []
            face_labels = []
            face_indices = []
            face_uuids = []
            face_index = 0
            for body in component.bRepBodies:
                for face in body.faces:
                    face_indices.append(face_index)
                    face_index += 1
                    face_uuid = face_map[face.entityToken]
                    assert face_uuid is not None
                    face_uuids.append(face_uuid)
                    mesher = face.meshManager.createMeshCalculator()
                    mesher.setQuality(
                        adsk.fusion.TriangleMeshQualityOptions.NormalQualityTriangleMesh
                    )
                    mesh = mesher.calculate()
                    face_meshes.append(mesh)

            triangle_count = 0
            vert_count = 0
            for mesh in face_meshes:
                triangle_count += mesh.triangleCount
                vert_count += mesh.nodeCount

            # Write the mesh to OBJ
            with open(file, "w") as obj_fh:
                obj_fh.write("# WaveFront *.obj file\n")
                obj_fh.write(f"# Vertices: {vert_count}\n")
                obj_fh.write(f"# Triangles : {triangle_count}\n\n")

                for mesh in face_meshes:
                    verts = mesh.nodeCoordinates
                    for pt in verts:
                        obj_fh.write(f"v {pt.x} {pt.y} {pt.z}\n")
                for mesh in face_meshes:
                    for vec in mesh.normalVectors:
                        obj_fh.write(f"vn {vec.x} {vec.y} {vec.z}\n")

                index_offset = 0
                for mesh_index, mesh in enumerate(face_meshes):
                    face_index = face_indices[mesh_index]
                    # We create groups of faces based on the face index
                    # and provide another group to indicate if the face is
                    # new data added from the feature or old existing data
                    obj_fh.write(
                        f"g {face_uuids[mesh_index]}\n"
                    )
                    mesh_tri_count = mesh.triangleCount
                    indices = mesh.nodeIndices
                    for t in range(mesh_tri_count):
                        i0 = indices[t * 3] + 1 + index_offset
                        i1 = indices[t * 3 + 1] + 1 + index_offset
                        i2 = indices[t * 3 + 2] + 1 + index_offset
                        obj_fh.write(f"f {i0}//{i0} {i1}//{i1} {i2}//{i2}\n")
                    index_offset += mesh.nodeCount

                obj_fh.write(f"\n# End of file")
            return True

        except Exception as ex:
            return False


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
            data_dir / "51022_47816098_0003.json",
            # data_dir / "Hexagon.json"
        ]

        json_count = len(json_files)
        for i, json_file in enumerate(json_files, start=1):
            # try:
            logger.log(f"[{i}/{json_count}] Reconstructing {json_file}")
            reconverter = Reconverter(json_file)
            reconverter.reconstruct()
            # At this point the final design
            # should be available in Fusion
            reconverter.export_labels()
            # except Exception as ex:
            #     logger.log(f"Error reconstructing: {ex}")
            # finally:
            #     # If we want to process multiple files...
            #     # Close the document
            #     # Fusion automatically opens a new window
            #     # after the last one is closed
            #     app.activeDocument.close(False)

    except:
        print(traceback.format_exc())
