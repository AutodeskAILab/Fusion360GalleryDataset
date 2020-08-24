"""

Base Command Class

"""

import adsk.core


class CommandBase():

    def __init__(self, runner):
        self.runner = runner
        self.logger = None
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.state = {}

    def set_logger(self, logger):
        self.logger = logger

    def clear(self):
        """Clear the state"""
        self.state = {}

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
            return "file not specified", None
        suffix = Path(data["file"]).suffix
        if suffix not in valid_formats:
            return "invalid file extension specified", None
        return None, suffix
