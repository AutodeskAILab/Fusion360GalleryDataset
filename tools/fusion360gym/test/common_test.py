import math
import json
from pathlib import Path


def check_graph_format(self, response_data, mode=None, labels=False):
    """Check the graph data that comes back is in the right format"""
    # If this is a json file, open it and load the data
    if isinstance(response_data, Path):
        with open(response_data, "r", encoding="utf8") as f:
            json_data = json.load(f)
        graph = json_data
    else:
        self.assertIn("graph", response_data, msg="graph in response_data")
        graph = response_data["graph"]
    # Metadata check
    self.assertIsNotNone(graph, msg="Graph is not None")
    self.assertIn("directed", graph, msg="Graph has directed")
    self.assertFalse(graph["directed"], msg="Directs is false")
    self.assertIn("multigraph", graph, msg="Graph has multigraph")
    self.assertIn("graph", graph, msg="Graph has graph")
    self.assertFalse(graph["multigraph"], msg="Multigraph is false")
    self.assertIsInstance(graph["graph"], dict, msg="Graph graph is dict")
    # Node and link check
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
    for link in graph["links"]:
        self.assertIn("id", link, msg="Graph link has id")
        # Check that the edges refer to existing faces
        self.assertIn("source", link, msg="Graph link has source")
        self.assertIn(link["source"], node_set, msg="Graph link source in node set")
        self.assertIn("target", link, msg="Graph link has target")
        self.assertIn(link["target"], node_set, msg="Graph link target in node set")

    if mode is None:
        return

    check_graph_node_features(self, graph["nodes"], mode)
    check_graph_link_features(self, graph["links"], mode)
    check_node_labels(self, graph["nodes"], labels)


def check_node_labels(self, nodes, labels):
    """Check the labels in the graph"""
    operations_labels = {
        "CutFeatureOperation",
        "IntersectFeatureOperation",
        "JoinFeatureOperation",
        "NewBodyFeatureOperation",
        "NewComponentFeatureOperation"
    }
    location_in_feature_labels = {
        "SideFace",
        "StartFace",
        "EndFace"
    }
    for node in nodes:
        if labels:
            self.assertIn("operation_label", node, msg="Graph node has operation_label")
            self.assertIn(node["operation_label"], operations_labels, msg="Valid operation_label")
            self.assertIn("timeline_index_label", node, msg="Graph node has timeline_index_label")
            self.assertIsInstance(node["timeline_index_label"], int, msg="timeline_index_label is an int")
            self.assertIn("location_in_feature_label", node, msg="Graph node has location_in_feature_label")
            self.assertIn(node["location_in_feature_label"], location_in_feature_labels, msg="Valid location_in_feature_label")
        else:
            self.assertNotIn("operation_label", node, msg="Graph node has no operation_label")
            self.assertNotIn("timeline_index_label", node, msg="Graph node has no timeline_index_label")
            self.assertNotIn("location_in_feature_label", node, msg="Graph node has no location_in_feature_label")


def check_graph_node_features(self, nodes, mode):
    """Check the graph node features"""
    surface_types = {
        "ConeSurfaceType",
        "CylinderSurfaceType",
        "EllipticalConeSurfaceType",
        "EllipticalCylinderSurfaceType",
        "NurbsSurfaceType",
        "PlaneSurfaceType",
        "SphereSurfaceType",
        "TorusSurfaceType"
    }
    per_extrude_features = {
        "reversed": bool,
        "area": float,
        "normal_x": float,
        "normal_y": float,
        "normal_z": float,
        "max_tangent_x": float,
        "max_tangent_y": float,
        "max_tangent_z": float,
        "max_curvature": float,
        "min_curvature": float,
    }

    for node in nodes:
        self.assertIn("surface_type", node, msg="Graph node has surface_type")
        self.assertIn(node["surface_type"], surface_types, msg="Valid surface type")

        if mode == "PerFace":
            self.assertIn("points", node, msg="Graph node has points")
            self.assertIsInstance(node["points"], list, msg="Points is a list")
            for point in node["points"]:
                self.assertIsInstance(point, float, msg="Point is a float")
                self.assertFalse(math.isinf(point), msg="Normal != inf")

            self.assertIn("normals", node, msg="Graph node has normals")
            self.assertIsInstance(node["normals"], list, msg="Normals is a list")
            for normal in node["normals"]:
                self.assertIsInstance(normal, float, msg="Normal is a float")
                self.assertFalse(math.isinf(normal), msg="Normal != inf")

            self.assertIn("trimming_mask", node, msg="Graph node has trimming_mask")
            self.assertIsInstance(node["trimming_mask"], list, msg="trimming_mask is a list")
            for tm in node["trimming_mask"]:
                self.assertIsInstance(tm, int, msg="Trimming mask is an int")
            points_len = len(node["points"])
            normals_len = len(node["normals"])
            self.assertEqual(points_len, normals_len, msg="#points == #normals")
            tm_len = len(node["trimming_mask"])
            self.assertEqual(int(points_len / 3), tm_len, msg="#points/3 == #trimming mask")

        elif mode == "PerExtrude":
            for feature, feature_type in per_extrude_features.items():
                self.assertIn(feature, node, msg=f"Graph node has {feature}")
                self.assertIsInstance(node[feature], feature_type, msg=f"{feature} is {str(feature_type)}")


