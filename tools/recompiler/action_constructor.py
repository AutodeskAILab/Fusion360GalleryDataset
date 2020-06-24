"""

Load actions sequence data and reconstructs the geometry in Fusion

"""


import traceback
import json
import os
import sys
import time
import math
from pathlib import Path
import adsk.core
import adsk.fusion

from importlib import reload

# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

# Add the server folder to sys.path
SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "fusion360gym", "server"))
if SERVER_DIR not in sys.path:
    sys.path.append(SERVER_DIR)

from command_runner import CommandRunner


class ActionConstructor():
    def __init__(self, actions):

        if isinstance(actions, list):
            self.actions = actions
        else:
            with open(actions, encoding="utf8") as f:
                self.actions = json.load(f)
    
        self.app = adsk.core.Application.get()
        product = self.app.activeProduct
        self.design = adsk.fusion.Design.cast(product)

    def traverse_actions(self):
        c_runner = CommandRunner()
        name_mapper = {}  # store the data name to fusion name map

        print('self.actions', self.actions)

        for action in self.actions:
            if(action['command'] == "add_sketch"):
                print(action)
                name = action['info']['name']

                d = {
                    'sketch_plane': action['info']['ref']
                }
                r = c_runner.run_command('add_sketch', d)
                name_mapper[name] = r[2]
            
            if(action['command'] == "add_line"):
                print(action)
                d = {
                    'sketch_name': name_mapper[action['info']['sketch']]['sketch_name'],
                    'pt1': action['info']['start'],
                    'pt2': action['info']['end']
                }
                r = c_runner.run_command('add_line', d)

                profiles = list(r[2]['profiles'].keys())

                # we only create single loop sketches
                if len(profiles):
                    name_mapper[action['info']['sketch']]['profile'] = profiles[0]
                print('line info', r)
            
            if(action['command'] == "add_extrude"):
                print(action)
                d = {
                    'sketch_name': name_mapper[action['info']['made_of']]['sketch_name'],
                    'distance': action['info']['distance'],
                    'profile_id': name_mapper[action['info']['made_of']]['profile'],
                    'operation': action['info']['operation']
                }

                r = c_runner.run_command('add_extrude', d)
            
                


            
        

        

    

        # Close the document - Fusion automatically opens a new window after the last one is closed
        # self.app.activeDocument.close(False)


