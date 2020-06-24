import traceback
import json
import os
import sys
import time
from pathlib import Path
import glob

from json_action_compiler import JsonActionCompiler


def run():
    data_path = Path(os.path.join(os.path.dirname(__file__), 'data'))

    # Get all the files in the data folder
    json_files = [f for f in data_path.glob("**/*.json")]
    json_count = len(json_files)

    for i, json_file in enumerate(json_files, start=1):
        print(f"[{i}/{json_count}] {json_file}")

        compiler = JsonActionCompiler(json_file)
        compiler.parse()

run()
