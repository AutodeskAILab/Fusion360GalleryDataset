
import sys
import os

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "fusion360gym", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)

from fusion_360_client import Fusion360Client


class ReplEnv():

    def __init__(self, host="127.0.0.1", port=8080):
        self.host = host
        self.port = port
        self.client = Fusion360Client(f"http://{self.host}:{self.port}")

    def set_target(self, target_file):
        """Setup search and connect to the Fusion Gym"""
        # Set the target
        r = self.client.set_target(target_file)
        self.__check_response("set_target", r)
        response_json = r.json()
        if "data" not in response_json or "graph" not in response_json["data"]:
            raise Exception("[set_target] response graph missing")
        return response_json["data"]["graph"]

    def revert_to_target(self):
        """Revert to the target to start the search again"""
        r = self.client.revert_to_target()
        self.__check_response("revert_to_target", r)
        response_json = r.json()
        if "data" not in response_json or "graph" not in response_json["data"]:
            raise Exception("[revert_to_target] response graph missing")
        return response_json["data"]["graph"]

    def get_empty_graph(self):
        """Get an empty graph to kick things off"""
        return {
            "directed": False,
            "multigraph": False,
            "graph": {},
            "nodes": [],
            "links": []
        }

    def extrude(self, start_face, end_face, operation):
        """Extrude wrapper around the gym client"""
        is_invalid = False
        return_graph = None
        return_iou = None
        r = self.client.add_extrude_by_target_face(
            start_face, end_face, operation)
        if r is not None and r.status_code == 200:
            response_json = r.json()
            if ("data" in response_json and
                    "graph" in response_json["data"] and
                    "iou" in response_json["data"]):
                return_graph = response_json["data"]["graph"]
                return_iou = response_json["data"]["iou"]
        return return_graph, return_iou

    def screenshot(self, file):
        """Save out a screenshot"""
        r = self.client.screenshot(file)
        return r is not None and r.status_code == 200

    def __check_response(self, call, r):
        """Check the response is valid and raise exceptions if not"""
        if r is None:
            raise Exception(f"[{call}] response is None")
        if r.status_code != 200:
            response_data = r.json()
            raise Exception(f"[{call}] {r.status_code}: {response_data['message']}")