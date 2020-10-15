"""

Reconstruction Graph
Generates a graph data structure using a face adjacency graph of B-Rep topology

"""

import adsk.core
import adsk.fusion
import traceback
import json
import os
import sys
import time
import copy
from pathlib import Path
import importlib
import unittest
import math

import name
import geometry
import exporter
import serialize
import exceptions
import face_reconstructor
importlib.reload(face_reconstructor)
from face_reconstructor import FaceReconstructor
from logger import Logger


class Regraph():
    """Reconstruction Graph generation"""

    def __init__(self, reconstruction, logger=None, mode="PerExtrude", use_temp_id=False, include_labels=True):
        # References to the Fusion design
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.product = self.app.activeProduct
        self.timeline = self.app.activeProduct.timeline

        self.reconstruction = reconstruction
        self.logger = logger
        if self.logger is None:
            self.logger = Logger()

        # The mode we want
        self.mode = mode
        # Global flag defining which id's to get for regraph
        self.use_temp_id = use_temp_id
        # Include labels when we output the graph
        self.include_labels = include_labels

        # Data structure to return
        self.data = {
            "graphs": [],
            "sequences": [],
            "status": []
        }
        # Cache of the extrude face label information
        self.face_cache = {}
        # Cache of the edge information
        self.edge_cache = {}
        # The sequence of nodes and edges that become explained
        self.sequence = []
        # The cache of the faces and edges seen so far
        self.sequence_cache = {
            "faces": set(),
            "edges": set()
        }
        # Current extrude index
        self.current_extrude_index = 0
        # Current overall action index
        self.current_action_index = 0

    # -------------------------------------------------------------------------
    # GENERATE
    # -------------------------------------------------------------------------

    def generate(self):
        """Generate graphs from the design in the timeline"""
        assert self.reconstruction.bRepBodies.count > 0
        # We (likely) need to first populate the face cache first
        self.add_faces_to_cache()
        # Check that all faces have uuids
        # Iterate over the occurrence bodies, not the component
        for body in self.reconstruction.bRepBodies:
            for face in body.faces:
                face_uuid = self.get_regraph_uuid(face)
                assert face_uuid is not None
        prev_extrude_index = 0
        skip_reason = None
        # Next move the marker to after each extrude and export
        for timeline_object in self.timeline:
            if isinstance(timeline_object.entity, adsk.fusion.ExtrudeFeature):
                self.timeline.markerPosition = timeline_object.index + 1
                extrude = timeline_object.entity
                supported, unsupported_reason = self.is_extrude_supported(extrude)
                if not supported:
                    self.timeline.markerPosition = prev_extrude_index
                    skip_reason = unsupported_reason
                    break
                # Populate the cache again
                self.add_extrude_to_cache(extrude, timeline_object.index)
                self.add_edges_to_cache()
                self.generate_from_extrude(extrude)
                prev_extrude_index = self.timeline.markerPosition
        if skip_reason is None:
            self.generate_last()
        else:
            self.data["status"].append(skip_reason)
        return self.data

    def generate_from_extrude(self, extrude):
        """Generate a graph after each extrude as reconstruction takes place"""
        # If we are exporting per face
        if self.mode == "PerFace":
            bodies = self.add_extrude_to_sequence(extrude)
            if len(bodies) == 1:
                graph = self.get_graph()
                self.data["graphs"].append(graph)
                self.data["status"].append("Success")
            else:
                body_ids = [b.revisionId for b in bodies]
                body_ids_set = set(body_ids)
                # Check if we have multiple faces extruding the same body
                if len(body_ids) != len(body_ids_set):
                    raise exceptions.UnsupportedException(
                            "Multiple face extrude to single body")
                for body in bodies:
                    if len(self.data["graphs"]) > 0:
                        prev_graph = copy.deepcopy(self.data["graphs"][-1])
                    else:
                        prev_graph = None
                    graph = self.get_graph_delta(prev_graph, body)
                    self.data["graphs"].append(graph)
                    self.data["status"].append("Success")
        else:
            graph = self.get_graph()
            self.data["graphs"].append(graph)
            self.data["status"].append("Success")
        self.current_extrude_index += 1

    def generate_last(self):
        """Export after the full reconstruction"""
        # The last extrude
        if self.mode == "PerFace":
            # Only export if we had some valid extrudes
            if self.current_extrude_index > 0:
                bbox = geometry.get_bounding_box(self.reconstruction)
                bbox_data = serialize.bounding_box3d(bbox)
                seq_data = {
                    "sequence": self.sequence,
                    "properties": {
                        "bounding_box": bbox_data,
                        "extrude_count": self.current_extrude_index,
                        "body_count": self.reconstruction.bRepBodies.count
                    }
                }
                if self.timeline is not None:
                    seq_data["properties"]["timeline_count"] = self.timeline.count
                self.data["sequences"].append(seq_data)

    def generate_from_bodies(self, bodies):
        """Generate a single graph from a collection of bodies"""
        if not self.use_temp_id:
            self.set_face_uuids(bodies)
        if self.include_labels:
            # We need to pull gt labels from the timeline
            self.add_faces_to_cache()
        self.add_edges_to_cache(bodies)
        graph = self.get_graph_from_bodies(bodies)
        return graph

    # -------------------------------------------------------------------------
    # DATA CACHING
    # -------------------------------------------------------------------------

    def add_faces_to_cache(self):
        """Iterate over the timeline and populate the face cache"""
        for timeline_object in self.timeline:
            if isinstance(timeline_object.entity, adsk.fusion.ExtrudeFeature):
                self.add_extrude_to_cache(timeline_object.entity, timeline_object.index)

    def add_extrude_to_cache(self, extrude, timeline_index):
        """Add the data from the latest extrude to the cache"""
        operation = serialize.feature_operation(extrude.operation)
        self.add_extrude_faces_to_cache(extrude.startFaces, operation, "StartFace", timeline_index)
        self.add_extrude_faces_to_cache(extrude.endFaces, operation, "EndFace", timeline_index)
        self.add_extrude_faces_to_cache(extrude.sideFaces, operation, "SideFace", timeline_index)

    def add_extrude_faces_to_cache(self, extrude_faces, operation, location_in_feature, timeline_index):
        """Update the extrude face cache with the recently added faces"""
        for face in extrude_faces:
            # We want to set a uuid on the face in the assembly context
            # of the reconstruction, rather than on the component face
            proxy_face = face.createForAssemblyContext(self.reconstruction)
            face_uuid = self.set_regraph_uuid(proxy_face)
            assert face_uuid is not None
            # We will have split faces with the same uuid
            # So we need to update them
            # assert face_uuid not in self.face_cache
            self.face_cache[face_uuid] = {
                "operation_label": operation,
                "timeline_index_label": timeline_index,
                "location_in_feature_label": location_in_feature
            }

    def add_edges_to_cache(self, bodies=None):
        """Update the edge cache with the latest extrude"""
        if bodies is None:
            # We want the occurrence bodies, not the component
            bodies = self.reconstruction.bRepBodies
        concave_edge_cache = set()
        for body in bodies:
            temp_ids = name.get_temp_ids_from_collection(body.concaveEdges)
            concave_edge_cache.update(temp_ids)
        for body in bodies:
            for face in body.faces:
                for edge in face.edges:
                    edge_faces = edge.faces
                    assert edge_faces.count == 2
                    edge_uuid = self.set_regraph_uuid(edge)
                    edge_temp_id = edge.tempId
                    edge_concave = edge_temp_id in concave_edge_cache
                    assert edge_uuid is not None
                    self.edge_cache[edge_uuid] = {
                        "temp_id": edge_temp_id,
                        "source": self.get_regraph_uuid(edge_faces[0]),
                        "target": self.get_regraph_uuid(edge_faces[1])
                    }
                    if self.mode == "PerExtrude":
                        self.edge_cache[edge_uuid]["convexity"] = self.get_edge_convexity(edge, edge_concave)
                    # TODO: Handle cases where an edge has more than 2 faces
                    # We have to connect each face to one another
                    # but currently we cache 1 graph edge for each brep edge
                    # we need to have a way to store multiple graph edges per brep edge...
                    # for edge_face_index, edge_face in enumerate(edge.faces):
                    #     for index in range(edge_face_index + 1, edge.faces.count):
                    #         print(edge_face_index, index)
                    #         self.edge_cache[edge_uuid] = {
                    #             "temp_id": edge.tempId,
                    #             "convexity": self.get_edge_convexity(edge, edge_concave),
                    #             "source": self.get_regraph_uuid(edge.faces[edge_face_index]),
                    #             "target": self.get_regraph_uuid(edge.faces[index])
                    #         }

    def add_extrude_to_sequence(self, extrude):
        """Add the extrude operation to the sequence"""
        # Keep track of which bodies from each extrude
        bodies = []
        # Multiple start or end faces in a single extrude
        if extrude.startFaces.count > 1 or extrude.endFaces.count > 1:
            start_faces = extrude.startFaces
            start_end_flipped = False
            if extrude.endFaces.count > extrude.startFaces.count:
                start_faces = extrude.endFaces
                start_end_flipped = True
            for start_face in start_faces:
                body = self.add_extrude_faces_to_sequence(extrude, start_face, start_end_flipped)
                bodies.append(body)
        # Single extrude
        else:
            body = self.add_extrude_faces_to_sequence(extrude)
            bodies.append(body)
        return bodies

    def add_extrude_faces_to_sequence(self, extrude, start_face=None, start_end_flipped=None):
        """Add the extrude operation to the sequence"""
        # If we don't already have a start face
        if start_face is None or start_end_flipped is None:
            start_face, start_end_flipped = self.get_extrude_start_face(extrude)
        assert start_face is not None
        # Get the face uuid in the context of the occurrence, not the component
        proxy_start_face = start_face.createForAssemblyContext(self.reconstruction)
        start_face_uuid = self.get_regraph_uuid(proxy_start_face)
        assert start_face_uuid is not None

        # End face
        end_face = self.get_extrude_end_face(extrude, start_end_flipped, start_face.body)
        assert end_face is not None
        # Get the face uuid in the context of the occurrence, not the component
        proxy_end_face = end_face.createForAssemblyContext(self.reconstruction)
        end_face_uuid = self.get_regraph_uuid(proxy_end_face)
        assert end_face_uuid is not None

        operation = serialize.feature_operation(extrude.operation)
        # Add the extrude to the sequence
        extrude_to_sequence_entry = {
            "start_face": start_face_uuid,
            "end_face": end_face_uuid,
            "operation": operation
        }
        self.sequence.append(extrude_to_sequence_entry)
        return start_face.body

    def get_extrude_start_face(self, extrude):
        """Get the start face from an extrude, along with a flag to
            indicate if the start and end face are flipped"""
        # Look for a start or end face with a single face
        start_end_flipped = False
        start_end_face_set = False
        if (extrude.startFaces.count == 1 and
           extrude.endFaces.count == 1):
            # If we have both a start face and an end face
            # we can't tell which face will remain intact so
            # we skip to the end of the design
            # and check it still exists
            prev_timeline_index = self.timeline.markerPosition
            self.timeline.moveToEnd()
            # If either start or end is absent
            # assign the other if we can
            if extrude.startFaces.count == 0:
                if extrude.endFaces.count > 0:
                    start_face = extrude.endFaces[0]
                    start_end_flipped = True
                    start_end_face_set = True
                self.timeline.markerPosition = prev_timeline_index
            elif extrude.endFaces.count == 0:
                if extrude.startFaces.count > 0:
                    start_face = extrude.startFaces[0]
                    start_end_flipped = False
                    start_end_face_set = True
                self.timeline.markerPosition = prev_timeline_index
            # If we have both start and end then pick the larger one
            # which has not been trimmed/split
            if (extrude.startFaces.count > 0 and
                extrude.endFaces.count > 0):
                    sf = extrude.startFaces[0]
                    ef = extrude.endFaces[0]
                    sf_area = sf.area
                    ef_area = ef.area
                    self.timeline.markerPosition = prev_timeline_index
                    # If both start and end are the same size
                    # then we want to skip out here
                    # and let the regular priority order take place
                    if not math.isclose(sf_area, ef_area, abs_tol=0.01):
                        if sf_area > ef_area:
                            start_face = extrude.startFaces[0]
                            start_end_flipped = False
                        else:
                            start_face = extrude.endFaces[0]
                            start_end_flipped = True
                        start_end_face_set = True
        # If we haven't yet decided, prioritize the start face
        if not start_end_face_set:
            if extrude.startFaces.count == 1:
                start_face = extrude.startFaces[0]
                start_end_flipped = False
            elif extrude.endFaces.count == 1:
                start_face = extrude.endFaces[0]
                start_end_flipped = True
        return start_face, start_end_flipped

    def get_extrude_end_face(self, extrude, start_end_flipped, body):
        """Get the end face from an extrude
            based on whether the start end faces are flipped"""
        end_faces = extrude.endFaces
        if start_end_flipped:
            end_faces = extrude.startFaces
        if end_faces.count > 0:
            # If we have a face to extrude to
            # lets use one from the same body
            for ef in end_faces:
                if ef.body.revisionId == body.revisionId:
                    end_face = end_faces[0]
                    break
        else:
            # Or we need to find an end face to extrude to
            # that is on coplanar to the end of the extrude
            if start_end_flipped:
                end_plane = self.get_extrude_start_plane(extrude)
            else:
                end_plane = self.get_extrude_end_plane(extrude)
            # Search for faces on the same body that are coplanar
            end_face = self.get_coplanar_face(end_plane, body)
        return end_face

    def set_face_uuids(self, bodies):
        """Set the face uuids for a collection of bodies"""
        for body in bodies:
            for face in body.faces:
                face_uuid = self.set_regraph_uuid(face)

    # -------------------------------------------------------------------------
    # FILTER
    # -------------------------------------------------------------------------

    def is_extrude_supported(self, extrude):
        """Check if this is a supported extrude for export"""
        reason = None
        if self.is_extrude_tapered(extrude):
            reason = "Extrude has taper"
        if reason is None:
            if self.mode == "PerExtrude":
                if extrude.operation == adsk.fusion.FeatureOperations.IntersectFeatureOperation:
                    reason = "Extrude has intersect operation"
            elif self.mode == "PerFace":
                # If we have a cut/intersect operation we want to use what we have
                # and export it
                # if extrude.operation == adsk.fusion.FeatureOperations.CutFeatureOperation:
                #     reason = "Extrude has cut operation"
                # If we don't have a single extrude start/end face
                if extrude.endFaces.count == 0 and extrude.startFaces.count == 0:
                    reason = "Extrude doesn't have start or end faces"
        if reason is not None:
            self.logger.log(f"Skipping {extrude.name}: {reason}")
            return False, reason
        else:
            return True, None

    @staticmethod
    def is_design_supported(json_data, mode):
        """Check the raw json data to see if this is a supported design for export"""
        if not isinstance(json_data, dict):
            with open(json_data, encoding="utf8") as f:
                json_data = json.load(f, object_pairs_hook=OrderedDict)
        reason = None
        timeline = json_data["timeline"]
        entities = json_data["entities"]
        for timeline_object in timeline:
            entity_uuid = timeline_object["entity"]
            entity_index = timeline_object["index"]
            entity = entities[entity_uuid]
            if entity["type"] == "ExtrudeFeature":
                if ("taper_angle" in entity["extent_one"] and
                        entity["extent_one"]["taper_angle"]["value"] != 0):
                    reason = "Extrude has taper"
                    break
                if mode == "PerExtrude":
                    if entity["operation"] == "IntersectFeatureOperation":
                        reason = "Extrude has intersect operation"
                        break
                elif mode == "PerFace":
                    # if entity["operation"] == "CutFeatureOperation":
                    #     reason = "Extrude has cut operation"
                    #     break
                    if len(entity["extrude_start_faces"]) == 0 and len(entity["extrude_end_faces"]) == 0:
                        reason = "Extrude doesn't have start or end faces"
                        break
        if reason is not None:
            return False, reason
        else:
            return True, None

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

    # -------------------------------------------------------------------------
    # FEATURES
    # -------------------------------------------------------------------------

    def get_face_custom_features(self, face):
        """Custom face features derived from the B-Rep"""
        face_data = {}
        face_data["reversed"] = face.isParamReversed
        # face_data["surface_type_id"] = face.geometry.surfaceType
        face_data["area"] = face.area
        normal = geometry.get_face_normal(face)
        face_data["normal_x"] = normal.x
        face_data["normal_y"] = normal.y
        face_data["normal_z"] = normal.z
        # face_data["normal_length"] = normal.length
        parameter_result, parameter_at_point = face.evaluator.getParameterAtPoint(face.pointOnFace)
        assert parameter_result
        curvature_result, max_tangent, max_curvature, min_curvature = face.evaluator.getCurvature(parameter_at_point)
        assert curvature_result
        face_data["max_tangent_x"] = max_tangent.x
        face_data["max_tangent_y"] = max_tangent.y
        face_data["max_tangent_z"] = max_tangent.z
        # face_data["max_tangent_length"] = max_tangent.length
        face_data["max_curvature"] = max_curvature
        face_data["min_curvature"] = min_curvature
        return face_data

    def get_edge_custom_features(self, edge, edge_metadata):
        """Custom edge features derived from the B-Rep"""
        edge_data = {}
        edge_data["curve_type"] = serialize.curve_type(edge.geometry)
        # edge_data["curve_type_id"] = edge.geometry.curveType
        edge_data["length"] = edge.length
        # Create a feature for the edge convexity
        edge_data["convexity"] = edge_metadata["convexity"]
        edge_data["perpendicular"] = geometry.are_faces_perpendicular(edge.faces[0], edge.faces[1])
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
        return edge_data

    def get_edge_convexity(self, edge, is_concave):
        # is_concave = self.is_concave_edge(edge.tempId)
        is_tc = geometry.are_faces_tangentially_connected(edge.faces[0], edge.faces[1])
        convexity = "Convex"
        # edge_data["convex"] = self.is_convex_edge(edge.tempId)
        if is_concave:
            convexity = "Concave"
        elif is_tc:
            convexity = "Smooth"
        return convexity

    def get_trimming_mask(self, pt, body):
        """Return a trimming mask value indicating if a point should be masked or not"""
        containment = body.pointContainment(pt)
        binary_containment = 1
        if containment == adsk.fusion.PointContainment.PointOutsidePointContainment:
            binary_containment = 0
        elif containment == adsk.fusion.PointContainment.UnknownPointContainment:
            binary_containment = 0
        return binary_containment

    def linspace(self, start, stop, n):
        if n == 1:
            yield stop
            return
        h = (stop - start) / (n - 1)
        for i in range(n):
            yield start + h * i

    def get_edge_parameter_features(self, edge):
        """UV-Net style parameter edge features"""
        param_features = {}
        samples = 10
        evaluator = edge.evaluator
        result, start_param, end_param = evaluator.getParameterExtents()
        assert result
        parameters = list(self.linspace(start_param, end_param, samples))
        result, points = evaluator.getPointsAtParameters(parameters)
        assert result
        param_features["points"] = []
        for pt in points:
            param_features["points"].append(pt.x)
            param_features["points"].append(pt.y)
            param_features["points"].append(pt.z)
        return param_features

    def get_face_parameter_features(self, face):
        """UV-Net style parameter face features"""
        param_features = {}
        samples = 10
        evaluator = face.evaluator
        range_bbox = evaluator.parametricRange()
        u_min = range_bbox.minPoint.x
        u_max = range_bbox.maxPoint.x
        v_min = range_bbox.minPoint.y
        v_max = range_bbox.maxPoint.y
        u_params = list(self.linspace(u_min, u_max, samples+2))[1:-1]
        v_params = list(self.linspace(v_min, v_max, samples+2))[1:-1]
        params = []
        for u in range(samples):
            for v in range(samples):
                pt = adsk.core.Point2D.create(u_params[u], v_params[v])
                params.append(pt)
        result, points = evaluator.getPointsAtParameters(params)
        result, normals = evaluator.getNormalsAtParameters(params)
        assert result
        param_features["points"] = []
        param_features["normals"] = []
        param_features["trimming_mask"] = []
        for i, pt in enumerate(points):
            param_features["points"].append(pt.x)
            param_features["points"].append(pt.y)
            param_features["points"].append(pt.z)
            normal = normals[i]
            param_features["normals"].append(normal.x)
            param_features["normals"].append(normal.y)
            param_features["normals"].append(normal.z)
            trim_mask = self.get_trimming_mask(pt, face.body)
            param_features["trimming_mask"].append(trim_mask)
        return param_features

    # -------------------------------------------------------------------------
    # GRAPH CONSTRUCTION
    # -------------------------------------------------------------------------

    def get_empty_graph(self):
        """Get an empty graph to start"""
        return {
            "directed": False,
            "multigraph": False,
            "graph": {},
            "nodes": [],
            "links": []
        }

    def get_graph(self):
        """Get a graph data structure for bodies"""
        graph = self.get_empty_graph()
        for body in self.reconstruction.bRepBodies:
            for face in body.faces:
                if face is not None:
                    face_data = self.get_face_data(face)
                    graph["nodes"].append(face_data)
            for edge in body.edges:
                if edge is not None:
                    edge_data = self.get_edge_data(edge)
                    graph["links"].append(edge_data)
        return graph

    def get_graph_delta(self, prev_graph, body):
        """Get a graph data structure as a delta from a previous graph
            while adding a body from an extrude"""
        graph = self.get_empty_graph()
        if prev_graph is not None:
            graph = prev_graph
        for face in body.faces:
            if face is not None:
                face_data = self.get_face_data(face)
                graph["nodes"].append(face_data)
        for edge in body.edges:
            if edge is not None:
                edge_data = self.get_edge_data(edge)
                graph["links"].append(edge_data)
        return graph

    def get_graph_from_bodies(self, bodies):
        """Get a graph from a set of bodies
            without using any cache data"""
        graph = self.get_empty_graph()
        for body in bodies:
            for face in body.faces:
                if face is not None:
                    face_data = self.get_face_data(face)
                    graph["nodes"].append(face_data)
        for body in bodies:
            for edge in body.edges:
                if edge is not None:
                    edge_data = self.get_edge_data(edge)
                    graph["links"].append(edge_data)
        return graph

    def get_face_data(self, face):
        """Get the features for a face"""
        face_uuid = self.get_regraph_uuid(face)
        assert face_uuid is not None
        face_metadata = None
        if self.include_labels:
            face_metadata = self.face_cache[face_uuid]
        if self.mode == "PerExtrude":
            return self.get_face_data_per_extrude(face, face_uuid, face_metadata)
        elif self.mode == "PerFace":
            return self.get_face_data_per_face(face, face_uuid, face_metadata)

    def get_common_face_data(self, face, face_uuid):
        """Get common edge data"""
        face_data = {}
        face_data["id"] = face_uuid
        face_data["surface_type"] = serialize.surface_type(face.geometry)
        return face_data

    def get_face_labels(self, face_metadata):
        """Get the face labels"""
        face_data = {}
        face_data["location_in_feature_label"] = face_metadata["location_in_feature_label"]
        face_data["timeline_index_label"] = face_metadata["timeline_index_label"]
        face_data["operation_label"] = face_metadata["operation_label"]
        return face_data

    def get_face_data_per_extrude(self, face, face_uuid, face_metadata=None):
        """Get the features for a face for a per extrude graph"""
        face_data = self.get_common_face_data(face, face_uuid)
        face_features = self.get_face_custom_features(face)
        face_data.update(face_features)
        if self.include_labels and face_metadata is not None:
            face_labels = self.get_face_labels(face_metadata)
            face_data.update(face_labels)
        return face_data

    def get_face_data_per_face(self, face, face_uuid, face_metadata=None):
        """Get the features for a face for a per curve graph"""
        face_data = self.get_common_face_data(face, face_uuid)
        face_param_feat = self.get_face_parameter_features(face)
        face_data.update(face_param_feat)
        if self.include_labels and face_metadata is not None:
            face_labels = self.get_face_labels(face_metadata)
            face_data.update(face_labels)
        return face_data

    def get_edge_data(self, edge):
        """Get the features for an edge"""
        edge_uuid = self.get_regraph_uuid(edge)
        assert edge_uuid is not None
        edge_metadata = self.edge_cache[edge_uuid]
        if self.mode == "PerExtrude":
            return self.get_edge_data_per_extrude(edge, edge_uuid, edge_metadata)
        elif self.mode == "PerFace":
            return self.get_edge_data_per_face(edge, edge_uuid, edge_metadata)

    def get_common_edge_data(self, edge_uuid, edge_metadata):
        """Get common edge data"""
        edge_data = {}
        edge_data["id"] = edge_uuid
        edge_data["source"] = edge_metadata["source"]
        edge_data["target"] = edge_metadata["target"]
        return edge_data

    def get_edge_data_per_extrude(self, edge, edge_uuid, edge_metadata):
        """Get the features for an edge for a per extrude graph"""
        edge_data = self.get_common_edge_data(edge_uuid, edge_metadata)
        edge_features = self.get_edge_custom_features(edge, edge_metadata)
        edge_data.update(edge_features)
        return edge_data

    def get_edge_data_per_face(self, edge, edge_uuid, edge_metadata):
        """Get the features for an edge for a per curve graph"""
        edge_data = self.get_common_edge_data(edge_uuid, edge_metadata)
        return edge_data

    def get_extrude_start_plane(self, extrude):
        """Get the plane where the extrude starts"""
        extrude_offset = self.get_extrude_offset(extrude)
        sketch, profile = self.get_extrude_sketch_profile(extrude)
        sketch_normal = profile.plane.normal
        sketch_normal.transformBy(sketch.transform)
        sketch_origin = sketch.origin
        if extrude_offset != 0:
            sketch_origin = self.offset_point_by_distance(sketch_origin, sketch_normal, extrude_offset)
        return adsk.core.Plane.create(sketch_origin, sketch_normal)

    def get_extrude_sketch_profile(self, extrude):
        """Get the sketch referenced from an extrude"""
        if isinstance(extrude.profile, adsk.fusion.Profile):
            return extrude.profile.parentSketch, extrude.profile
        elif isinstance(extrude.profile, adsk.core.ObjectCollection):
            return extrude.profile[0].parentSketch, extrude.profile[0]
        else:
            raise Exception("Extrude sketch profile error")

    def get_extrude_end_plane(self, extrude):
        """Get the plane where the extrude ends"""
        plane = self.get_extrude_start_plane(extrude)
        extrude_distance = self.get_extrude_distance(extrude)
        plane.origin = self.offset_point_by_distance(plane.origin, plane.normal, extrude_distance)
        return plane

    def offset_point_by_distance(self, point, vector, distance):
        """Offset a point along a vector by a given distance"""
        point_vector = point.asVector()
        scale_vector = vector.copy()
        scale_vector.scaleBy(distance)
        point_vector.add(scale_vector)
        return point_vector.asPoint()

    def get_extrude_distance(self, extrude):
        """Get the extrude distance"""
        if extrude.extentType != adsk.fusion.FeatureExtentTypes.OneSideFeatureExtentType:
            raise exceptions.UnsupportedException(f"Unsupported Extent Type: {extrude.extentType}")
        if not isinstance(extrude.extentOne, adsk.fusion.DistanceExtentDefinition):
            raise exceptions.UnsupportedException(f"Unsupported Extent Definition: {extrude.extentOne.objectType}")
        return extrude.extentOne.distance.value

    def get_extrude_offset(self, extrude):
        """Get any offset from the sketch plane to the extrude"""
        start_extent = extrude.startExtent
        if isinstance(start_extent, adsk.fusion.ProfilePlaneStartDefinition):
            return 0
        elif isinstance(start_extent, adsk.fusion.OffsetStartDefinition):
            offset = start_extent.offset
            # If the ProfilePlaneWithOffsetDefinition is
            # associated with an existing feature
            if isinstance(offset, adsk.fusion.ModelParameter):
                return offset.value
            # If the ProfilePlaneWithOffsetDefinition object was created statically
            # and is not associated with a feature
            elif isinstance(offset, adsk.core.ValueInput):
                if offset.valueType == adsk.fusion.ValueTypes.RealValueType:
                    return offset.realValue
                elif value_input.valueType == adsk.fusion.ValueTypes.StringValueType:
                    return float(offset.stringValue)
        return 0

    def get_coplanar_face(self, plane, body):
        """Find a face on the same body that is coplanar to the given plane"""
        # for body in self.reconstruction.bRepBodies:
        for face in body.faces:
            if isinstance(face.geometry, adsk.core.Plane):
                is_coplanar = plane.isCoPlanarTo(face.geometry)
                if is_coplanar:
                    return face
        return None

    def get_regraph_uuid(self, entity):
        """Get a uuid or a tempid depending on a flag"""
        is_face = isinstance(entity, adsk.fusion.BRepFace)
        is_edge = isinstance(entity, adsk.fusion.BRepEdge)
        if self.use_temp_id and (is_face or is_edge):
            return str(entity.tempId)
        else:
            return name.get_uuid(entity)

    def set_regraph_uuid(self, entity):
        """Set a uuid or a tempid depending on a flag"""
        is_face = isinstance(entity, adsk.fusion.BRepFace)
        is_edge = isinstance(entity, adsk.fusion.BRepEdge)
        if self.use_temp_id and (is_face or is_edge):
            return str(entity.tempId)
        else:
            return name.set_uuid(entity)


