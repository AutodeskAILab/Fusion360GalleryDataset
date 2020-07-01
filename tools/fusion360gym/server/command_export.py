"""

Export geometry/images/data commands

"""

import adsk.core
import adsk.fusion
import traceback
import tempfile
import shutil
import os
import sys
import importlib
from zipfile import ZipFile
from pathlib import Path


# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "common")
)
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)
import exporter
import view_control
from sketch_extrude_importer import SketchExtrudeImporter


class CommandExport():

    def __init__(self, runner):
        self.runner = runner
        self.logger = None
        self.app = adsk.core.Application.get()

    def set_logger(self, logger):
        self.logger = logger

    def reconstruct(self, data):
        """Reconstruct a design from the provided json data"""
        importer = SketchExtrudeImporter(data)
        importer.reconstruct()
        return self.runner.return_success()

    def mesh(self, data, dest_dir=None):
        """Create a mesh in the given format (either .obj or .stl)
            and send it back as a binary file"""
        error, suffix = self.__check_file(data, [".obj", ".stl"])
        if error is not None:
            return self.runner.return_failure(error)
        temp_file = self.__get_temp_file(data["file"], dest_dir)
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if suffix == ".obj":
            export_result = exporter.export_obj_from_component(
                temp_file, design.rootComponent
            )
        elif suffix == ".stl":
            export_result = exporter.export_stl_from_component(
                temp_file, design.rootComponent
            )
        file_exists = temp_file.exists()
        if export_result and file_exists:
            self.logger.log(f"Mesh temp file written to: {temp_file}")
            return self.runner.return_success(temp_file)
        else:
            return self.runner.return_failure(f"{suffix} export failure")

    def brep(self, data, dest_dir=None):
        """Create a brep in the given format (.step, smt)
            and send it back as a binary file"""
        error, suffix = self.__check_file(data, [".step", ".smt"])
        if error is not None:
            return self.runner.return_failure(error)
        temp_file = self.__get_temp_file(data["file"], dest_dir)
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if suffix == ".step":
            export_result = exporter.export_step_from_component(
                temp_file, design.rootComponent
            )
        elif suffix == ".smt":
            export_result = exporter.export_smt_from_component(
                temp_file, design.rootComponent
            )
        file_exists = temp_file.exists()
        if export_result and file_exists:
            self.logger.log(f"BRep temp file written to: {temp_file}")
            return self.runner.return_success(temp_file)
        else:
            return self.runner.return_failure(f"{suffix} export failure")

    def sketches(self, data, dest_dir=None, use_zip=True):
        """Generate sketches in a given format (e.g. .png)
            and return as a binary zip file"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if data is None or "format" not in data:
            return self.runner.return_failure("format not specified")
        suffix = data["format"]
        valid_formats = [".png", ".dxf"]
        if suffix not in valid_formats:
            return self.runner.return_failure("invalid format specified")
        if suffix == ".png":
            zip_file = self.__export_sketch_pngs(dest_dir, use_zip)
        elif suffix == ".dxf":
            zip_file = self.__export_sketch_dxfs(dest_dir, use_zip)
        return self.runner.return_success(zip_file)

    def commands(self, data):
        """Run a series of commands one after the other"""
        if not isinstance(data, list) or len(data) == 0:
            return self.runner.return_failure("command list not specified")
        # Get a list of the commands to run
        command_list, return_data_count = self.__build_command_list(data)
        if len(command_list) == 0:
            return self.runner.return_failure("no valid commands found")

        if return_data_count > 0:
            # Create a temp directory for the output to go
            dest_dir = Path(tempfile.mkdtemp())
        # Execute the list of commands
        for command_set in command_list:
            command_string = command_set["command_string"]
            self.logger.log(f"Executing {command_string} command")
            if command_string in ["ping", "refresh", "clear"]:
                status, message, return_data = command_set["command"]()
                if status == 500:
                    return status, message, return_data
            elif command_string == "reconstruct":
                if "data" not in command_set:
                    return self.runner.return_failure("missing arguments")
                data = command_set["data"]
                status, message, return_data = command_set["command"](data)
                if status == 500:
                    return status, message, return_data
            elif command_string in ["mesh", "brep"]:
                if "data" not in command_set:
                    return self.runner.return_failure("missing arguments")
                data = command_set["data"]
                status, message, return_data = command_set["command"](
                    data, dest_dir=dest_dir
                )
                if status == 500:
                    return status, message, return_data
            # Commands creating a folder of output
            elif command_string == "sketches":
                if "data" not in command_set:
                    return self.runner.return_failure("missing arguments")
                data = command_set["data"]
                status, message, return_data = command_set["command"](
                    data, dest_dir=dest_dir, use_zip=False
                )
                if status == 500:
                    return status, message, return_data
        # Zip all the files we produced up and pass them back
        if return_data_count > 0:
            zip_file = self.__zip_dir(dest_dir)
            return self.runner.return_success(zip_file)
        else:
            return self.runner.return_success()

    def __build_command_list(self, data):
        """Build the command list to execute"""
        command_list = []
        # Keep track of how many bits of data to return
        return_data_count = 0
        # Build the list of commands to run
        for command_set in data:
            if "command" in command_set:
                command_string = command_set["command"]
                if isinstance(command_string, str):
                    if command_string in ["ping", "refresh", "clear"]:
                        command = getattr(self.runner, command_string)
                    else:
                        command = getattr(self, command_string)
                    if command is not None:
                        # Count how many sets of data we are returning
                        if command_string in ["mesh", "brep", "sketches"]:
                            return_data_count += 1
                        valid_command_set = {
                            "command": command,
                            "command_string": command_string
                        }
                        if "data" in command_set:
                            data = command_set["data"]
                            valid_command_set["data"] = data
                        command_list.append(valid_command_set)
        return command_list, return_data_count

    def __export_sketch_pngs(self, dest_dir=None, use_zip=True):
        """Export all sketches as png files and return a zip file"""
        if dest_dir is None:
            dest_dir = Path(tempfile.mkdtemp())
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Loop over each sketch and export a PNG
        for component in design.allComponents:
            for sketch in component.sketches:
                png_file = dest_dir / f"{sketch.name}.png"
                exporter.export_png_from_sketch(png_file, sketch)
        if use_zip:
            return self.__zip_dir(dest_dir)
        else:
            return dest_dir

    def __export_sketch_dxfs(self, dest_dir=None, use_zip=True):
        """Export all sketches as dxf files and return a zip file"""
        if dest_dir is None:
            dest_dir = Path(tempfile.mkdtemp())
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Then we loop over each sketch and export a DXF
        for component in design.allComponents:
            for sketch in component.sketches:
                try:
                    dxf_file = dest_dir / f"{sketch.name}.dxf"
                    sketch.saveAsDXF(str(dxf_file.resolve()))
                except:
                    # If the sketch is Null then keep on to the next
                    pass
        if use_zip:
            return self.__zip_dir(dest_dir)
        else:
            return dest_dir

    def __zip_dir(self, src_dir, delete_src_dir=True):
        """Create a temp zip file of all the files in a given folder"""
        temp_file_handle, temp_file_path = tempfile.mkstemp(suffix=".zip")
        zip_file = Path(temp_file_path)
        with ZipFile(zip_file, "w") as zip_obj:
            # Iterate over all the files in directory
            for folder_name, subfolders, files in os.walk(src_dir):
                for file in files:
                    # create complete filepath of file in directory
                    file_path = os.path.join(folder_name, file)
                    # Add file to zip
                    zip_obj.write(file_path, file)
            self.logger.log(f"Zip temp file written to: {zip_file.name}")
        if delete_src_dir:
            # Clean up the folder after outselves
            shutil.rmtree(src_dir)
        return zip_file

    def __check_file(self, data, valid_formats):
        """Check that the data has a valid file value"""
        if data is None or "file" not in data:
            return "file not specified"
        suffix = Path(data["file"]).suffix
        if suffix not in valid_formats:
            return "invalid file extension specified"
        return None, suffix

    def __get_temp_file(self, file, dest_dir=None):
        """Return a file with a given name in a temp directory"""
        if dest_dir is None:
            dest_dir = Path(tempfile.mkdtemp())
        # Make the dir if we need to
        if not dest_dir.exists():
            dest_dir.mkdir(parents=True)

        temp_file = dest_dir / file
        return temp_file
