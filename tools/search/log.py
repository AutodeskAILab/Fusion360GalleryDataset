import time
import json
from pathlib import Path


class Log:

    def __init__(self):
        self.current_dir = Path(__file__).resolve().parent
        self.log_dir = Path(__file__).resolve().parent / "log"
        if not self.log_dir.exists():
            self.log_dir.mkdir()
        self.log_data = []

    def set_target(self, target_file):
        """Set the target file so the log can be named after it"""
        self.target_file = target_file

    def log(self, data):
        """Log data to the log array"""
        self.log_data.append(data)

    def save(self):
        """Save out a log of the search sequence"""
        if self.log_data is not None and len(self.log_data) > 0:
            time_stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
            log_file = self.log_dir / f"{self.target_file.stem}_{time_stamp}_log.json"
            with open(log_file, "w", encoding="utf8") as f:
                json.dump(self.log_data, f, indent=4)