# -------------------------------------------------------------------------
# REGRAPH WRITER
# -------------------------------------------------------------------------


class RegraphWriter():
    """Reconstruction Graph Writer
        Takes a design and writes out a graph
        representing B-Rep topology"""

    def __init__(self, logger=None, mode="PerExtrude", include_labels=True):
        self.logger = logger
        if self.logger is None:
            self.logger = Logger()
        # The mode we want
        self.mode = mode
        self.include_labels = include_labels

    def write(self, file, output_dir, reconstruction):
        """Write out the design as graph json files"""
        self.output_dir = output_dir
        self.file = file
        regraph = Regraph(
            reconstruction=reconstruction,
            mode=self.mode,
            include_labels=self.include_labels
        )
        # Create the graph from the reconstruction component
        graph_data = regraph.generate()
        # If we don't get any graphs back return None
        if len(graph_data["graphs"]) <= 0:
            return None
        if self.mode == "PerFace":
            self.update_sequence_data(graph_data)
        # Perform tests on the graph data
        regraph_tester = RegraphTester(mode=self.mode)
        regraph_tester.test(graph_data)
        if self.mode == "PerFace":
            # Perform reconstruction to ensure the data is good
            # The target we want to match is
            # in the reconstruction component
            regraph_tester.reconstruct(
                graph_data,
                target=reconstruction
            )
        return self.write_graph_data(graph_data)

    def update_sequence_data(self, graph_data):
        """Update the sequence with the correct graph file names"""
        graph_files = []
        for index, graph in enumerate(graph_data["graphs"]):
            graph_file = self.get_write_path(f"{index:04}")
            graph_files.append(graph_file)
        # Add the names of the graphs to the sequence
        seq_data = graph_data["sequences"][0]
        for index, seq in enumerate(seq_data["sequence"]):
            seq["graph"] = graph_files[index].name

    def write_graph_data(self, graph_data):
        """Write the graph data generated from regraph"""
        write_data = {}
        for index, graph in enumerate(graph_data["graphs"]):
            status = graph_data["status"][index]
            graph_file = self.write_extrude_graph(graph, index)
            write_data[graph_file.name] = {
                "graph": graph,
                "status": status
            }
        if self.mode == "PerFace":
            seq_data = graph_data["sequences"][0]
            seq_file = self.write_sequence(seq_data)
            write_data[seq_file.name] = seq_data
        return write_data

    def get_write_path(self, name):
        """Get the write path from a name"""
        return self.output_dir / f"{self.file.stem}_{name}.json"

    def write_extrude_graph(self, graph, extrude_index):
        """Write a graph from an extrude operation"""
        graph_file = self.get_write_path(f"{extrude_index:04}")
        self.write_graph(graph_file, graph)
        return graph_file

    def write_graph(self, graph_file, graph):
        """Write a graph as json"""
        self.logger.log(f"Exporting {graph_file}")
        exporter.export_json(graph_file, graph)

    def write_sequence(self, seq_data):
        """Write the sequence data"""
        seq_file = self.output_dir / f"{self.file.stem}_sequence.json"
        with open(seq_file, "w", encoding="utf8") as f:
            json.dump(seq_data, f, indent=4)
        return seq_file


