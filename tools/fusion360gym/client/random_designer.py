""""
A random designer using reconstruct_sketch() and add_extrude()
to generate 3D models from real-world sketches
"""

"""
to-do:
1. expand sample data

2. force to have at least two steps

3. distribution on sketch plane

4. crash handling
"""

from pathlib import Path
import sys
import os
from os.path import isfile, join
import json
import random
import time
import math
import numpy as np
from fusion_360_client import Fusion360Client

# lib for random designer 
import designer_utilities as designer

# Before running ensure the Fusion360Server is running
# and configured with the same host name and port number
HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080

TOTAL_EPISODES = 1

MIN_AREA = 10
MAX_AREA = 500
EXTRUDE_LIMIT = 3
TRANSLATE_NOISE = 1

RECONSTRUCTION_DATA_PATH = "random_designer_data" # to-do: need to change to training data
GENERATED_DATA_PATH = "generated_design"

# face count distribution
FACE_COUNTS = [821, 2595, 1950, 1038, 608, 378, 319, 184, 135, 90, 70, 52, 41, 35, 27, 27, 14, 19, 9, 17, 11, 18, 19, 8, 10]
FACES =  [4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56, 60, 64, 68, 72, 76, 80, 84, 88, 92, 96, 100]
FACE_PROBS = []
for count in FACE_COUNTS:
	FACE_PROBS.append(count / sum(FACE_COUNTS))

# sketch place distribution
# to-do: add real distribution later
SKETCH_PLANE = random.choice(["XY", "XZ", "YZ"])

