# Fusion 360 Gym Examples
This directory contains a number of examples that demonstrate how to work with the Fusion 360 Gym. 

## Setup
All examples require Fusion 360 to be open with the Fusion 360 Gym sever running. Follow the instructions in the [main readme](../README.md#running) for full setup details.

## Running
For a simple example of how to interact with the server check out [client_example.py](client_example.py).
```
cd /path/to/fusion360gym/examples
python client_example.py
```
This script will output various files to the `tools/test_data/output` directory and you will see Fusion 360 update as it processes requests.