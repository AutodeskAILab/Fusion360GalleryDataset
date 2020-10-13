import math


def check_graph_format(self, response_data):
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
