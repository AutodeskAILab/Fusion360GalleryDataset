import adsk.core
import adsk.fusion

from .sketch_extrude_importer import SketchExtrudeImporter


class CommandRunner():

    def __init__(self, logger):
        self.logger = logger
        self.app = adsk.core.Application.get()
        self.last_command = ""

    def run_command(self, command, data):
        self.last_command = command
        result = None
        if command == "reconstruct":
            result = self.reconstruct(data)
        elif command == "clear":
            result = self.clear()
        # Update the UI
        adsk.doEvents()
        return result

    def reconstruct(self, data):
        """Reconstruct a design from the provided json data"""
        try:
            importer = SketchExtrudeImporter(data)
            importer.reconstruct()
            return __return_success()
        except Exception as ex:
            return __return_exception(ex)

    def clear(self):
        """Clear (i.e. close) all open designs in Fusion"""
        try:
            for doc in self.app.documents:
                # Save without closing
                doc.close(False)
            return __return_success()
        except Exception as ex:
            return __return_exception(ex)

    def __return_success(self):
        message = f"Success processing {self.last_command} command"
        return 200, message

    def __return_exception(self, ex):
        message = f"""Error processing {self.last_command} command\n
                      Exception of type {type(ex)} with args: {ex.args}"""
        return 500, message
