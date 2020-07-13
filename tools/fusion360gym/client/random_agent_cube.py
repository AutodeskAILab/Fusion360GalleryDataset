from pathlib import Path
import sys
import os
import json
import random
import time
from fusion_360_client import Fusion360Client

# Before running ensure the Fusion360Server is running
# and configured with the same host name and port number
HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080

class RandomAgent():

    """Policy that takes random actions and never learns."""
    def __init__(self, config):
        
        self.max_episodes = config["max_episodes"]
        self.max_steps = config["max_steps"]

        self.min_points = 4
        self.max_points = 4

        self.low_width = -10
        self.high_width = 10
        self.low_height = -10
        self.high_height = 10

        self.low_dist = -2
        self.high_dist = 2

        # self.reset()


    def reset(self):

        # Create the client class to interact with the server
        self.client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")
        # Clear to force close all documents in Fusion
        r = self.client.clear()

        # Create an empty sketch on a random plane
        planes = ["XY", "XZ", "YZ"]
        random_plane = random.choice(planes)
        r = self.client.add_sketch(random_plane)
        
        # Get the unique name of the sketch created
        response_json = r.json()
        sketch_name = response_json["data"]["sketch_name"]
        
        # use width and height as x & y constraint
        # x & y could be defined separately if necessary
        # pts = self._draw_rect([[self.low_width, self.high_width], [self.low_height, self.high_height]])

        pts = [
            {"x": 5, "y": 5},
            {"x": 5, "y": -5},
            {"x": -5, "y": -5},
            {"x": -5, "y": 5}
        ]

        # random draw points
        # pts = []
        # num_points = random.randint(self.min_points, self.max_points) 
        # for _ in range(num_points):
        #     x = random.uniform(self.low_x, self.high_x)
        #     y = random.uniform(self.low_y, self.high_y)
        #     pts.append({"x": x, "y": y})

        return sketch_name, pts

    def train(self):

        for _ in range(self.max_episodes):

            sketch_name, pts = self.reset()
            done = False
            reward = 0.0
            steps = 0

            while steps < self.max_steps and done is False:

                if steps == 0:
                    for pt in pts:
                        self.client.add_point(sketch_name, pt)
                else:
                    for pt in pts:
                        self.client.add_point(sketch_name, pt, transform="world")
                r = self.client.close_profile(sketch_name)

                response_json = r.json()
                response_data = response_json["data"]

                keys = list(response_data["profiles"].keys())
                profile_id = random.choice(keys)
                distance = random.uniform(self.low_dist , self.high_dist)
                
                if steps == 0:
                    r = self.client.add_extrude(sketch_name, profile_id, distance, "NewBodyFeatureOperation")
                    print("New body is created")

                else:
                    if distance >= 0:
                       r = self.client.add_extrude(sketch_name, profile_id, distance, "JoinFeatureOperation") 
                    else: 
                       r = self.client.add_extrude(sketch_name, profile_id, distance, "CutFeatureOperation")  

                # Pick a random face for the next sketch
                response_json = r.json()
                
                try:
                    response_data = response_json["data"]

                    faces = response_data["faces"]
                    random_face = random.choice(faces)
                    # print(random_face)

                    # Create a second sketch on a random face
                    r = self.client.add_sketch(random_face["face_id"])
                    response_json = r.json()
                    
                    sketch_name = response_json["data"]["sketch_name"]

                    vertices = random_face["vertices"]
                    constraint = self._cal_constraint(vertices) 
                    pts = self._draw_rect(constraint)

                    # num_points = random.randint(self.min_points, self.max_points)
                    # pts = []
                    # for _ in range(num_points):
                    #     x = random.uniform(self.low_x, self.high_x)
                    #     y = random.uniform(self.low_y, self.high_y)
                    #     pts.append({"x": x, "y": y})

                    steps += 1
                
                except KeyError:
                    done = True

    def _draw_rect(self, constraint):

        pts = []

        w = random.uniform(self.low_width, self.high_width)
        h = random.uniform(self.low_height, self.high_height)

        if isinstance(constraint[0], list) is False: 
            x = constraint[0]
            y = random.uniform(constraint[1][0], constraint[1][1])
            z = random.uniform(constraint[2][0], constraint[2][1])
        
            pts = [
                {"x": x, "y": y, "z": z},
                {"x": x, "y": y, "z": z+h},
                {"x": x, "y": y+w, "z": z+h},
                {"x": x, "y": y+w, "z": z}
            ]

        elif isinstance(constraint[1], list) is False: 
            x = random.uniform(constraint[0][0], constraint[0][1])
            y = constraint[1]
            z = random.uniform(constraint[2][0], constraint[2][1])
        
            pts = [
                {"x": x, "y": y, "z": z},
                {"x": x, "y": y, "z": z+h},
                {"x": x+w, "y": y, "z": z+h},
                {"x": x+w, "y": y, "z": z}
            ]

        elif isinstance(constraint[2], list) is False: 
            x = random.uniform(constraint[0][0], constraint[0][1])
            y = random.uniform(constraint[1][0], constraint[1][1])
            z = constraint[2]
        
            pts = [
                {"x": x, "y": y, "z": z},
                {"x": x, "y": y+h, "z": z},
                {"x": x+w, "y": y+h, "z": z},
                {"x": x+w, "y": y, "z": z}
            ]

        return pts

    def _cal_constraint(self, vertices):

        x = []
        y = []
        z = []
        for vertex in vertices:
            x.append(round(vertex["x"], 4))
            y.append(round(vertex["y"], 4))
            z.append(round(vertex["z"], 4))    
        
        x_min = min(x)
        x_max = max(x)

        y_min = min(y)
        y_max = max(y)

        z_min = min(z)
        z_max = max(z)

        if x_min == x_max:
            return [x_min, [y_min, y_max], [z_min, z_max]]
        elif y_min == y_max:
            return [[x_min, x_max], y_min, [z_min, z_max]]
        elif z_min == z_max:
            return [[x_min, x_max], [y_min, y_max], z_min]

if __name__ == "__main__":

    config = {
        "max_episodes": 10,
        "max_steps": 10,
    }

    trainer = RandomAgent(config)    
    trainer.train()