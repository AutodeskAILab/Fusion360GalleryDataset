import traceback
import json
import os
import sys
import time
from pathlib import Path
import glob
from importlib import reload

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json_action_compiler
reload(json_action_compiler)


from json_action_compiler import JsonActionCompiler
from action_executor_freecad import ActionExecutorFreeCAD

# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

def run(context):
    data_path = Path(os.path.join(os.path.dirname(__file__),'..', '..', 'fusion360gym', 'data'))

    # Get all the files in the data folder
    json_files = [f for f in data_path.glob("**/*.json")]
    json_count = len(json_files)

    for i, json_file in enumerate(json_files, start=1):

        # i=5: hexagon
        # i=3: couch
        # i=2: single extrude

        if i == 3:
            print(f"[{i}/{json_count}] {json_file}")

            compiler = JsonActionCompiler(json_file)
            compiler.parse()

            tree = compiler.getTree()
            actions = compiler.getActions()

            for act in actions:
                print(act)

            # use freecad excecutor to turn actions to model
            constructor = ActionExecutorFreeCAD(actions)
            constructor.traverse_actions()


run(None)