import time
import json
from pathlib import Path


class Log:

    def __init__(self, env, log_dir):
        self.env = env
        self.current_dir = Path(__file__).resolve().parent
        if log_dir is not None:
            self.log_dir = log_dir
        else:
            self.log_dir = Path(__file__).resolve().parent / "log"
            if not self.log_dir.exists():
                self.log_dir.mkdir()
        self.log_data = []

    def set_target(self, target_file):
        """Set the target file so the log can be named after it"""
        self.target_file = target_file
        self.log_data = []
        # Create a log folder for this file
        # time_stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
        self.log_file_dir = self.log_dir / self.target_file.stem
        if not self.log_file_dir.exists():
            self.log_file_dir.mkdir()
        self.log_file = self.log_file_dir / f"{self.target_file.stem}_log.json"

    def log(self, data, screenshot=False):
        """Log data to the log array"""
        if screenshot:
            if isinstance(data, dict):
                file_name = f"Screenshot_{data['used_budget']:04}.png"
                file = self.log_file_dir / file_name
            else:
                time_stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
                file = self.log_file_dir / f"Screenshot_{time_stamp}.png"
            result = self.env.screenshot(file)
            if isinstance(data, dict):
                data["screenshot"] = file.name
        if isinstance(data, dict):
            data["time"] = time.time()
        self.log_data.append(data)
        self.save()

    def save(self):
        """Save out a log of the search sequence"""
        if (self.log_data is not None and
                len(self.log_data) > 0 and
                self.log_file is not None):
            with open(self.log_file, "w", encoding="utf8") as f:
                json.dump(self.log_data, f, indent=4)
