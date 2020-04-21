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
            result = self.mesh(data)
        elif command == "brep":
            result = self.brep(data)            
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
    
    def mesh(self, data):
        """Create a mesh in the given format (currently .stl) and send it back as a binary file"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix=".stl")
            temp_file.close()
            stl_export_options = design.exportManager.createSTLExportOptions(design.rootComponent, temp_file.name)
            stl_export_options.sendToPrintUtility = False
            export_result = design.exportManager.execute(stl_export_options)
            file_exists = os.path.exists(temp_file.name)
            if export_result and file_exists:
                self.logger.log_text(f"Mesh temp file written to: {temp_file.name}")
                return self.__return_success(temp_file.name)
            else:
                return self.__return_failure(".stl export failure")
        except Exception as ex:
            return self.__return_exception(ex)

    def brep(self, data):
        """Create a brep in the given format (currently .step, smt) and send it back as a binary file"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if data is None or "format" not in data:
            return self.__return_failure("format not specified")
        suffix = data["format"]
        valid_formats = [".step", ".smt"]
        if suffix not in valid_formats:
            return self.__return_failure("invalid format specified")
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix=suffix)
            temp_file.close()
            if suffix == ".step":
                export_options = design.exportManager.createSTEPExportOptions(temp_file.name, design.rootComponent)
            elif suffix == ".smt":
                export_options = design.exportManager.createSMTExportOptions(temp_file.name, design.rootComponent)
            export_result = design.exportManager.execute(export_options)
            file_exists = os.path.exists(temp_file.name)
            if export_result and file_exists:
                self.logger.log_text(f"BRep temp file written to: {temp_file.name}")
                return self.__return_success(temp_file.name)
            else:
                return self.__return_failure(f"{suffix} export failure")
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

        
