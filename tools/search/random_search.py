import sys
import os
import random
import math
from pathlib import Path

from base_search import BaseSearch


class RandomSearch(BaseSearch):

    def __init__(self, host, port):
        BaseSearch.__init__(self, host, port)
        self.target_faces = None
        self.operations = ["JoinFeatureOperation", "CutFeatureOperation"]

    def setup(self, target_file):
        super().setup(target_file)
        assert self.target_graph is not None
        # Store a list of the planar faces we can choose from
        self.target_faces = []
        for node in self.target_graph["nodes"]:
            if node["surface_type"] == "PlaneSurfaceType":
                self.target_faces.append(node["id"])
        assert len(self.target_faces) >= 2

    def run(self):
        while self.steps < 100:
            faces = self.get_random_faces()
            start_face = faces[0]
            end_face = faces[1]
            operation = self.get_operation()
            graph, iou = self.extrude(start_face, end_face, operation)
            print(f"Start: {start_face} \tEnd: {end_face} \tOperation: {operation:20} \tIoU: {iou}")
            if iou is not None:
                if math.isclose(iou, 1.0, abs_tol=0.0001):
                    break
        self.save_log()

    def get_random_faces(self):
        """Get a random face from the target graph"""
        assert self.target_faces is not None
        return random.sample(self.target_faces, 2)

    def get_operation(self):
        """Get a semi-random extrude operation"""
        if not self.first_extrude_complete:
            return "NewBodyFeatureOperation"
        else:
            return random.choice(self.operations)


def main():
    # Connects to FusionGym when initialzied
    search = RandomSearch(host="127.0.0.1", port=8080)
    # Setup with the target file we are trying to recreate
    target_file = search.testdata_dir / "Couch.smt"
    search.setup(target_file)
    search.run()

if __name__ == "__main__":
    main()
