from pathlib import Path
import sys
import os
import json
import random
import time
from fusion_360_client import Fusion360Client

class CouchEnv():

	def __init__(self):
		
		HOST_NAME = "127.0.0.1"
		PORT_NUMBER = 8080
		current_dir = Path(__file__).resolve().parent
		root_dir = current_dir.parent
		data_dir = root_dir / "data"
		output_dir = data_dir / "output"
		if not output_dir.exists():
			output_dir.mkdir()

		hex_design_json_file = data_dir / "Couch.json"
		with open(hex_design_json_file) as file_handle:
			hex_design_json_data = json.load(file_handle)

		self.timeline = hex_design_json_data["timeline"]
		self.entities = hex_design_json_data["entities"]
		self.sketches = {}

		# SETUP
		# Create the client class to interact with the server
		self.client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")

		self.action_space = [0, 1, 2, 3]

	def step(self, action):
		entity_key = self.timeline[action]["entity"]
		entity = self.entities[entity_key]
		if entity["type"] == "Sketch":
			self.sketches[entity_key] = self.add_sketch(self.client, entity, entity_key)
		elif entity["type"] == "ExtrudeFeature":
			self.add_extrude_feature(self.client, entity, entity_key, self.sketches)

	def reset(self):
		r = self.client.clear()
		response_data = r.json()
		print(f"[{r.status_code}] Response: {response_data['message']}")

	def sample_action(self):
		return random.choice(self.action_space)

	def add_sketch(self, client, sketch, sketch_id):
		"""Add a sketch to the design"""
		# First we need a plane to sketch on
		ref_plane = sketch["reference_plane"]
		ref_plane_type = ref_plane["type"]
		# Default to making a sketch on the XY plane
		sketch_plane = "XY"
		if ref_plane_type == "ConstructionPlane":
			# Use the name as a reference to the plane axis
			sketch_plane = ref_plane["name"]
		elif ref_plane_type == "BRepFace":
			# Identify the face by a point that sits on it
			sketch_plane = ref_plane["point_on_face"]
		r = client.add_sketch(sketch_plane)
		# Get the sketch name back
		response_json = r.json()
		print(response_json)
		sketch_name = response_json["data"]["sketch_name"]
		profile_ids = self.add_profiles(client, sketch_name, sketch)
		return {
			"sketch_name": sketch_name,
			"profile_ids": profile_ids
		}

	def add_profiles(self, client, sketch_name, sketch):
		"""Add the sketch profiles to the design"""
		profiles = sketch["profiles"]
		original_curves = sketch["curves"]
		transform = sketch["transform"]
		profile_ids = {}
		response_json = None
		for original_profile_id, profile in profiles.items():
			for loop in profile["loops"]:
				for curve in loop["profile_curves"]:
					if curve["type"] != "Line3D":
						print(f"Warning: Unsupported curve type - {curve['type']}")
						continue
					# Skip over curves that are construction geometry
					curve_id = curve["curve"]
					curve_construction_geom = original_curves[curve_id]["construction_geom"]
					if curve_construction_geom:
						continue
					# We have to send the sketch transform here
					# due to the way Fusion saves out data from designs
					r = client.add_line(sketch_name, curve["start_point"], curve["end_point"], transform)
					response_json = r.json()
			# Look at the response and add profiles to the lookup dict
			# mapping between the original uuids and the profiles
			response_data = response_json["data"]
			for re_profile in response_data["profiles"]:
				profile_ids[original_profile_id] = re_profile
				# Note we make a silly assumption that its always the first
				# profile we use, so we return early here
				# when there could be many profiles in a sketch
				return profile_ids

	def add_extrude_feature(self, client, extrude_feature, extrude_feature_id, sketches):
		"""Add an extrude feature to the design"""
		# We only handle a single profile
		original_profile_id = extrude_feature["profiles"][0]["profile"]
		original_sketch_id = extrude_feature["profiles"][0]["sketch"]
		# Use the original ids to find the new ids
		sketch_name = sketches[original_sketch_id]["sketch_name"]
		profile_id = sketches[original_sketch_id]["profile_ids"][original_profile_id]
		# Pull out the other extrude parameters
		distance = extrude_feature["extent_one"]["distance"]["value"]
		operation = extrude_feature["operation"]
		# Add the extrude
		r = client.add_extrude(sketch_name, profile_id, distance, operation)
		response_json = r.json()
		response_data = response_json["data"]
		print("Response from add_extrude()", response_data)


class RandomAgent():
	"""Policy that takes random actions and never learns."""
	def __init__(self, env, config):
		self.env = env
		self.config = config

	def train(self):

		rewards = []
		steps = 0

		for _ in range(self.config["max_episodes"]):

			# obs = self.env.reset()
			self.env.reset()
			done = False
			reward = 0.0
			
			while not done:
				action = self.env.sample_action()
				self.env.step(action)
				# obs, r, done, info = self.env.step(action)
				#reward += r
				steps += 1
				# rewards.append(reward)
				time.sleep(1)
			
			# return {
			# 	"episode_reward_mean": np.mean(rewards),
			# 	"timesteps_this_iter": steps,
			# }

if __name__ == "__main__":

	couch = CouchEnv()
	# print(type(couch.timeline))
	# print(couch.entities)
	trainer = RandomAgent(env=couch, config={"max_episodes": 10})
	# result = trainer.train()
	trainer.train()