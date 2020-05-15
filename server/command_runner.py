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
from . import serialize


class CommandRunner():

    def __init__(self):
        self.logger = None
        self.app = adsk.core.Application.get()
        self.last_command = ""

    def set_logger(self, logger):
        self.logger = logger

    def run_command(self, command, data=None):
        """Run a command and route it to the right method"""
        try:
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
            elif command == "add_extrude":
                result = self.add_extrude(data)
            else:
                return self.__return_failure("Unknown command")
            return result
        except Exception as ex:
            return self.__return_exception(ex)
        finally:
            # Update the UI
            adsk.doEvents()

    def ping(self):
        """Ping for debugging"""
        return self.__return_success()

    def refresh(self):
        """Refresh the active viewport"""
        self.app.activeViewport.refresh()
        return self.__return_success()

    def reconstruct(self, data):
        """Reconstruct a design from the provided json data"""
        importer = SketchExtrudeImporter(data)
        importer.reconstruct()
        return self.__return_success()

    def clear(self):
        """Clear (i.e. close) all open designs in Fusion"""
        for doc in self.app.documents:
            # Save without closing
            doc.close(False)
        return self.__return_success()

    def mesh(self, data, dest_dir=None):
        """Create a mesh in the given format (currently .stl) and send it back as a binary file"""
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

    def brep(self, data, dest_dir=None):
        """Create a brep in the given format (currently .step, smt) and send it back as a binary file"""
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

    def sketches(self, data, dest_dir=None, use_zip=True):
        """Generate sketches in a given format (e.g. .png) and return as a binary zip file"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if data is None or "format" not in data:
            return self.__return_failure("format not specified")
        suffix = data["format"]
        valid_formats = [".png", ".dxf"]
        if suffix not in valid_formats:
            return self.__return_failure("invalid format specified")
        if suffix == ".png":
            zip_file = self.__export_sketch_pngs(dest_dir, use_zip)
        elif suffix == ".dxf":
            zip_file = self.__export_sketch_dxfs(dest_dir, use_zip)
        return self.__return_success(zip_file)

    def commands(self, data):
        """Run a series of commands one after the other"""
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
            "sketch_id": sketch_uuid,
            "sketch_name": sketch.name
        })

    def add_line(self, data):
        """Add a line to an existing sketch"""
        if (data is None or "sketch_name" not in data or
                "pt1" not in data or "pt2" not in data):
            return self.__return_failure("add_line data not specified")
        sketch = match.sketch_by_name(data["sketch_name"])
        if sketch is None:
            return self.__return_failure("sketch not found")
        sketch_uuid = name.get_uuid(sketch)
        start_point = deserialize.point3d(data["pt1"])
        end_point = deserialize.point3d(data["pt2"])
        if "transform" in data:
            # For mapping Fusion exported data back correctly
            xform = deserialize.matrix3d(data["transform"])
            sketch_transform = sketch.transform
            sketch_transform.invert()
            xform.transformBy(sketch_transform)
            start_point.transformBy(xform)
            end_point.transformBy(xform)

        line = sketch.sketchCurves.sketchLines.addByTwoPoints(start_point, end_point)
        line_uuid = name.set_uuid(line)
        name.set_uuids_for_sketch(sketch)
        profile_data = serialize.sketch_profiles(sketch.profiles)
        return self.__return_success({
            "sketch_id": sketch_uuid,
            "sketch_name": sketch.name,
            "line_id": line_uuid,
            "profiles": profile_data
        })

    def add_extrude(self, data):
        """Add an extrude feature from a sketch"""
        if (data is None or "sketch_name" not in data or
                "profile_id" not in data or "distance" not in data or
                "operation" not in data):
            return self.__return_failure("add_extrude data not specified")
        sketch = match.sketch_by_name(data["sketch_name"])
        if sketch is None:
            return self.__return_failure("extrude sketch not found")
        profile = match.sketch_profile_by_id(data["profile_id"], [sketch])
        if profile is None:
            return self.__return_failure("extrude sketch profile not found")
        operation = self.__get_extrude_operation(data["operation"])
        if operation is None:
            return self.__return_failure("extrude operation not found")

        # Make the extrude
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        extrudes = design.rootComponent.features.extrudeFeatures
        extrude_input = extrudes.createInput(profile, operation)
        distance = adsk.core.ValueInput.createByReal(data["distance"])
        extent_distance = adsk.fusion.DistanceExtentDefinition.create(distance)
        extrude_input.setOneSideExtent(extent_distance, adsk.fusion.ExtentDirections.PositiveExtentDirection)
        extrude_feature = extrudes.add(extrude_input)
        # Serialize the data and return
        extrude_feature_data = serialize.extrude_feature_brep(extrude_feature)
        return self.__return_success(extrude_feature_data)

    def __get_extrude_operation(self, operation):
        """Return an appropriate extrude operation"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Check that the operation is going to work
        body_count = 0
        for component in design.allComponents:
            body_count += component.bRepBodies.count
        # If there are no other bodies, we have to make a new body
        if body_count == 0:
            operation = "NewBodyFeatureOperation"
        return deserialize.feature_operations(operation)

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
