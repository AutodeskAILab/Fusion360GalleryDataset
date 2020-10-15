"""

Autmatically run regraph_exporter.py
and handle relaunching Fusion 360 if necessary

Requires regraph_exporter to be set to Run On Startup
inside of Fusion 360

"""

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


def launch_loop(launcher, results_file):
    """Launch Fusion again and again in a loop"""
    p = launcher.launch()
    killing = False

    while p.poll() is None:
        if time_out_reached(results_file):
            if not killing:
                p.kill()
            killing = True
        else:
            time.sleep(1)

    if killing:
        # Update the file to avoid infinite loop
        results_file.touch()
        print(f"Fusion killed after timeout, relaunching...")
    else:
        print(f"Fusion crashed with code {p.returncode}, relaunching...")
    launch_loop(launcher, results_file)


def time_out_reached(results_file):
    """Check for a timeout by
        checking the results file to see if it has been updated"""
    if not results_file.exists():
        return False
    start_time = os.path.getmtime(results_file)
    time_elapsed = time.time() - start_time
    print(f"Time processing current file: {time_elapsed}\r", end="")
    # Wait for this amount of time before killing
    time_out_limit = 15 * 60
    return time_elapsed > time_out_limit


if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent / "testdata"
    output_dir = data_dir / "output"
    # We use the timestamp of this file to check we haven't timed out
    # This file is updated at regular intervals when all is working
    results_file = output_dir / "regraph_results.json"
    if results_file.exists():
        # Touch the file to start the timer
        results_file.touch()

    launcher = Launcher()
    launch_loop(launcher, results_file)
