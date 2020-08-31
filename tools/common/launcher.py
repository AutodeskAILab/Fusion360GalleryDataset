"""

Find and launch Fusion 360

"""

import os
import sys
from pathlib import Path
import subprocess
import importlib


class Launcher():

    def __init__(self):
        self.fusion_app = self.find_fusion()
        if self.fusion_app is None:
            print("Error: Fusion 360 could not be found")
        elif not self.fusion_app.exists():
            print(f"Error: Fusion 360 does not exist at {self.fusion_app}")
        else:
            print(f"Fusion 360 found at {self.fusion_app}")

    def launch(self):
        """Opens a new instance of Fusion 360"""
        if self.fusion_app is None:
            print("Error: Fusion 360 could not be found")
            return None
        elif not self.fusion_app.exists():
            print(f"Error: Fusion 360 does not exist at {self.fusion_app}")
            return None
        else:
            fusion_path = str(self.fusion_app.resolve())
            args = []
            if sys.platform == "darwin":
                # -W is to wait for the app to finish
                # -n is to open a new app
                args = ["open", "-W", "-n", fusion_path]
            elif sys.platform == "win32":
                args = [fusion_path]

            print(f"Fusion launching from {fusion_path}")
            # Turn off output from Fusion
            return subprocess.Popen(
                args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def find_fusion(self):
        """Find the Fusion app"""
        if sys.platform == "darwin":
            return self.find_fusion_mac()
        elif sys.platform == "win32":
            return self.find_fusion_windows()

    def find_fusion_mac(self):
        """Find the Fusion app on mac"""
        # Shortcut location that links to the latest version
        user_path = Path(os.path.expanduser("~"))
        fusion_app = user_path / "Library/Application Support/Autodesk/webdeploy/production/Autodesk Fusion 360.app"
        return fusion_app

    def find_fusion_windows(self):
        """Find the Fusion app
            by looking in a windows FusionLauncher.exe.ini file"""
        fusion_launcher = self.find_fusion_launcher()
        if fusion_launcher is None:
            return None
        # FusionLauncher.exe.ini looks like this (encoding is UTF-16):
        # [Launcher]
        # stream = production
        # auid = AutodeskInc.Fusion360
        # cmd = ""C:\path\to\Fusion360.exe""
        # global = False
        with open(fusion_launcher, "r", encoding="utf16") as f:
            lines = f.readlines()
        lines = [x.strip() for x in lines]

        for line in lines:
            if line.startswith("cmd") and "Fusion360.exe" in line:
                pieces = line.split("\"")
                for piece in pieces:
                    if "Fusion360.exe" in piece:
                        return Path(piece)
        return None

    def find_fusion_launcher(self):
        """Find the FusionLauncher.exe.ini file on windows"""
        user_dir = Path(os.environ["LOCALAPPDATA"])
        production_dir = user_dir / "Autodesk/webdeploy/production/"
        production_contents = Path(production_dir).iterdir()
        for item in production_contents:
            if item.is_dir():
                fusion_launcher = item / "FusionLauncher.exe.ini"
                if fusion_launcher.exists():
                    return fusion_launcher
        return None
