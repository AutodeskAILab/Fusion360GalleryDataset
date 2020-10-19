"""

Tests for Randomized Reconstruction Commands

"""
import unittest
import requests
import sys
import os
import importlib
from pathlib import Path
import json

import common_test

# Add the client folder to sys.path
CLIENT_DIR = os.path.join(os.path.dirname(__file__), "..", "client")
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)

from fusion360gym_client import Fusion360GymClient

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080

class TestFusion360GymRandomizedReconstruction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360GymClient(f"http://{HOST_NAME}:{PORT_NUMBER}")

        current_dir = Path(__file__).parent
        test_config_file = current_dir / "test_config.json"
        if not test_config_file.exists():
            print("Error: test_config.json file not found in the test directory")

        with open(test_config_file, encoding="utf8") as f:
            test_config = json.load(f)
        dataset_dir = Path(test_config["dataset_dir"])
        if not dataset_dir.exists():
            print("Error: dataset_dir does not exist")

        cls.data_dir = dataset_dir
        cls.void_data_dir = dataset_dir.parent / "void"
        cls.split_file = dataset_dir.parent / "train_test.json"
        cls.void_split_file = dataset_dir.parent / "void.json"
        cls.distributions_json = dataset_dir.parent / "d7_distributions.json"
        cls.distributions_training_only_json = dataset_dir.parent / "d7_training_distributions.json"

        cls.distribution_categories = [
            "sketch_plane",
            "num_faces",
            "num_extrusions",
            "length_sequences",
            "num_curves",
            "num_bodies",
            "sketch_areas",
            "profile_areas"
        ]

    def test_sample_design(self):
        # Sample the whole dataset
        r = self.client.sample_design(self.data_dir, filter=False)
        self.assertIsInstance(r, list, msg="sample_design response is a list")
        self.assertEqual(len(r), 2, msg="sample_design response has two elements")
        self.assertIsInstance(r[0], dict, msg="sample_design response[0] is a dictionary")
        self.assertIsInstance(r[1], Path, msg="sample_design response[1] is a Path")
        # Sample the training data
        r = self.client.sample_design(self.data_dir, filter=True, split_file=self.split_file)
        self.assertIsInstance(r, list, msg="sample_design response is a list")
        self.assertEqual(len(r), 2, msg="sample_design response has two elements")
        self.assertIsInstance(r[0], dict, msg="sample_design response[0] is a dictionary")
        self.assertIsInstance(r[1], Path, msg="sample_design response[1] is a Path")


    def test_sample_design_invalid_data_dir(self):
        # Sample from a non-existent directory
        r = self.client.sample_design(self.void_data_dir, filter=False)
        self.assertIsNone(r, msg="sample_design response is None")
        # Sample from a non-existent directory with the split file
        r = self.client.sample_design(self.void_data_dir, filter=True, split_file=self.split_file)
        self.assertIsNone(r, msg="sample_design responseis None")
        # Sample from a non-existent string
        r = self.client.sample_design("random_data_dir", filter=False)
        self.assertIsNone(r, msg="sample_design response is None")

    def test_sample_design_invalid_split_file(self):
        # the split file is void
        r = self.client.sample_design(self.data_dir, filter=True, split_file=self.void_split_file)
        self.assertIsNone(r, msg="sample_design response is None")

    def test_get_distributions_from_dataset(self):
        # distributions of the whole dataset
        r = self.client.get_distributions_from_dataset(self.data_dir, filter=False)
        for catergory in self.distribution_categories:
            self.assertIn(catergory, r, msg = catergory + " is in the distributions")
        # distributions of the training dataset
        r = self.client.get_distributions_from_dataset(self.data_dir, filter=True, split_file=self.split_file)
        for catergory in self.distribution_categories:
            self.assertIn(catergory, r, msg = catergory + " is in the distributions")

    def test_get_distributions_from_json(self):
        # distributions of the whole dataset
        r = self.client.get_distributions_from_json(self.distributions_json)
        for catergory in self.distribution_categories:
            self.assertIn(catergory, r, msg = catergory + " is in the distributions")
        # distributions of the training dataset
        r = self.client.get_distributions_from_json(self.distributions_training_only_json)
        for catergory in self.distribution_categories:
            self.assertIn(catergory, r, msg = catergory + " is in the distributions")
        # invalid input file
        r = self.client.get_distributions_from_json("void")
        self.assertIsNone(r, msg="get_distributions_from_json response is None")

    def test_distribution_sampling(self):
        # test invalid distributions
        distributions = {"invalid": "testing"}
        r = self.client.distribution_sampling(distributions)
        self.assertIsNone(r, msg="distribution_sampling response is None")
        # sample all parameters
        distributions = self.client.get_distributions_from_json(self.distributions_training_only_json)
        for catergory in self.distribution_categories:
            self.assertIn(catergory, distributions, msg = catergory + " is in the distributions")
        r = self.client.distribution_sampling(distributions)
        self.assertIsInstance(r, dict, msg="distribution_sampling response is dictionary")
        for catergory in self.distribution_categories:
            self.assertIn(catergory, r, msg = catergory + " is in the parameters")
        # test invalid parameters
        r = self.client.distribution_sampling(distributions, ["invalid"])
        self.assertIsNone(r, msg="distribution_sampling response is None")
        # sample a list of selected parameters
        r = self.client.distribution_sampling(distributions, ["num_faces", "num_bodies"])
        self.assertIsInstance(r, dict, msg="distribution_sampling response is dictionary")
        for catergory in ["num_faces", "num_bodies"]:
            self.assertIn(catergory, r, msg = catergory + " is in the parameters")

    def test_sample_sketch(self):
        json_data, _ = self.client.sample_design(self.data_dir, filter=True, split_file=self.split_file)
        self.assertIsInstance(json_data, dict, msg="sample_design response is json")
        # test invlid sampling type
        r = self.client.sample_sketch(json_data, "invalid")
        self.assertIsNone(r, msg="sample_design response is None")
        # random sampling
        r = self.client.sample_sketch(json_data, sampling_type = "random")
        self.assertIsInstance(r, dict, msg="sample_design response is dictionary")
        self.assertEqual("Sketch", r["type"], msg="sample_sketch response is sketch type")
        # deterministic sampling
        r = self.client.sample_sketch(json_data, sampling_type = "deterministic")
        self.assertIsInstance(r, dict, msg="sample_design response ")
        self.assertEqual("Sketch", r["type"], msg="sample_sketch response is sketch type")
        # distributive sampling
        distributions = self.client.get_distributions_from_json(self.distributions_training_only_json)
        self.assertIn("sketch_areas", distributions, msg = "Sketch areas is in the distributions")
        r = self.client.sample_sketch(json_data, sampling_type = "distributive", area_distribution=distributions["sketch_areas"])
        self.assertIsInstance(r, dict, msg="Sketch is dictionary")
        self.assertEqual("Sketch", r["type"], msg="sample_sketch response is sketch type")
        # test invalid area distribution
        r = self.client.sample_sketch(json_data, sampling_type = "distributive", area_distribution=["invalid"])
        self.assertIsNone(r, msg="sample_sketch response is None")

    def test_sample_profiles(self):
        json_data, _ = self.client.sample_design(self.data_dir, filter=True, split_file=self.split_file)
        self.assertIsInstance(json_data, dict, msg="sample_design response is json")
        sketch_data = self.client.sample_sketch(json_data, sampling_type = "random")
        self.assertIsInstance(sketch_data, dict, msg="sample_sketch response is json")
        self.assertEqual("Sketch", sketch_data["type"], msg="sample_sketch response is sketch type")
        # test invalid sketch data
        r = self.client.sample_profiles({"data":"invalid"}, max_number_profiles = 1, sampling_type = "random")
        self.assertIsNone(r, msg="sample_profiles response is None")
        # test invalid max number of profiles
        r = self.client.sample_profiles(sketch_data, max_number_profiles = -1, sampling_type = "random")
        self.assertIsNone(r, msg="sample_profiles response is None")
        # random sampling
        r = self.client.sample_profiles(sketch_data, max_number_profiles = 2, sampling_type = "random")
        self.assertIsInstance(r, list, msg="sample_profiles response is list")
        self.assertNotEqual(len(r), 0, msg="sample_profiles response has more than 1 element")
        # deterministic sampling
        r = self.client.sample_profiles(sketch_data, max_number_profiles = 2, sampling_type = "deterministic")
        self.assertIsInstance(r, list, msg="sample_profiles response is list")
        self.assertNotEqual(len(r), 0, msg="sample_profiles response has more than 1 element")
        # distributive sampling
        distributions = self.client.get_distributions_from_json(self.distributions_training_only_json)
        r = self.client.sample_profiles(sketch_data, max_number_profiles = 2, sampling_type = "distributive", area_distribution=distributions["profile_areas"])
        self.assertIsInstance(r, list, msg="sample_profiles response is list")
        self.assertNotEqual(len(r), 0, msg="sample_profiles response has more than 1 element")
        # test invalid area distribution
        r = self.client.sample_profiles(sketch_data, max_number_profiles = 2, sampling_type = "distributive", area_distribution=["invalid"])
        self.assertIsNone(r, msg="sample_profiles response is None")

if __name__ == "__main__":
    unittest.main()
