"""

Test utility for Randomized Reconstruction Commands 

"""
import unittest
import requests
import sys
import os
import importlib
from pathlib import Path

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)
import fusion_360_client
importlib.reload(fusion_360_client)
from fusion_360_client import Fusion360Client

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080

class TestFusion360RandomizedReconstruction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")
        cls.data_dir = Path(__file__).parent.parent / "d7"
        cls.void_data_dir = Path(__file__).parent.parent / "void"
        cls.split_file = Path(__file__).parent.parent / "train_test.json"
        cls.void_split_file = Path(__file__).parent.parent / "void.json"
        cls.distributions_json = Path(__file__).parent.parent / "d7_distributions.json"
        cls.distributions_training_only_json = Path(__file__).parent.parent / "d7_training_distributions.json"

    def test_sample_design(self):
        # Sample the whole dataset
        r = self.client.sample_design(self.data_dir, filter=False)
        # Sample the training data
        r = self.client.sample_design(self.data_dir, filter=True, split_file=self.split_file)

    def test_sample_design_invalid_data_dir(self):
        # Sample from a non-existent directory 
        r = self.client.sample_design(self.void_data_dir, filter=False)
        # Sample from a non-existent directory with the split file 
        r = self.client.sample_design(self.void_data_dir, filter=True, split_file=self.split_file)
        # Sample from a non-existent string 
        r = self.client.sample_design("random_data_dir", filter=False)

    def test_sample_design_invalid_split_file(self):
        # the split file is void
        r = self.client.sample_design(self.data_dir, filter=True, split_file=self.void_split_file)

    def test_get_distributions_from_dataset(self):
        import json
        # distributions of the whole dataset
        r = self.client.get_distributions_from_dataset(self.data_dir, filter=False)
        with open('d7_distributions.json', 'w') as outfile:
            json.dump(r, outfile)
        # distributions of the training dataset
        r = self.client.get_distributions_from_dataset(self.data_dir, filter=True, split_file=self.split_file)
        with open('d7_training_distributions.json', 'w') as outfile:
            json.dump(r, outfile)

    def test_get_distributions_from_json(self):
        # distributions of the whole dataset
        r = self.client.get_distributions_from_json(self.distributions_json)
        # distributions of the training dataset
        r = self.client.get_distributions_from_json(self.distributions_training_only_json)
        # invalid input file
        r = self.client.get_distributions_from_json("void")

    def test_distribution_sampling(self):
        # test invalid distributions
        distributions = {"invalid": "testing"}
        r = self.client.distribution_sampling(distributions)
        # sample all parameters
        distributions = self.client.get_distributions_from_json(self.distributions_training_only_json)
        r = self.client.distribution_sampling(distributions)
        # test invalid parameters
        r = self.client.distribution_sampling(distributions, ["invalid"])
        # sample a list of selected parameters
        r = self.client.distribution_sampling(distributions, ["num_faces", "num_bodies"])
    
    def test_sample_sketch(self):
        json_data, _ = self.client.sample_design(self.data_dir, filter=True, split_file=self.split_file)
        # test invlid sampling type
        r = self.client.sample_sketch(json_data, "invalid")
        # random sampling 
        r = self.client.sample_sketch(json_data, sampling_type = "random")
        # deterministic sampling
        r = self.client.sample_sketch(json_data, sampling_type = "deterministic")
        # distributive sampling
        distributions = self.client.get_distributions_from_json(self.distributions_training_only_json)
        r = self.client.sample_sketch(json_data, sampling_type = "distributive", area_distribution=distributions["sketch_areas"])
        # test invalid area distribution
        r = self.client.sample_sketch(json_data, sampling_type = "distributive", area_distribution=["invalid"])

    def test_sample_profiles(self):
        json_data, _ = self.client.sample_design(self.data_dir, filter=True, split_file=self.split_file)
        sketch_data = self.client.sample_sketch(json_data, sampling_type = "random")
        # test invalid sketch data
        r = self.client.sample_profiles({"data":"invalid"}, max_number_profiles = 1, sampling_type = "random")
        # test invalid max number of profiles
        r = self.client.sample_profiles(sketch_data, max_number_profiles = -1, sampling_type = "random")
        # random sampling
        r = self.client.sample_profiles(sketch_data, max_number_profiles = 2, sampling_type = "random")
        # deterministic sampling
        r = self.client.sample_profiles(sketch_data, max_number_profiles = 2, sampling_type = "deterministic")
        # distributive sampling
        distributions = self.client.get_distributions_from_json(self.distributions_training_only_json)
        r = self.client.sample_sketch(json_data, sampling_type = "distributive", area_distribution=distributions["profile_areas"])
        # test invalid area distribution
        r = self.client.sample_sketch(json_data, sampling_type = "distributive", area_distribution=["invalid"])

if __name__ == "__main__":
    unittest.main()