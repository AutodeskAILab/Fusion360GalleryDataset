import adsk.core
import adsk.fusion
import traceback
import json
import os
import sys
import time
from pathlib import Path
from importlib import reload


# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

import name
import serialize
from logger import Logger
from sketch_extrude_importer import SketchExtrudeImporter

reload(serialize)


class Regraph():
    """Reconstruction Graph
        Takes a reconstruction json file and converts it
        into a graph representing B-Rep topology"""

    def __init__(self, json_file):
        self.json_file = json_file
        # Export data to this directory
        self.output_dir = json_file.parent / "output"
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True)
        # References to the Fusion design
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Counter for the number of design actions that have taken place
        self.inc_action_index = 0

    def reconstruct(self):
        """Reconstruct the design from the json file"""
        importer = SketchExtrudeImporter(self.json_file)
        importer.reconstruct(self.inc_export)

    def inc_export(self, data):
        """Callback function called whenever a the design changes
            i.e. when a curve is added or an extrude
            This enables us to save out incremental data"""
        if "extrude" in data:
            self.inc_export_extrude(data)
        self.inc_action_index += 1

    def inc_export_extrude(self, data):
        """Save out a graph after each extrude as reconstruction takes place"""
        extrude_face_cache = self.get_extrude_face_cache(data["extrude"])
        graphs = self.get_json_graphs(extrude_face_cache)
        graph_json_string = json.dumps(graphs, indent=4)  
        # print(graph_json_string)

    def get_temp_ids_from_collection(self, collection):
        """From a collection, make a set of the tempids"""
        id_set = set()
        for entity in collection:
            if entity is not None:
                temp_id = entity.tempId
                id_set.add(temp_id)
        return id_set

    def get_extrude_face_cache(self, extrude):
        extrude_face_cache = {}
        extrude_face_cache["start_faces"] = self.get_temp_ids_from_collection(extrude.startFaces)
        extrude_face_cache["end_faces"] = self.get_temp_ids_from_collection(extrude.endFaces)
        extrude_face_cache["side_faces"] = self.get_temp_ids_from_collection(extrude.sideFaces)
        return extrude_face_cache

    def get_extrude_face_label(self, temp_id, extrude_face_cache):
        """Find where in the extrude this face came from
            Was it the start, end or side of an extrude"""
        if "start_faces" in extrude_face_cache:
            if temp_id in extrude_face_cache["start_faces"]:
                return "StartFace"
        if "end_faces" in extrude_face_cache:
            if temp_id in extrude_face_cache["end_faces"]:
                return "EndFace"
        if "side_faces" in extrude_face_cache:
            if temp_id in extrude_face_cache["side_faces"]:
                return "SideFace"
        return None

    def get_edge_cache(self, body):
        edge_cache = {}
        edge_cache["concave_edges"] = self.get_temp_ids_from_collection(body.concaveEdges)
        edge_cache["convex_edges"] = self.get_temp_ids_from_collection(body.convexEdges)
        print(edge_cache)
        return edge_cache

    def is_concave_edge(self, temp_id, edge_cache):
        return temp_id in edge_cache["concave_edges"]

    def is_convex_edge(self, temp_id, edge_cache):
        return temp_id in edge_cache["convex_edges"]

    def get_json_graphs(self, extrude_face_cache):
        graphs = []
        for body in self.design.rootComponent.bRepBodies:
            graph = {
                "directed": False,
                "multigraph": False,
                "graph": {},
                "nodes": [],
                "links": []
            }
            for face in body.faces:
                if face is not None:
                    face_data = {}
                    face_data["id"] = face.tempId
                    face_data["surface_type"] = serialize.surface_type(face.geometry)
                    face_data["surface_type_id"] = face.geometry.surfaceType
                    face_data["area"] = face.area
                    point_on_face = face.pointOnFace
                    evaluator = face.evaluator
                    normal_result, normal = evaluator.getNormalAtPoint(point_on_face)
                    assert normal_result
                    face_data["normal_x"] = normal.x
                    face_data["normal_y"] = normal.x
                    face_data["normal_z"] = normal.x
                    face_data["normal_length"] = normal.length
                    parameter_result, parameter_at_point = evaluator.getParameterAtPoint(point_on_face)
                    assert parameter_result
                    curvature_result, max_tangent, max_curvature, min_curvature = evaluator.getCurvature(parameter_at_point)
                    assert curvature_result
                    face_data["max_tangent_x"] = max_tangent.x
                    face_data["max_tangent_y"] = max_tangent.y
                    face_data["max_tangent_z"] = max_tangent.z
                    face_data["max_tangent_length"] = max_tangent.length
                    face_data["max_curvature"] = max_curvature
                    face_data["min_curvature"] = min_curvature
                    face_data["label"] = self.get_extrude_face_label(face.tempId, extrude_face_cache)
                    assert face_data["label"] is not None
                    graph["nodes"].append(face_data)

            edge_cache = self.get_edge_cache(body)
            for edge in body.edges:
                if edge is not None:
                    edge_data = {}
                    edge_data["id"] = edge.tempId
                    assert edge.faces.count == 2
                    edge_data["source"] = edge.faces[0].tempId
                    edge_data["target"] = edge.faces[1].tempId
                    edge_data["curve_type"] = serialize.curve_type(edge.geometry)
                    edge_data["curve_type_id"] = edge.geometry.curveType
                    edge_data["length"] = edge.length
                    edge_data["concave"] = self.is_concave_edge(edge.tempId, edge_cache)
                    edge_data["convex"] = self.is_convex_edge(edge.tempId, edge_cache)
                    point_on_edge = edge.pointOnEdge
                    evaluator = edge.evaluator
                    parameter_result, parameter_at_point = evaluator.getParameterAtPoint(point_on_edge)
                    assert parameter_result
                    curvature_result, direction, curvature = evaluator.getCurvature(parameter_at_point)
                    edge_data["direction_x"] = direction.x
                    edge_data["direction_y"] = direction.y
                    edge_data["direction_z"] = direction.z
                    edge_data["direction_length"] = direction.length
                    edge_data["curvature"] = curvature
                    graph["links"].append(edge_data)
            graphs.append(graph)
        return graphs


def run(context):
    try:
        app = adsk.core.Application.get()
        # Logger to print to the text commands window in Fusion
        logger = Logger()
        # Fusion requires an absolute path
        current_dir = Path(__file__).resolve().parent
        data_dir = current_dir.parent / "testdata"

        # Get all the files in the data folder
        # json_files = [f for f in data_dir.glob("**/*.json")]
        json_files = [data_dir / "Couch.json"]

        json_count = len(json_files)
        for i, json_file in enumerate(json_files, start=1):
            try:
                logger.log(f"[{i}/{json_count}] Processing {json_file}")
                reconverter = Regraph(json_file)
                reconverter.reconstruct()

            except Exception as ex:
                logger.log(f"Error reconstructing: {ex}")
                print(traceback.format_exc())
            finally:
                # Close the document
                # Fusion automatically opens a new window
                # after the last one is closed
                app.activeDocument.close(False)

    except:
        print(traceback.format_exc())
