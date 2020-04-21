import adsk.core
import adsk.fusion
import traceback
import tempfile
import os

from .sketch_extrude_importer import SketchExtrudeImporter


class CommandRunner():

    def __init__(self):
        self.logger = None
        self.app = adsk.core.Application.get()
        self.last_command = ""

    def set_logger(self, logger):
        self.logger = logger

    def run_command(self, command, data=None):
        """Run a command and route it to the right method"""
        self.last_command = command
        result = None
        if command == "ping":
            result = self.ping()
        elif command == "reconstruct":
            result = self.reconstruct(data)
        elif command == "clear":
            result = self.clear()
        elif command == "mesh":
            result = self.mesh()
        # Update the UI
        adsk.doEvents()
        return result
    
    def ping(self):
        """Ping for debugging"""
        return self.__return_success()

    def reconstruct(self, data):
        """Reconstruct a design from the provided json data"""
        try:
            importer = SketchExtrudeImporter(data)
            importer.reconstruct()
            return self.__return_success()
        except Exception as ex:
            return self.__return_exception(ex)

    def clear(self):
        """Clear (i.e. close) all open designs in Fusion"""
        try:
            for doc in self.app.documents:
                # Save without closing
                doc.close(False)
            return self.__return_success()
        except Exception as ex:
            return self.__return_exception(ex)
    
    def mesh(self):
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        try:
            temp_stl = tempfile.NamedTemporaryFile(suffix=".stl")
            temp_stl.close()
            stl_export_options = design.exportManager.createSTLExportOptions(design.rootComponent, temp_stl.name)
            stl_export_options.sendToPrintUtility = False
            export_result = design.exportManager.execute(stl_export_options)
            stl_exists = os.path.exists(temp_stl.name)
            if export_result and stl_exists:
                self.logger.log_text(f"Mesh temp file written to: {temp_stl.name}")
                return self.__return_success(temp_stl.name)
            else:
                return self.__return_failure(".stl export failure")
        except Exception as ex:
            return self.__return_exception(ex)

    def __return_success(self, binary_file=None):
        message = f"Success processing {self.last_command} command"
        return 200, message, binary_file

    def __return_failure(self, reason):
        message = f"Failed processing {self.last_command} command due to {reason}"
        return 500, message, None

    def __return_exception(self, ex):
        message = f"""Error processing {self.last_command} command\n
                      Exception of type {type(ex)} with args: {ex.args}\n
                      {traceback.format_exc()}"""
        return 500, message, None

        