def main():
	# initialize client 
	client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")

	# assign path
	current_dir = Path(__file__).resolve().parent
	data_dir = current_dir / RECONSTRUCTION_DATA_PATH
	generated_dir = current_dir / GENERATED_DATA_PATH
	
	new_body = False
	episode = 0
	
	while episode < TOTAL_EPISODES:
		client.clear()

		# sample the target number of faces for this design  
		face_target = np.random.choice(FACES, 1, p=FACE_PROBS)[0]
		print("target faces: {}".format(face_target))

				
		# pick up a random json file from a folder
		json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
		json_file_dir = data_dir / random.choice(json_files)
		# retrieve the json in case we need to investigate it 
		print("base sketch：{}".format(json_file_dir))

		# load a single json file for debug
		# json_file_dir = current_dir / "sample_data/demo_01.json"

		# multiple extrudes from one sketch may cause the merged-face issue
		# to result in regraph fail
		# json_file_dir = current_dir / "random_designer_data/60295_e0b2e08b_0000.json"

		# NoneType' object has no attribute 'attributes
		# random_designer_data/146888_62f0c3fe_0001.json

		with open(json_file_dir) as file_handle:
			json_data = json.load(file_handle)
		
		# traverse all the sketches
		sketches = designer.traverse_sketches(json_data)
		# skip if the json file doesn't contain sketches 		
		if len(sketches) == 0:
			continue

		# pick the sketch that has the largest area
		sketch, sketch_name, average_area, sketch_area = designer.largest_area(sketches)
		if sketch is None:
			continue
		# print("average area: {}".format(average_area))
		# print("max area: {}".format(max_area))
		
		# filter out designs are too larger 
		if sketch_area > MAX_AREA or sketch_area < MIN_AREA:
			print("Invalid area")
			continue

		# calculate the centroid of the sketch
		sketch_centroid = designer.calculate_sketch_centroid(sketch)
		# print("base sketch centroid: {}".format(sketch_centroid))
		
		# translate the sketch to the center
		if SKETCH_PLANE == "XY":
			translate = {"x": -sketch_centroid["x"], "y": -sketch_centroid["y"], "z": 0}
		elif SKETCH_PLANE == "XZ":
			translate = {"x": -sketch_centroid["x"], "y": 0, "z": -sketch_centroid["z"]}
		elif SKETCH_PLANE == "YZ":
			translate = {"x": 0, "y": -sketch_centroid["y"], "z": -sketch_centroid["z"]}
		scale = {"x": 1, "y": 1, "z": 1}		

		# reconsturct the based sketch
		r = client.reconstruct_sketch(json_data, sketch_name, sketch_plane=SKETCH_PLANE, scale=scale, translate=translate)
		
		response_data = r.json()
		if response_data["status"] == 200:
			print("sketches are reconstructed")
		elif response_data["status"] == 500:
			print(response_data["message"])

		# extrude profiles 
		if "data" in response_data and "profiles" in response_data["data"]:
			profiles = response_data["data"]["profiles"]
			sketch_name = response_data["data"]["sketch_name"]

			average_area = designer.calculate_average_area(profiles)
			
			bases_faces = []
			for profile_id in profiles:
				if math.ceil(profiles[profile_id]["properties"]["area"]) >= math.ceil(average_area):
					if not new_body: 
						r = client.add_extrude(sketch_name, profile_id, 
												random.uniform(0, EXTRUDE_LIMIT),
												"NewBodyFeatureOperation")
						new_body = True
					else:
						r = client.add_extrude(sketch_name, profile_id, 
							random.uniform(0, EXTRUDE_LIMIT),
							"JoinFeatureOperation")

					response_data = r.json()
					if response_data["status"] != 500:
						bases_faces.append(response_data)
		else:
			continue
		
		# to-do: the way to calculate the current face might be problematic 
		current_faces = 0
		for data in bases_faces:
			current_faces += len(data["data"]["faces"])
		print("Current faces: {}".format(current_faces))

		# start the sub-sketches 
		while current_faces < face_target:

			# select the last face (usually the one on the top) to draw sub-sketch
			data = np.random.choice(bases_faces, 1)[0]
			faces = data["data"]["faces"]
			sketch_plane = faces[-1]["face_id"]
			
			# pick up a random json file from a folder
			json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
			json_file_dir = data_dir / random.choice(json_files)
			# testing json file
			# json_file_dir = current_dir / "sample_data/Z0HexagonCutJoin_RootComponent.json"
			
			with open(json_file_dir) as file_handle:
				json_data = json.load(file_handle)
			# retrieve the json in case we need to investigate it 
			print(json_file_dir)
			
			sketches = designer.traverse_sketches(json_data)
			if len(sketches) == 0:
				continue
			
			sketch = np.random.choice(sketches, 1)[0]
			sketch_name = sketch["name"]   
			sketch_centroid = designer.calculate_sketch_centroid(sketch)
			sketch_average_area = designer.calculate_average_area(sketch["profiles"])
			# print(sketch_centroid)
			
			scale = {"x": 1, "y": 1, "z": 1}
			if(sketch_average_area > average_area * 2):
				resize_factor = math.ceil(sketch_average_area / average_area)
				scale =  {"x": 1/resize_factor, "y": 1/resize_factor, "z": 1/resize_factor}
			translate = {"x": -sketch_centroid["x"] + random.uniform(-TRANSLATE_NOISE, TRANSLATE_NOISE), 
							"y": -sketch_centroid["y"] + random.uniform(-TRANSLATE_NOISE, TRANSLATE_NOISE), 
							"z": 0}
			
			r = client.reconstruct_sketch(json_data, sketch_name, sketch_plane=sketch_plane, scale=scale, translate=translate)

			# extrude profiles 
			if "data" in r.json() and "profiles" in r.json()["data"]:
				response_data = r.json()["data"]
				profiles = response_data["profiles"]
				sketch_name = response_data["sketch_name"]
				
				# extrude all profiles
				# for profile_id in profiles:
				#     r = client.add_extrude(sketch_name, profile_id, random.uniform(0, EXTRUDE_LIMIT/2), "JoinFeatureOperation")

				# extrude a random profile
				profile_id = random.choice(list(profiles.keys()))
				r = client.add_extrude(sketch_name, profile_id, random.uniform(0, EXTRUDE_LIMIT/2), "JoinFeatureOperation")

				# update the current faces
				for data in bases_faces:
					current_faces += len(data["data"]["faces"])
				print("Current faces: {}".format(current_faces))
		
		# save graph 
		json_file_dir = generated_dir
		json_file = str(episode) + ".json"
		r = client.graph(json_file, json_file_dir, format="PerFace")
		if r.status_code == 500:
			print(r.json()["message"])
		else:
			# save f3d
			f3d_file = str(episode) + ".f3d"
			f3d_file_dir = generated_dir / f3d_file
			client.brep(f3d_file_dir)
			episode += 1

		print("current episode: {}".format(episode))

if __name__ == "__main__":
	main() 