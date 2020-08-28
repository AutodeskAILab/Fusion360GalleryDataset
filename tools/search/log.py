import time
import json
from pathlib import Path


class Log:

    def __init__(self, target_file):
        self.target_file = target_file
        self.current_dir = Path(__file__).resolve().parent
        self.log_dir = Path(__file__).resolve().parent / "log"
        if not self.log_dir.exists():
            self.log_dir.mkdir()
        self.log = []

    def log(self, data):
        self.log.append(data)

    def save_log(self):
        """Save out a log of the search sequence"""
        if self.log is not None and len(self.log) > 0:
            time_stamp = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())
            log_file = self.log_dir / f"{self.target_file.stem}_{time_stamp}_log.json"
            with open(log_file, "w", encoding="utf8") as f:
                json.dump(self.log, f, indent=4)
