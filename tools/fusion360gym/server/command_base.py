"""

Base Command Class

"""

import adsk.core
from pathlib import Path
import tempfile


class CommandBase():

    def __init__(self, runner, design_state):
        self.runner = runner
        self.design_state = design_state
        self.logger = None
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.state = {}

    def set_logger(self, logger):
        self.logger = logger

    def clear(self):
        """Clear the state"""
        self.state = {}
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)

    def get_temp_file(self, file, dest_dir=None):
        """Return a file with a given name in a temp directory"""
        if dest_dir is None:
            dest_dir = Path(tempfile.mkdtemp())
        # Make the dir if we need to
        if not dest_dir.exists():
            dest_dir.mkdir(parents=True)

        temp_file = dest_dir / file
        return temp_file

    def check_file(self, data, valid_formats):
        """Check that the data has a valid file value"""
        if data is None or "file" not in data:
            return None, "file not specified"
        data_file = Path(data["file"])
        if data_file.suffix not in valid_formats:
            return None, "invalid file extension specified"
        return data_file, None
