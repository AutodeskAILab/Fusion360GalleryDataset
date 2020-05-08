import adsk.core
import adsk.fusion
import traceback
import tempfile
import shutil
import os
from zipfile import ZipFile
from pathlib import Path

from .sketch_extrude_importer import SketchExtrudeImporter
from . import name
from . import match
from . import deserialize


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
        elif command == "refresh":
            result = self.refresh()
        elif command == "reconstruct":
            result = self.reconstruct(data)
        elif command == "clear":
            result = self.clear()
        elif command == "mesh":
            result = self.mesh(data)
        elif command == "brep":
            result = self.brep(data)
        elif command == "sketches":
            result = self.sketches(data)
        elif command == "commands":
            result = self.commands(data)
        elif command == "add_sketch":
            result = self.add_sketch(data)
        elif command == "add_line":
            result = self.add_line(data)       
        # Update the UI
        adsk.doEvents()
        return result

    def ping(self):
        """Ping for debugging"""
        return self.__return_success()

    def refresh(self):
        """Refresh the active viewport"""
        self.app.activeViewport.refresh()
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

    def mesh(self, data, dest_dir=None):
        """Create a mesh in the given format (currently .stl) and send it back as a binary file"""
        try:
            error, suffix = self.__check_file(data, [".stl"])
            if error is not None:
                return self.__return_failure(error)

            temp_file = self.__get_temp_file(data["file"], dest_dir)
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            stl_export_options = design.exportManager.createSTLExportOptions(design.rootComponent, str(temp_file.resolve()))
            stl_export_options.sendToPrintUtility = False
            export_result = design.exportManager.execute(stl_export_options)
            file_exists = temp_file.exists()
            if export_result and file_exists:
                self.logger.log_text(f"Mesh temp file written to: {temp_file}")
                return self.__return_success(temp_file)
            else:
                return self.__return_failure(f"{suffix} export failure")
        except Exception as ex:
            return self.__return_exception(ex)

    def brep(self, data, dest_dir=None):
        """Create a brep in the given format (currently .step, smt) and send it back as a binary file"""
        try:
            error, suffix = self.__check_file(data, [".step", ".smt"])
            if error is not None:
                return self.__return_failure(error)
            temp_file = self.__get_temp_file(data["file"], dest_dir)
            design = adsk.fusion.Design.cast(self.app.activeProduct)
            if suffix == ".step":
                export_options = design.exportManager.createSTEPExportOptions(str(temp_file.resolve()), design.rootComponent)
            elif suffix == ".smt":
                export_options = design.exportManager.createSMTExportOptions(str(temp_file.resolve()), design.rootComponent)
            export_result = design.exportManager.execute(export_options)
            file_exists = temp_file.exists()
            if export_result and file_exists:
                self.logger.log_text(f"BRep temp file written to: {temp_file}")
                return self.__return_success(temp_file)
            else:
                return self.__return_failure(f"{suffix} export failure")
        except Exception as ex:
            return self.__return_exception(ex)

    def sketches(self, data, dest_dir=None, use_zip=True):
        """Generate sketches in a given format (e.g. .png) and return as a binary zip file"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if data is None or "format" not in data:
            return self.__return_failure("format not specified")
        suffix = data["format"]
        valid_formats = [".png", ".dxf"]
        if suffix not in valid_formats:
            return self.__return_failure("invalid format specified")
        try:
            if suffix == ".png":
                zip_file = self.__export_sketch_pngs(dest_dir, use_zip)
            elif suffix == ".dxf":
                zip_file = self.__export_sketch_dxfs(dest_dir, use_zip)
            return self.__return_success(zip_file)
        except Exception as ex:
            return self.__return_exception(ex)

    def commands(self, data):
        """Run a series of commands one after the other"""
        try:
            if not isinstance(data, list) or len(data) == 0:
                return self.__return_failure("command list not specified")
            # Make a list of the valid commands
            command_list = []
            # Keep track of how many bits of data to return
            return_data_count = 0
            # Build the list of commands to run
            for command_set in data:
                if "command" in command_set:
                    command_string = command_set["command"]
                    if isinstance(command_string, str):
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

            if len(command_list) == 0:
                return self.__return_failure("no valid commands found")

            if return_data_count > 0:
                # Create a temp directory for the output to go
                dest_dir = Path(tempfile.mkdtemp())
            # Execute the list of commands
            for command_set in command_list:
                command_string = command_set["command_string"]
                self.logger.log_text(f"Executing {command_string} command")
                if command_string in ["ping", "refresh", "clear"]:
                    status, message, return_data = command_set["command"]()
                    if status == 500:
                        return status, message, return_data
                elif command_string == "reconstruct":
                    if "data" not in command_set:
                        return self.__return_failure("missing arguments")
                    data = command_set["data"]
                    status, message, return_data = command_set["command"](data)
                    if status == 500:
                        return status, message, return_data
                elif command_string in ["mesh", "brep"]:
                    if "data" not in command_set:
                        return self.__return_failure("missing arguments")
                    data = command_set["data"]
                    status, message, return_data = command_set["command"](data, dest_dir=dest_dir)
                    if status == 500:
                        return status, message, return_data
                # Commands creating a folder of output
                elif command_string == "sketches":
                    if "data" not in command_set:
                        return self.__return_failure("missing arguments")
                    data = command_set["data"]
                    status, message, return_data = command_set["command"](data, dest_dir=dest_dir, use_zip=False)
                    if status == 500:
                        return status, message, return_data
            # Zip all the files we produced up and pass them back
            if return_data_count > 0:
                zip_file = self.__zip_dir(dest_dir)
                return self.__return_success(zip_file)
            else:
                return self.__return_success()

        except Exception as ex:
            return self.__return_exception(ex)

    def add_sketch(self, data):
        """Add a sketch to the existing design"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if data is None or "sketch_plane" not in data:
            return self.__return_failure("sketch_plane not specified")
        sketch_plane = match.sketch_plane(data["sketch_plane"])
        if sketch_plane is None:
            return self.__return_failure("sketch_plane could not be found")
        sketches = design.rootComponent.sketches
        sketch = sketches.addWithoutEdges(sketch_plane)
        sketch_uuid = name.set_uuid(sketch)
        return self.__return_success({
            "id": sketch_uuid
        })

    def add_line(self, data):
        """Add a line to an existing sketch"""
        if (data is None or "sketch_id" not in data or
                "pt1" not in data or "pt2" not in data):
            return self.__return_failure("add_line data not specified")
        sketch = match.sketch(data["sketch_id"])
        # TODO: Debug why id is None
        if sketch is None:
            return self.__return_failure("sketch not found")
        start_point = deserialize.point3d(data["pt1"])
        end_point = deserialize.point3d(data["pt2"])
        line = sketch.sketchCurves.sketchLines.addByTwoPoints(start_point, end_point)
        line_uuid = name.set_uuid(line)
        return self.__return_success({
            "id": line_uuid
        })

    def __export_sketch_pngs(self, dest_dir=None, use_zip=True):
        """Export all sketches as png files and return a zip file"""
        if dest_dir is None:
            dest_dir = Path(tempfile.mkdtemp())
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Lets hide all the bodies and sketches so we can export
        for component in design.allComponents:
            for body in component.bRepBodies:
                body.isVisible = False
            for sketch in component.sketches:
                sketch.isVisible = False

        # Then we loop over each sketch and export a PNG
        for component in design.allComponents:
            for sketch in component.sketches:
                self.__export_sketch_png(sketch, dest_dir)

        # Now lets show all the bodies and sketches again
        for component in design.allComponents:
            for body in component.bRepBodies:
                body.isVisible = True
            for sketch in component.sketches:
                sketch.isVisible = True

        if use_zip:
            return self.__zip_dir(dest_dir)
        else:
            return dest_dir

    def __export_sketch_png(self, sketch, dest_dir):
        """Export a single sketch as png files"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Show the sketch
        sketch.isVisible = True

        # Get the existing camera and modify it
        camera = self.app.activeViewport.camera
        # Pull out the transform matrix pieces
        (origin, xAxis, yAxis, zAxis) = sketch.transform.getAsCoordinateSystem()
        # We will fit to the contents of the screen
        # So we just need to point the camera in the right direction
        camera.target = origin
        camera.upVector = yAxis
        eye_offset = zAxis.asPoint()
        camera.eye = adsk.core.Point3D.create(
            origin.x + eye_offset.x,
            origin.y + eye_offset.y,
            origin.z + eye_offset.z
        )

        # Set this once to fit to the camera view
        # But fit() needs to also be called below
        camera.isFitView = True
        self.app.activeViewport.camera = camera  # Update the viewport
        # Call fit to the screen after we have changed to top view
        self.app.activeViewport.fit()

        # Save image
        png_file = dest_dir / f"{sketch.name}.png"
        self.app.activeViewport.saveAsImageFile(str(png_file.resolve()), 800, 600)
        self.logger.log_text(f"Sketch png temp file written to: {png_file}")
        # Hide the sketch ready for the next export
        sketch.isVisible = False
        adsk.doEvents()
        self.app.activeViewport.refresh()

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
            self.logger.log_text(f"Sketch zip temp file written to: {zip_file.name}")
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

    def __return_success(self, data=None):
        message = f"Success processing {self.last_command} command"
        return 200, message, data

    def __return_failure(self, reason):
        message = f"Failed processing {self.last_command} command due to {reason}"
        return 500, message, None

    def __return_exception(self, ex):
        message = f"""Error processing {self.last_command} command\n
                      Exception of type {type(ex)} with args: {ex.args}\n
                      {traceback.format_exc()}"""
        return 500, message, None