# -------------------------------------------------------------------------
# REGRAPH TESTER
# -------------------------------------------------------------------------


class RegraphTester(unittest.TestCase):
    """Reconstruction Graph tester to check for invalid data"""

    def __init__(self, mode="PerExtrude"):
        self.mode = mode
        unittest.TestCase.__init__(self)

    def test(self, graph_data):
        """Test the graph data structure returned by regraph"""
        if self.mode == "PerExtrude":
            for graph in graph_data["graphs"]:
                self.test_per_extrude_graph(graph)
        elif self.mode == "PerFace":
            if len(graph_data["sequences"]) > 0:
                self.assertEqual(len(graph_data["sequences"]), 1, msg="Only 1 per face sequence")
                sequence = graph_data["sequences"][0]
                self.assertGreaterEqual(len(graph_data["graphs"]), 1, msg=">= 1 per face graph")
                self.assertEqual(len(graph_data["graphs"]), len(sequence["sequence"]), msg="Number of graphs === sequence length")
                for index, graph in enumerate(graph_data["graphs"]):
                    node_set, link_set = self.test_per_face_graph(graph)
                self.test_per_face_sequence(sequence, node_set, link_set)

    def reconstruct(self, graph_data, target):
        """Reconstruct and test it matches the target"""
        # We create another temporary test component
        # to perform reconstruction in
        app = adsk.core.Application.get()
        design = adsk.fusion.Design.cast(app.activeProduct)
        test_comp = design.rootComponent.occurrences.addNewComponent(
            adsk.core.Matrix3D.create()
        )
        name = f"Test_{test_comp.component.name}"
        test_comp.component.name = name
        face_reconstructor = FaceReconstructor(
            target=target,
            reconstruction=test_comp,
            use_temp_id=False
        )
        face_reconstructor.reconstruct(graph_data)
        # Compare the ground truth with the reconstruction
        self.test_reconstruction(target, test_comp)
        # Clean up
        test_comp.deleteMe()
        adsk.doEvents()

    def test_per_extrude_graph(self, graph):
        """Test a per extrude graph"""
        self.assertIsNotNone(graph, msg="Graph is not None")
        self.assertIn("nodes", graph, msg="Graph has nodes")
        self.assertIn("links", graph, msg="Graph has links")
        self.assertGreaterEqual(len(graph["nodes"]), 3, msg="Graph nodes >= 3")
        self.assertGreaterEqual(len(graph["links"]), 2, msg="Graph links >= 2")
        node_set = set()
        node_list = []
        for node in graph["nodes"]:
            self.assertIn("id", node, msg="Graph node has id")
            node_set.add(node["id"])
            node_list.append(node["id"])
        self.assertEqual(len(node_set), len(node_list), msg="Graph nodes are unique")
        for link in graph["links"]:
            self.assertIn("id", link, msg="Graph link has id")
            self.assertIn("source", link, msg="Graph link has source")
            self.assertIn(link["source"], node_set, msg="Graph link source in node set")
            self.assertIn("target", link, msg="Graph link has target")
            self.assertIn(link["target"], node_set, msg="Graph link target in node set")

    def test_per_face_graph(self, graph):
        """Test a per face graph"""
        # Target graph
        self.assertIsNotNone(graph, msg="Graph is not None")
        self.assertIn("nodes", graph, msg="Graph has nodes")
        self.assertIsInstance(graph["nodes"], list, msg="Nodes is list")
        self.assertIn("links", graph, msg="Graph has links")
        self.assertIsInstance(graph["links"], list, msg="Links is list")
        self.assertGreaterEqual(len(graph["nodes"]), 3, msg="Graph nodes >= 3")
        self.assertGreaterEqual(len(graph["links"]), 2, msg="Graph links >= 3")
        node_set = set()
        node_list = []
        for node in graph["nodes"]:
            self.assertIn("id", node, msg="Graph node has id")
            node_set.add(node["id"])
            node_list.append(node["id"])
        self.assertEqual(len(node_set), len(node_list), msg="Graph nodes are unique")
        link_set = set()
        for link in graph["links"]:
            self.assertIn("id", link, msg="Graph link has id")
            link_set.add(link["id"])
            # Check that the edges refer to existing faces
            self.assertIn("source", link, msg="Graph link has source")
            self.assertIn(link["source"], node_set, msg="Graph link source in node set")
            self.assertIn("target", link, msg="Graph link has target")
            self.assertIn(link["target"], node_set, msg="Graph link target in node set")
        return node_set, link_set

    def test_per_face_sequence(self, sequence, node_set, link_set):
        # Sequence
        self.assertIsNotNone(sequence, msg="Sequence is not None")
        self.assertIn("sequence", sequence, msg="Sequence has sequence")
        self.assertGreaterEqual(len(sequence["sequence"]), 1, msg="Sequence length >= 1")
        valid_extrudes = [
            "JoinFeatureOperation",
            "CutFeatureOperation",
            "IntersectFeatureOperation",
            "NewBodyFeatureOperation"
        ]
        for seq in sequence["sequence"]:
            # Check that the faces are in the target
            self.assertIn("start_face", seq, msg="Sequence element has start_face")
            self.assertIn(seq["start_face"], node_set, msg="Start face is in target nodes")
            self.assertIn("end_face", seq, msg="Sequence element has end_face")
            self.assertIn(seq["end_face"], node_set, msg="End face is in target nodes")
            self.assertIn("operation", seq, msg="Sequence element has operation")
            self.assertIn(seq["operation"], valid_extrudes, msg="Operation is valid")
            self.assertIn("graph", seq, msg="Sequence element has graph")
            self.assertIsInstance(seq["graph"], str, msg="Sequence graph is string")
            self.assertTrue(seq["graph"].endswith(".json"), msg="Sequence ends with .json")

        # Properties
        self.assertIn("properties", sequence, msg="Sequence has properties")
        self.assertIn("bounding_box", sequence["properties"], msg="Properties has bounding_box")
        self.assertIn("extrude_count", sequence["properties"], msg="Properties has extrude_count")
        self.assertIn("body_count", sequence["properties"], msg="Properties has body_count")

    def test_reconstruction(self, gt, rc, places=1):
        """Test the reconstruction"""
        # Update the UI so bounding boxes are accurate
        adsk.doEvents()        
        self.assertEqual(
            len(gt.bRepBodies),
            len(rc.bRepBodies),
            msg="Same number of bodies"
        )
        self.assertEqual(
            geometry.get_face_count(gt),
            geometry.get_face_count(rc),
            msg="Same number of faces"
        )
        self.assertEqual(
            geometry.get_edge_count(gt),
            geometry.get_edge_count(rc),
            msg="Same number of edges"
        )
        gt_bbox = geometry.get_bounding_box(gt)
        rc_bbox = geometry.get_bounding_box(rc)
        self.assertAlmostEqual(
            rc_bbox.maxPoint.x,
            gt_bbox.maxPoint.x,
            places=places, msg="bounding_box_max_x"
        )
        self.assertAlmostEqual(
            rc_bbox.maxPoint.y,
            gt_bbox.maxPoint.y,
            places=places,
            msg="bounding_box_max_y"
        )
        self.assertAlmostEqual(
            rc_bbox.maxPoint.z,
            gt_bbox.maxPoint.z,
            places=places,
            msg="bounding_box_max_z"
        )
        self.assertAlmostEqual(
            rc_bbox.minPoint.x,
            gt_bbox.minPoint.x,
            places=places,
            msg="bounding_box_min_x"
        )
        self.assertAlmostEqual(
            rc_bbox.minPoint.y,
            gt_bbox.minPoint.y,
            places=places,
            msg="bounding_box_min_y"
        )
        self.assertAlmostEqual(
            rc_bbox.minPoint.z,
            gt_bbox.minPoint.z,
            places=places,
            msg="bounding_box_min_z"
        )
        self.assertFalse(
            math.isinf(rc_bbox.maxPoint.x),
            msg="bounding_box_max_x != inf"
        )
        self.assertFalse(
            math.isinf(rc_bbox.maxPoint.y),
            msg="bounding_box_max_y != inf"
        )
        self.assertFalse(
            math.isinf(rc_bbox.maxPoint.z),
            msg="bounding_box_max_z != inf"
        )
        self.assertFalse(
            math.isinf(rc_bbox.minPoint.x),
            msg="bounding_box_min_x != inf"
        )
        self.assertFalse(
            math.isinf(rc_bbox.minPoint.y),
            msg="bounding_box_min_y != inf"
        )
        self.assertFalse(
            math.isinf(rc_bbox.minPoint.z),
            msg="bounding_box_min_z != inf"
        )
