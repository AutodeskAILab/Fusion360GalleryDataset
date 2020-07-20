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
import exporter
import serialize
from logger import Logger
from sketch_extrude_importer import SketchExtrudeImporter

reload(serialize)


class Regraph():
    """Reconstruction Graph
        Takes a reconstruction json file and converts it
        into a graph representing B-Rep topology"""

    def __init__(self, json_file, logger):
        self.json_file = json_file
        self.logger = logger
        # References to the Fusion design
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Cache of the extrude face label information
        self.extrude_face_cache = {}
        # Current extrude index
        self.current_extrude_index = 1

    def export(self, output_dir):
        """Reconstruct the design from the json file"""
        self.output_dir = output_dir
        importer = SketchExtrudeImporter(self.json_file)
        self.extrude_count = self.get_extrude_count(importer.data)
        importer.reconstruct(self.inc_export)

    def inc_export(self, data):
        """Callback function called whenever a the design changes
            i.e. when a curve is added or an extrude
            This enables us to save out incremental data"""
        if "extrude" in data:
            self.inc_export_extrude(data)

    def inc_export_extrude(self, data):
        """Save out a graph after each extrude as reconstruction takes place"""
        self.add_extrude_to_cache(data)
        graphs = self.get_json_graphs()
        for body_count, graph in enumerate(graphs):
            json_file = self.output_dir / f"{self.json_file.stem}_{self.current_extrude_index-1:04}_{body_count:04}.json"
            self.logger.log(f"Exporting {json_file}")
            exporter.export_json(json_file, graph)
        self.current_extrude_index += 1

    def get_extrude_count(self, data):
        """Get the number of extrudes in a design"""
        extrude_count = 0
        entities = data["entities"]
        for entity in entities.values():
            if entity["type"] == "ExtrudeFeature":
                extrude_count += 1
        return extrude_count

    def get_temp_ids_from_collection(self, collection):
        """From a collection, make a set of the tempids"""
        id_set = set()
        for entity in collection:
            if entity is not None:
                temp_id = entity.tempId
                id_set.add(temp_id)
        return id_set

    def add_extrude_faces_to_cache(self, extrude_faces, extrude_operation, extrude_face_location, extrude_taper):
        """Update the extrude face cache with the recently added faces"""
        operation = serialize.feature_operation(extrude_operation)
        operation_short = operation.replace("FeatureOperation", "")
        assert operation_short != "NewComponent"
        if operation_short == "NewBody" or operation_short == "Join":
            operation_short = "Extrude"

        for face in extrude_faces:
            face_uuid = name.set_uuid(face)
            assert face_uuid is not None
            assert face_uuid not in self.extrude_face_cache
            self.extrude_face_cache[face_uuid] = {
                # "timeline_label": self.current_extrude_index / self.extrude_count,
                "operation_label": f"{operation_short}{extrude_face_location}",
                "last_operation_label": True,
                "operation": operation,
                "extrude_taper": extrude_taper
            }

    def add_extrude_to_cache(self, extrude_data):
        """Add the data from the latest extrude to the cache"""
        # First toggle the previous extrude last_operation label
        for face_data in self.extrude_face_cache.values():
            face_data["last_operation_label"] = False
        extrude = extrude_data["extrude"]
        extrude_taper = self.is_extrude_tapered(extrude)
        self.add_extrude_faces_to_cache(extrude.startFaces, extrude.operation, "Start", extrude_taper)
        self.add_extrude_faces_to_cache(extrude.endFaces, extrude.operation, "End", extrude_taper)
        self.add_extrude_faces_to_cache(extrude.sideFaces, extrude.operation, "Side", extrude_taper)

    def get_edge_cache(self, body):
        name.set_uuids_for_collection(body.edges)
        edge_cache = {}
        edge_cache["concave_edges"] = self.get_temp_ids_from_collection(body.concaveEdges)
        edge_cache["convex_edges"] = self.get_temp_ids_from_collection(body.convexEdges)
        return edge_cache

    def is_concave_edge(self, temp_id, edge_cache):
        return temp_id in edge_cache["concave_edges"]

    def is_convex_edge(self, temp_id, edge_cache):
        return temp_id in edge_cache["convex_edges"]

    def are_faces_tangentially_connected(self, face1, face2):
        for tc_face in face1.tangentiallyConnectedFaces:
            if tc_face.tempId == face2.tempId:
                return True
        return False

    def is_extrude_tapered(self, extrude):
        if extrude.extentOne is not None:
            if isinstance(extrude.extentOne, adsk.fusion.DistanceExtentDefinition):
                if extrude.taperAngleOne is not None:
                    if extrude.taperAngleOne.value is not None and extrude.taperAngleOne.value != "":
                        if extrude.taperAngleOne.value != 0:
                            return True
        # Check the second extent if needed
        if (extrude.extentType ==
                adsk.fusion.FeatureExtentTypes.TwoSidesFeatureExtentType):
            if extrude.extentTwo is not None:
                if isinstance(extrude.extentTwo, adsk.fusion.DistanceExtentDefinition):
                    if extrude.taperAngleTwo is not None:
                        if extrude.taperAngleTwo.value is not None and extrude.taperAngleTwo.value != "":
                            if extrude.taperAngleTwo.value != 0:
                                return True
        return False

    def get_json_graphs(self):
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
                    face_uuid = name.get_uuid(face)
                    assert face_uuid is not None
                    face_labels = self.extrude_face_cache[face_uuid]
                    # Abort if we hit an intersect operation
                    if face_labels["operation"] == "IntersectFeatureOperation":
                        self.logger.log("Skipping: Extrude uses intersection")
                        return graphs
                    # Abort if we hit a taper
                    if face_labels["extrude_taper"]:
                        self.logger.log("Skipping: Extrude has taper")
                        return graphs
                    face_data["id"] = face.tempId
                    face_data["surface_type"] = serialize.surface_type(face.geometry)
                    # face_data["surface_type_id"] = face.geometry.surfaceType
                    face_data["area"] = face.area
                    point_on_face = face.pointOnFace
                    evaluator = face.evaluator
                    normal_result, normal = evaluator.getNormalAtPoint(point_on_face)
                    assert normal_result
                    face_data["normal_x"] = normal.x
                    face_data["normal_y"] = normal.y
                    face_data["normal_z"] = normal.z
                    # face_data["normal_length"] = normal.length
                    parameter_result, parameter_at_point = evaluator.getParameterAtPoint(point_on_face)
                    assert parameter_result
                    curvature_result, max_tangent, max_curvature, min_curvature = evaluator.getCurvature(parameter_at_point)
                    assert curvature_result
                    face_data["max_tangent_x"] = max_tangent.x
                    face_data["max_tangent_y"] = max_tangent.y
                    face_data["max_tangent_z"] = max_tangent.z
                    # face_data["max_tangent_length"] = max_tangent.length
                    face_data["max_curvature"] = max_curvature
                    face_data["min_curvature"] = min_curvature
                    # face_data["timeline_label"] = face_labels["timeline_label"]
                    face_data["operation_label"] = face_labels["operation_label"]
                    face_data["last_operation_label"] = face_labels["last_operation_label"]
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
                    # edge_data["curve_type_id"] = edge.geometry.curveType
                    edge_data["length"] = edge.length
                    # Create a feature for the edge convexity
                    is_concave = self.is_concave_edge(edge.tempId, edge_cache)
                    is_tc = self.are_faces_tangentially_connected(edge.faces[0], edge.faces[1])
                    convexity = "Convex"
                    # edge_data["convex"] = self.is_convex_edge(edge.tempId, edge_cache)
                    if is_concave:
                        convexity = "Concave"
                    elif is_tc:
                        convexity = "Smooth"
                    edge_data["convexity"] = convexity
                    point_on_edge = edge.pointOnEdge
                    evaluator = edge.evaluator
                    parameter_result, parameter_at_point = evaluator.getParameterAtPoint(point_on_edge)
                    assert parameter_result
                    curvature_result, direction, curvature = evaluator.getCurvature(parameter_at_point)
                    edge_data["direction_x"] = direction.x
                    edge_data["direction_y"] = direction.y
                    edge_data["direction_z"] = direction.z
                    # edge_data["direction_length"] = direction.length
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
        output_dir = current_dir / "output"
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        # Get all the files in the data folder
        json_files = [f for f in data_dir.glob("**/*.json")]
        json_files = [
            data_dir / "Couch.json",
            data_dir / "Z0HexagonCutJoin_RootComponent.json",
            data_dir / "Z0Convexity_12a12060_0000.json"
        ]

        json_count = len(json_files)
        for i, json_file in enumerate(json_files, start=1):
            try:
                logger.log(f"[{i}/{json_count}] Processing {json_file}")
                reconverter = Regraph(json_file, logger)
                reconverter.export(output_dir)

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
