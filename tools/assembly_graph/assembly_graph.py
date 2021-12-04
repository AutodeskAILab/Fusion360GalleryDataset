import sys
import json
import argparse
import time
from pathlib import Path
import numpy as np


class AssemblyGraph():
    """
    Construct a graph representing an assembly with connectivity
    between visible B-Rep bodies with joints and contact surfaces
    """

    def __init__(self, assembly_data):
        if isinstance(assembly_data, dict):
            self.assembly_data = assembly_data
        else:
            if isinstance(assembly_data, str):
                assembly_file = Path(assembly_data)
            else:
                assembly_file = assembly_data
            assert assembly_file.exists()
            with open(assembly_file, "r", encoding="utf-8") as f:
                self.assembly_data = json.load(f)
        self.graph_nodes = []
        self.graph_links = []
        self.graph_node_ids = set()

    def get_graph_data(self):
        """Get the graph data as a list of nodes and links"""
        self.graph_nodes = []
        self.graph_links = []
        self.graph_node_ids = set()
        # TODO: Add support for a flag to include hidden bodies
        self.populate_graph_nodes()
        self.populate_graph_links()
        return self.graph_nodes, self.graph_links

    def get_graph_networkx(self):
        """Get a networkx graph"""
        graph_data = {
            "directed": True,
            "multigraph": False,
            "graph": {},
            "nodes": [],
            "links": []
        }
        graph_data["nodes"], graph_data["links"] = self.get_graph_data()
        from networkx.readwrite import json_graph
        return json_graph.node_link_graph(graph_data)

    def get_node_label_dict(self, attribute="occurrence_name"):
        """Get a dictionary mapping from node ids to a given attribute"""
        label_dict = {}
        if len(self.graph_nodes) == 0:
            return label_dict
        for node in self.graph_nodes:
            node_id = node["id"]
            if attribute in node:
                node_att = node[attribute]
            else:
                node_att = node["body_name"]
            label_dict[node_id] = node_att
        return label_dict

    def export_graph_json(self, json_file):
        """Export the graph as an networkx node-link format json file"""
        graph_data = {
            "directed": True,
            "multigraph": False,
            "graph": {},
            "nodes": [],
            "links": []
        }
        graph_data["nodes"], graph_data["links"] = self.get_graph_data()
        with open(json_file, "w", encoding="utf8") as f:
            json.dump(graph_data, f, indent=4)
        return json_file.exists()

    def populate_graph_nodes(self):
        """
        Recursively traverse the assembly tree
        and generate a flat set of graph nodes from bodies
        """
        # First get the root and add it's bodies
        root_component_uuid = self.assembly_data["root"]["component"]
        root_component = self.assembly_data["components"][root_component_uuid]
        if "bodies" in root_component:
            for body_uuid in root_component["bodies"]:
                node_data = self.get_graph_node_data(body_uuid)
                self.graph_nodes.append(node_data)
        # Recurse over the occurrences in the tree
        tree_root = self.assembly_data["tree"]["root"]
        # Start with an identity matrix
        root_transform = np.identity(4)
        self.walk_tree(tree_root, root_transform)
        # Check all our node ids are unique
        total_nodes = len(self.graph_nodes)
        self.graph_node_ids = set([f["id"] for f in self.graph_nodes])
        assert total_nodes == len(self.graph_node_ids), "Duplicate node ids found"

    def populate_graph_links(self):
        """Create links in the graph between bodies with joints and contacts"""
        if "joints" in self.assembly_data:
            self.populate_graph_joint_links()
        if "as_built_joints" in self.assembly_data:
            self.populate_graph_as_built_joint_links()
        if "contacts" in self.assembly_data:
            self.populate_graph_contact_links()

    def walk_tree(self, occ_tree, occ_transform):
        """Recursively walk the occurrence tree"""
        for occ_uuid, occ_sub_tree in occ_tree.items():
            occ = self.assembly_data["occurrences"][occ_uuid]
            if not occ["is_visible"]:
                continue
            occ_sub_transform = occ_transform @ self.transform_to_matrix(occ["transform"])
            if "bodies" in occ:
                for occ_body_uuid, occ_body in occ["bodies"].items():
                    if not occ_body["is_visible"]:
                        continue
                    node_data = self.get_graph_node_data(
                        occ_body_uuid,
                        occ_uuid,
                        occ,
                        occ_sub_transform
                    )
                    self.graph_nodes.append(node_data)
            self.walk_tree(occ_sub_tree, occ_sub_transform)

    def get_graph_node_data(self, body_uuid, occ_uuid=None, occ=None, transform=None):
        """Add a body as a graph node"""
        body = self.assembly_data["bodies"][body_uuid]
        node_data = {}
        if occ_uuid is None:
            body_id = body_uuid
        else:
            body_id = f"{occ_uuid}_{body_uuid}"
        node_data["id"] = body_id
        node_data["body_name"] = body["name"]
        node_data["body_file"] = body_uuid
        if occ:
            node_data["occurrence_name"] = occ["name"]
        if transform is None:
            transform = np.identity(4)
        node_data["transform"] = transform.tolist()
        return node_data

    def populate_graph_joint_links(self):
        """Populate directed links between bodies with joints"""
        if self.assembly_data["joints"] is None:
            return
        for joint_uuid, joint in self.assembly_data["joints"].items():
            # TODO: Consider links between entity_two if it exists
            ent1 = joint["geometry_or_origin_one"]["entity_one"]
            ent2 = joint["geometry_or_origin_two"]["entity_one"]
            # Don't add links when the bodies aren't visible
            body1_visible = self.is_body_visible(ent1)
            body2_visible = self.is_body_visible(ent2)
            if not body1_visible or not body2_visible:
                continue
            link_data = self.get_graph_link_data(ent1, ent2)
            link_data["type"] = "Joint"
            link_data["joint_type"] = joint["joint_motion"]["joint_type"]
            # TODO: Add more joint features
            self.graph_links.append(link_data)

    def populate_graph_as_built_joint_links(self):
        """Populate directed links between bodies with as built joints"""
        if self.assembly_data["as_built_joints"] is None:
            return
        for joint_uuid, joint in self.assembly_data["as_built_joints"].items():
            geo_ent = None
            geo_ent_id = None
            # For non rigid joint types we will get geometry
            if "joint_geometry" in joint:
                if "entity_one" in joint["joint_geometry"]:
                    geo_ent = joint["joint_geometry"]["entity_one"]
                    geo_ent_id = self.get_link_entity_id(geo_ent)

            occ1 = joint["occurrence_one"]
            occ2 = joint["occurrence_two"]
            body1 = None
            body2 = None
            if geo_ent is not None and "occurrence" in geo_ent:
                if geo_ent["occurrence"] == occ1:
                    body1 = geo_ent["body"]
                elif geo_ent["occurrence"] == occ2:
                    body2 = geo_ent["body"]

            # We only add links if there is a single body
            # in both occurrences
            # TODO: Look deeper in the tree if there is a single body
            if body1 is None:
                body1 = self.get_occurrence_body_uuid(occ1)
                if body1 is None:
                    continue
            if body2 is None:
                body2 = self.get_occurrence_body_uuid(occ2)
                if body2 is None:
                    continue
            # Don't add links when the bodies aren't visible
            body1_visible = self.is_body_visible(body_uuid=body1, occurrence_uuid=occ1)
            body2_visible = self.is_body_visible(body_uuid=body2, occurrence_uuid=occ2)
            if not body1_visible or not body2_visible:
                continue
            ent1 = f"{occ1}_{body1}"
            ent2 = f"{occ2}_{body2}"
            link_id = f"{ent1}>{ent2}"
            link_data = {}
            link_data["id"] = link_id
            link_data["source"] = ent1
            assert link_data["source"] in self.graph_node_ids, "Link source id doesn't exist in nodes"
            link_data["target"] = ent2
            assert link_data["target"] in self.graph_node_ids, "Link target id doesn't exist in nodes"
            link_data["type"] = "AsBuiltJoint"
            link_data["joint_type"] = joint["joint_motion"]["joint_type"]
            # TODO: Add more joint features
            self.graph_links.append(link_data)

    def populate_graph_contact_links(self):
        """Populate undirected links between bodies in contact"""
        if self.assembly_data["contacts"] is None:
            return
        for contact in self.assembly_data["contacts"]:
            ent1 = contact["entity_one"]
            ent2 = contact["entity_two"]
            # Don't add links when the bodies aren't visible
            body1_visible = self.is_body_visible(ent1)
            body2_visible = self.is_body_visible(ent2)
            if not body1_visible or not body2_visible:
                continue
            link_data = self.get_graph_link_data(ent1, ent2)
            link_data["type"] = "Contact"
            self.graph_links.append(link_data)
            # Add a link in reverse so we have a undirected connection
            link_data = self.get_graph_link_data(ent2, ent1)
            link_data["type"] = "Contact"
            self.graph_links.append(link_data)

    def get_graph_link_data(self, entity_one, entity_two):
        """Get the common data for a graph link from a joint or contact"""
        link_data = {}
        link_data["id"] = self.get_link_id(entity_one, entity_two)
        link_data["source"] = self.get_link_entity_id(entity_one)
        assert link_data["source"] in self.graph_node_ids, "Link source id doesn't exist in nodes"
        link_data["target"] = self.get_link_entity_id(entity_two)
        assert link_data["target"] in self.graph_node_ids, "Link target id doesn't exist in nodes"
        return link_data

    def get_link_id(self, entity_one, entity_two):
        """Get a unique id for a link"""
        ent1_id = self.get_link_entity_id(entity_one)
        ent2_id = self.get_link_entity_id(entity_two)
        return f"{ent1_id}>{ent2_id}"

    def get_link_entity_id(self, entity):
        """Get a unique id for one side of a link"""
        if "occurrence" in entity:
            return f"{entity['occurrence']}_{entity['body']}"
        else:
            return entity["body"]

    def get_occurrence_body_uuid(self, occurrence_uuid):
        """Get the body uuid from an occurrence"""
        occ = self.assembly_data["occurrences"][occurrence_uuid]
        # We only return a body_uuid if there is one body
        if "bodies" not in occ:
            return None
        if len(occ["bodies"]) != 1:
            return None
        # Return the first key
        return next(iter(occ["bodies"]))

    def is_body_visible(self, entity=None, body_uuid=None, occurrence_uuid=None):
        """Check if a body is visible"""
        if body_uuid is None:
            body_uuid = entity["body"]
        if occurrence_uuid is None:
            # If we don't have an occurrence
            # we need to look in the root component
            if "occurrence" not in entity:
                body = self.assembly_data["root"]["bodies"][body_uuid]
                return body["is_visible"]
            # First check the occurrence is visible
            occurrence_uuid = entity["occurrence"]
        occ = self.assembly_data["occurrences"][occurrence_uuid]
        if not occ["is_visible"]:
            return False
        body = occ["bodies"][body_uuid]
        return body["is_visible"]

    def transform_to_matrix(self, transform=None):
        """
        Convert a transform dict into a
        4x4 affine transformation matrix
        """
        if transform is None:
            return np.identity(4)
        x_axis = self.transform_vector_to_np(transform["x_axis"])
        y_axis = self.transform_vector_to_np(transform["y_axis"])
        z_axis = self.transform_vector_to_np(transform["z_axis"])
        translation = self.transform_vector_to_np(transform["origin"])
        translation[3] = 1.0
        return np.transpose(np.stack([x_axis, y_axis, z_axis, translation]))

    def transform_vector_to_np(self, vector):
        x = vector["x"]
        y = vector["y"]
        z = vector["z"]
        h = 0.0
        return np.array([x, y, z, h])
