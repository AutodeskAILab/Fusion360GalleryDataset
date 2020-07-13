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

        self.min_points = 3
        self.max_points = 5

        self.low_x = -5
        self.high_x = 5
        self.low_y = -5
        self.high_y = 5

        self.low_dist = -2
        self.high_dist = 2

        self.reset()


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
        
        num_points = random.randint(self.min_points, self.max_points)
        pts = []
        for _ in range(num_points):
            x = random.uniform(self.low_x, self.high_x)
            y = random.uniform(self.low_y, self.high_y)
            pts.append({"x": x, "y": y})

        return sketch_name, num_points, pts

    def train(self):

        for _ in range(self.max_episodes):

            sketch_name, num_points, pts = self.reset()
            done = False
            reward = 0.0
            steps = 0

            while steps < self.max_steps and done is False:

                for pt in pts:
                    self.client.add_point(sketch_name, pt)
                r = self.client.close_profile(sketch_name)

                response_json = r.json()
                response_data = response_json["data"]

                keys = list(response_data["profiles"].keys())
                # profile_id = random.choice(keys)
                profile_id = next(iter(response_data["profiles"]))
                distance = random.uniform(self.low_dist , self.high_dist)
                
                if steps == 0:
                    r = self.client.add_extrude(sketch_name, profile_id, distance, "NewBodyFeatureOperation")

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
                    # Create a second sketch on a random face
                    r = self.client.add_sketch(random_face["face_id"])
                    response_json = r.json()
                    
                    sketch_name = response_json["data"]["sketch_name"]

                    num_points = random.randint(self.min_points, self.max_points)
                    pts = []
                    for _ in range(num_points):
                        x = random.uniform(self.low_x, self.high_x)
                        y = random.uniform(self.low_y, self.high_y)
                        pts.append({"x": x, "y": y})

                    steps += 1
                
                except KeyError:
                    done = True

if __name__ == "__main__":

    config = {
        "max_episodes": 100,
        "max_steps": 10,
    }

    trainer = RandomAgent(config)    
    trainer.train()