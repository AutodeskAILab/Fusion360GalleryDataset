import os
import sys
from pathlib import Path
import subprocess
import json
import time

# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

from launcher import Launcher


def launch_loop(launcher):
    p = launcher.launch()
    while p.poll() is None:
        time.sleep(1)
    print(f"Fusion crashed with code {p.returncode}, relaunching...")
    launch_loop(launcher)

if __name__ == "__main__":
    launcher = Launcher()
    launch_loop(launcher)
