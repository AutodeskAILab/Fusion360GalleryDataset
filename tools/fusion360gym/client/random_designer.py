from pathlib import Path
from requests.exceptions import ConnectionError
import numpy as np
import math
import random

from random_designer_env import RandomDesignerEnv

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080

RECONSTRUCTION_DATA_PATH = "d7" 
GENERATED_DATA_PATH = "random_designs_10grid"

TOTAL_EPISODES = 499

MIN_AREA = 10
MAX_AREA = 2000

EXTRUDE_LIMIT = 3
TRANSLATE_NOISE = 0
MAX_NUM_FACES_PER_PROFILE = 20
MAX_STEPS = 4

def main():

	current_dir = Path(__file__).resolve().parent
	input_dir = current_dir / RECONSTRUCTION_DATA_PATH
	output_dir = current_dir / GENERATED_DATA_PATH

	random_designer = RandomDesignerEnv(host=HOST_NAME, port=PORT_NUMBER, extrude_limit=EXTRUDE_LIMIT)

	new_body = False
	episode = 0

	while episode < TOTAL_EPISODES:

		try:

			current_num_faces = 0

			# setup 
			random_designer.client.clear()
			target_face, sketch_plane = random_designer.setup_from_distributions()

			# pick up a random json file
			json_data, json_file_dir = random_designer.select_json(input_dir)

			# retrieve the json in case we need to investigate it 
			print("The base sketch is：{}\n".format(json_file_dir))

			# traverse all the sketches from the json data
			sketches = random_designer.traverse_sketches(json_data)
			# skip if the json file doesn't contain sketches 		
			if len(sketches) == 0:
				continue

			# pick the sketch that has the largest area
			sketch, sketch_name, average_area, sketch_area = random_designer.largest_area(sketches)
			if sketch is None:
				continue
			# print("average area: {}".format(average_area))
			# print("max area: {}".format(max_area))
			
			# filter out designs are too larger 
			if sketch_area > MAX_AREA or sketch_area < MIN_AREA:
				print("Invalid area\n")
				continue

			# calculate the centroid of the sketch
			sketch_centroid = random_designer.calculate_sketch_centroid(sketch)
			# print("base sketch centroid: {}".format(sketch_centroid))
			
			# translate the sketch to the center
			if sketch_plane == "XY":
				translate = {"x": -sketch_centroid["x"], "y": -sketch_centroid["y"], "z": 0}
			elif sketch_plane == "XZ":
				translate = {"x": -sketch_centroid["x"], "y": 0, "z": -sketch_centroid["z"]}
			elif sketch_plane == "YZ":
				translate = {"x": 0, "y": -sketch_centroid["y"], "z": -sketch_centroid["z"]}
			scale = {"x": 1, "y": 1, "z": 1}		

			# reconsturct the based sketch
			r = random_designer.client.reconstruct_sketch(json_data, sketch_name, sketch_plane=sketch_plane, scale=scale, translate=translate)
			response_data = r.json()
			if response_data["status"] == 500:
				print(response_data["message"])
				continue

			base_faces, num_faces = random_designer.extrude_profiles(response_data)
			if base_faces is None or num_faces > MAX_NUM_FACES_PER_PROFILE:
				continue
			current_num_faces += num_faces

			# start the sub-sketches 
			steps = 0
			while current_num_faces < target_face and len(base_faces) > 0 and steps < MAX_STEPS:

				try:
					sketch_plane = random_designer.select_plane(base_faces)
				except ValueError:
					continue

				# pick up a new random json file
				json_data, json_file_dir = random_designer.select_json(input_dir)
				print("The sub-sketch is：{}\n".format(json_file_dir))

				sketches = random_designer.traverse_sketches(json_data)
				if len(sketches) == 0:
					continue
			
				sketch = np.random.choice(sketches, 1)[0]
				sketch_name = sketch["name"]   
				sketch_centroid = random_designer.calculate_sketch_centroid(sketch)
				sketch_average_area = random_designer.calculate_average_area(sketch["profiles"])

				scale = {"x": 1, "y": 1, "z": 1}
				if(sketch_average_area > average_area * 2):
					resize_factor = math.ceil(sketch_average_area / average_area)
					scale =  {"x": 1/resize_factor, "y": 1/resize_factor, "z": 1/resize_factor}
				translate = {"x": -sketch_centroid["x"] + random.uniform(-TRANSLATE_NOISE, TRANSLATE_NOISE), 
								"y": -sketch_centroid["y"] + random.uniform(-TRANSLATE_NOISE, TRANSLATE_NOISE), 
								"z": 0}
				
				r = random_designer.client.reconstruct_sketch(json_data, sketch_name, sketch_plane=sketch_plane, scale=scale, translate=translate)
				response_data = r.json()
				if response_data["status"] == 500:
					print(response_data["message"])

				num_faces = random_designer.extrude_one_profile(response_data)
				if base_faces is None or num_faces > MAX_NUM_FACES_PER_PROFILE:
					continue
				current_num_faces += num_faces

				steps += 1

			# save graph and f3d
			try:
				success = random_designer.save(output_dir)
				if success:
					episode += 1
			except OSError:
				# random_designer.launch_gym()
				continue

		except ConnectionError as ex:
			random_designer.launch_gym()
			continue


if __name__ == "__main__":
	main() 