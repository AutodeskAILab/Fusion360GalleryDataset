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

    def test_get_distributions(self):
        r = self.client.get_distributions(self.data_dir, filter=False)
        print(r)

if __name__ == "__main__":
    unittest.main()