import unittest
import requests
from pathlib import Path
import sys
import os

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TEST_DIR)
CLIENT_DIR = os.path.join(ROOT_DIR, "client")

# Add the client folder to sys.path
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)
from fusion_360_client import Fusion360Client
sys.path.remove(CLIENT_DIR)

HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080


class TestFusion360Server(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = Fusion360Client(f"http://{HOST_NAME}:{PORT_NUMBER}")
        cls.data_path = Path("data")

    def test_reconstruct(self):
        json_file = self.data_path / "test.json"
        r = self.client.reconstruct(json_file)
        self.assertEqual(r.status_code, 200)

    # params = {
    #     "hello": "world"
    # }  
    # print("Sending get request to Fusion 360...")
    # response = requests.get(url=API_ENDPOINT, params=params) 
    # print("Get Response", response)

    # data = {
    #     "hello": "world"
    # } 
    # print("Sending post request to Fusion 360...")
    # response = requests.post(url=API_ENDPOINT, data=data) 
    # print("Post Response", response)

    @classmethod
    def tearDownClass(cls):
        cls.client.detach()


if __name__ == '__main__':
    unittest.main()