def check_graph_link_features(self, links, mode):
    """Check the graph link (edge) features"""
    curve_types = {
        "Line3DCurveType",
        "Arc3DCurveType"
        "Circle3DCurveType",
        "Ellipse3DCurveType",
        "EllipticalArc3DCurveType",
        "InfiniteLine3DCurveType",
        "Line3DCurveType",
        "NurbsCurve3DCurveType",
    }
    convexity_types = {
        "Concave",
        "Convex"
    }
    edge_features = {
        "length": float,
        "perpendicular": bool,
        "direction_x": float,
        "direction_y": float,
        "direction_z": float,
        "curvature": float
    }
    for link in links:
        if mode == "PerExtrude":
            for feature, feature_type in edge_features.items():
                self.assertIn(feature, link, msg=f"Graph link has {feature}")
                self.assertIsInstance(link[feature], feature_type, msg=f"{feature} is {str(feature_type)}")
            self.assertIn("curve_type", link, msg="Graph link has curve_type")
            self.assertIn(link["curve_type"], curve_types, msg="Valid curve_type")
            self.assertIn("convexity", link, msg="Graph link has convexity")
            self.assertIn(link["convexity"], convexity_types, msg="Valid convexity")            


def check_empty_graph_format(self, response_data):
    """Check the graph data that comes back is in the right format"""
    self.assertIn("graph", response_data, msg="graph in response_data")
    graph = response_data["graph"]
    # Metadata check
    self.assertIsNotNone(graph, msg="Graph is not None")
    self.assertIn("directed", graph, msg="Graph has directed")
    self.assertFalse(graph["directed"], msg="Directs is false")
    self.assertIn("multigraph", graph, msg="Graph has multigraph")
    self.assertIn("graph", graph, msg="Graph has graph")
    self.assertFalse(graph["multigraph"], msg="Multigraph is false")
    self.assertIsInstance(graph["graph"], dict, msg="Graph graph is dict")
    # Node and link check
    self.assertIn("nodes", graph, msg="Graph has nodes")
    self.assertIsInstance(graph["nodes"], list, msg="Nodes is list")
    self.assertIn("links", graph, msg="Graph has links")
    self.assertIsInstance(graph["links"], list, msg="Links is list")


def check_bounding_box(self, response_data):
    """Check the bounding box data that comes back is in the right format"""
    self.assertIn("bounding_box", response_data, msg="bounding_box in response_data")
    bbox = response_data["bounding_box"]

    self.assertIn("max_point", bbox, msg="max_point in bounding_box")
    self.assertIn("x", bbox["max_point"], msg="x in max_point")
    self.assertIn("y", bbox["max_point"], msg="y in max_point")
    self.assertIn("z", bbox["max_point"], msg="z in max_point")
    self.assertIsInstance(bbox["max_point"]["x"], float, msg="max_point x is float")
    self.assertIsInstance(bbox["max_point"]["y"], float, msg="max_point y is float")
    self.assertIsInstance(bbox["max_point"]["z"], float, msg="max_point z is float")

    self.assertIn("min_point", bbox, msg="min_point in bounding_box")
    self.assertIn("x", bbox["min_point"], msg="x in min_point")
    self.assertIn("y", bbox["min_point"], msg="y in min_point")
    self.assertIn("z", bbox["min_point"], msg="z in min_point")
    self.assertIsInstance(bbox["min_point"]["x"], float, msg="min_point x is float")
    self.assertIsInstance(bbox["min_point"]["y"], float, msg="min_point y is float")
    self.assertIsInstance(bbox["min_point"]["z"], float, msg="min_point z is float")

    self.assertFalse(
        math.isinf(bbox["max_point"]["x"]),
        msg="bounding_box_max_x != inf"
    )
    self.assertFalse(
        math.isinf(bbox["max_point"]["y"]),
        msg="bounding_box_max_y != inf"
    )
    self.assertFalse(
        math.isinf(bbox["max_point"]["z"]),
        msg="bounding_box_max_z != inf"
    )
    self.assertFalse(
        math.isinf(bbox["min_point"]["x"]),
        msg="bounding_box_min_x != inf"
    )
    self.assertFalse(
        math.isinf(bbox["min_point"]["y"]),
        msg="bounding_box_min_y != inf"
    )
    self.assertFalse(
        math.isinf(bbox["min_point"]["z"]),
        msg="bounding_box_min_z != inf"
    )


def check_extrude_data(self, response_data, has_iou=False):
    """Check the data returned from extrude operations"""
    # Extrude
    self.assertIn("extrude", response_data, msg="extrude data has extrude")
    self.assertIsInstance(response_data["extrude"], dict, msg="extrude data is dict")
    extrude_data = response_data["extrude"]
    self.assertIn("type", extrude_data, msg="extrude data response has type")
    self.assertIn("faces", extrude_data, msg="extrude data response has faces")
    self.assertIsInstance(extrude_data["faces"], list, msg="extrude data faces is list")
    self.assertGreater(len(extrude_data["faces"]), 0, msg="extrude data faces length greater than 0")
    # Graph
    self.assertIn("graph", response_data, msg="extrude data has graph")
    self.assertIsInstance(response_data["graph"], dict, msg="extrude graph is dict")
    check_graph_format(self, response_data, mode="PerFace")
    # IoU
    if has_iou:
        self.assertIn("iou", response_data, msg="response has iou")
        self.assertIsInstance(response_data["iou"], float, msg="iou is float")
        self.assertGreaterEqual(response_data["iou"], 0, msg="iou >= 0")
    # Bounding Box
    self.assertIn("bounding_box", response_data, msg="extrude data has bounding_box")
    self.assertIsInstance(response_data["bounding_box"], dict, msg="extrude bounding_box is dict")
    check_bounding_box(self, response_data)
