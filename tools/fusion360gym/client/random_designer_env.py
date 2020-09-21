import os
import random
import json
import numpy as np
import math
import time

from gym_env import GymEnv


class RandomDesignerEnv(GymEnv):

    def __init__(self, host, port, extrude_limit, data_dir, split_file, launch_gym=False):

        self.extrude_limit = extrude_limit
        self.new_body = False
        self.max_base_profiles = 1
        self.train_files = self.get_json_train_files(data_dir, split_file)

        GymEnv.__init__(self, host=host, port=port, launch_gym=launch_gym)

    # return the sketch that has the largest area
    def largest_area(self, sketches):
        max_area = 0
        return_sketch = None
        for sketch in sketches:
            areas = []
            if "profiles" in sketch:
                profiles = sketch["profiles"]
                for profile in profiles:
                    areas.append(profiles[profile]["properties"]["area"])
                sum_area = sum(areas)
                average_area = sum_area / len(areas)
                if sum_area > max_area:
                    max_area = sum_area
                    return_sketch = sketch
        return return_sketch, return_sketch["name"], average_area, max_area

    # return the centroid of a sketch

    def calculate_sketch_centroid(self, sketch):
        profiles = sketch["profiles"]
        # calcuate the centroid of the sketch
        sketch_centroid = {"x": 0, "y": 0, "z": 0}
        for profile in profiles:
            sketch_centroid["x"] += profiles[profile]["properties"]["centroid"]["x"]
            sketch_centroid["y"] += profiles[profile]["properties"]["centroid"]["y"]
            sketch_centroid["z"] += profiles[profile]["properties"]["centroid"]["z"]
        for key in sketch_centroid:
            sketch_centroid[key] /= len(profiles)
        return sketch_centroid

    # calculate average area from profiles

    def calculate_average_area(self, profiles):
        average_area = 0
        for profile_id in profiles:
            average_area += profiles[profile_id]["properties"]["area"]
        return average_area / len(profiles)

    # traverse all the sketches

    def traverse_sketches(self, json_data):
        sketches = []
        timeline = json_data["timeline"]
        entities = json_data["entities"]
        for timeline_object in timeline:
            entity_uuid = timeline_object["entity"]
            entity_index = timeline_object["index"]
            entity = entities[entity_uuid]
            # we only want sketches with profiles
            if entity["type"] == "Sketch" and "profiles" in entity:
                sketches.append(entity)
        return sketches

    # Get a set of just the training set json files"""

    def get_json_train_files(self, data_dir, split_file):
        train_files = []
        with open(split_file, encoding="utf8") as f:
            json_data = json.load(f)
            if "train" not in json_data:
                print("Split file does not have a train set")
            else:
                for train_file_name in json_data["train"]:
                    train_file = data_dir / f"{train_file_name}.json"
                    if not train_file.exists():
                        print(f"Train file {train_file} missing")
                    else:
                        train_files.append(train_file)
        return train_files

    # select a radnom json file from the database

    def select_json(self, data_dir):
        json_file_dir = data_dir / random.choice(self.train_files)
        with open(json_file_dir, encoding="utf8") as file_handle:
            json_data = json.load(file_handle)
        return json_data, json_file_dir

    # select a particular json file from the databse

    def select_specific_json(self, data_dir, file_name):
        json_file_dir = data_dir / file_name
        with open(json_file_dir, encoding="utf8") as file_handle:
            json_data = json.load(file_handle)
        return json_data

    def setup_from_distributions(self):
        # face count distribution
        FACE_COUNTS = [821, 2595, 1950, 1038, 608, 378, 319, 184, 135,
                       90, 70, 52, 41, 35, 27, 27, 14, 19, 9, 17, 11, 18, 19, 8, 10]
        FACES = [4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48,
                 52, 56, 60, 64, 68, 72, 76, 80, 84, 88, 92, 96, 100]
        FACE_PROBS = []
        for count in FACE_COUNTS:
            FACE_PROBS.append(count / sum(FACE_COUNTS))
        target_face = np.random.choice(FACES, 1, p=FACE_PROBS)[0]

        # sketch place distribution
        # to-do: add real distribution later
        sketch_plane = random.choice(["XY", "XZ", "YZ"])

        return target_face, sketch_plane

    def extrude_profiles(self, response_data):
        # extrude profiles
        if "data" in response_data and "profiles" in response_data["data"] and len(response_data["data"]["profiles"]) > 0:
            sketch_name = response_data["data"]["sketch_name"]
            profiles = response_data["data"]["profiles"]
            average_area = self.calculate_average_area(profiles)
            bases_faces = []
            profile_ids = []

            for profile_id in profiles:
                if math.ceil(profiles[profile_id]["properties"]["area"]) >= math.ceil(average_area):
                    profile_ids.append(profile_id)
            # we only extrude a certain number of profiles
            if len(profile_ids) > self.max_base_profiles:
                profile_ids = random.sample(
                    profile_ids, self.max_base_profiles)

            for profile_id in profile_ids:
                if not self.new_body:
                    r = self.client.add_extrude(sketch_name, profile_id, random.uniform(
                        0, self.extrude_limit), "NewBodyFeatureOperation")
                    self.new_body = True
                else:
                    r = self.client.add_extrude(sketch_name, profile_id, random.uniform(
                        0, self.extrude_limit), "JoinFeatureOperation")
                response_data = r.json()
                if response_data["status"] != 500:
                    bases_faces.append(response_data)

            # to-do: the way to calculate the current face might be problematic
            num_faces = 0
            for data in bases_faces:
                num_faces += len(data["data"]["faces"])

            return bases_faces, num_faces
        else:
            return None, None

    def extrude_one_profile(self, response_data):
        # extrude profiles
        if "data" in response_data and "profiles" in response_data["data"]:
            profiles = response_data["data"]["profiles"]
            sketch_name = response_data["data"]["sketch_name"]

            if len(profiles) == 0:
                return 0

            average_area = self.calculate_average_area(profiles)

            profile_ids = []
            for profile_id in profiles:
                if math.ceil(profiles[profile_id]["properties"]["area"]) >= math.ceil(average_area):
                    profile_ids.append(profile_id)
            # we only extrude a certain number of profiles
            if len(profile_ids) > self.max_base_profiles:
                profile_ids = random.sample(
                    profile_ids, self.max_base_profiles)

            profile_id = random.choice(profile_ids)
            r = self.client.add_extrude(sketch_name, profile_id, random.uniform(
                0, self.extrude_limit), "JoinFeatureOperation")

            response_data = r.json()

            # to-do: the way to calculate the current face might be problematic
            if "data" in response_data:
                num_faces = len(response_data["data"]["faces"])
            else:
                num_faces = 0

            return int(num_faces)
        else:
            return 0

    def save(self, output_dir, prefix):
        json_file_dir = output_dir
        file_name = str(prefix) + "-" + str(math.floor(time.time()))
        json_file = file_name + ".json"
        r = self.client.graph(json_file, json_file_dir, format="PerFace")
        if r.status_code == 500:
            print(r.json()["message"])
            return False
        else:
            # save f3d
            f3d_file = file_name + ".f3d"
            f3d_file_dir = output_dir / f3d_file
            self.client.brep(f3d_file_dir)
            print("Data generation success!\n")
            return True

    def select_plane(self, base_faces, base_start_face_used, base_end_face_used):
        # randomly pick an extrude
        data = np.random.choice(base_faces, 1)[0]
        faces = data["data"]["faces"]
        valid_faces = []
        for face in faces:
            # Don't choose a start face is we have used the end face
            if face["location_in_feature"] == "StartFace" and base_end_face_used:
                continue
            # Don't choose an end face if we have used the start face
            if face["location_in_feature"] == "EndFace" and base_start_face_used:
                continue
            if face["surface_type"] != "CylinderSurfaceType":
                valid_faces.append(face)
        face_id = np.random.choice(len(valid_faces), 1)[0]
        sketch_plane = valid_faces[face_id]["face_id"]
        location_in_feature = valid_faces[face_id]["location_in_feature"]
        return sketch_plane, location_in_feature

    # def select_plane(self, base_faces):

    # 	# randomly pick an extrude
    # 	data = np.random.choice(base_faces, 1)[0]
    # 	faces = data["data"]["faces"]
    # 	# pick the start face
    # 	# sketch_plane = faces[0]["face_id"]
    # 	face_id = np.random.choice(len(faces), 1)[0]
    # 	sketch_plane = faces[face_id]["face_id"]

    # 	return sketch_plane, base_faces
