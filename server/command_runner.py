import adsk.core
import adsk.fusion
import traceback
import tempfile
import os
from zipfile import ZipFile

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
    
    def mesh(self, data):
        """Create a mesh in the given format (currently .stl) and send it back as a binary file"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        if data is None or "format" not in data:
            return self.__return_failure("format not specified")
        suffix = data["format"]
        valid_formats = [".stl"]
        if suffix not in valid_formats:
            return self.__return_failure("invalid format specified")
        try:
            temp_file = tempfile.NamedTemporaryFile(suffix=suffix)
            temp_file.close()
            stl_export_options = design.exportManager.createSTLExportOptions(design.rootComponent, temp_file.name)
            stl_export_options.sendToPrintUtility = False
            export_result = design.exportManager.execute(stl_export_options)
            file_exists = os.path.exists(temp_file.name)
            if export_result and file_exists:
                self.logger.log_text(f"Mesh temp file written to: {temp_file.name}")
                return self.__return_success(temp_file.name)
            else:
                return self.__return_failure(f"{suffix} export failure")
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

    def sketches(self, data):
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
                zip_file = self.__export_sketch_pngs()
            elif suffix == ".dxf":
                zip_file = self.__export_sketch_dxfs()
            return self.__return_success(zip_file)
        except Exception as ex:
            return self.__return_exception(ex)

    def __export_sketch_pngs(self):
        """Export all sketches as png files and return a zip file"""
        temp_dir = tempfile.TemporaryDirectory()
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Lets hide all the bodies so we can export some sketches
        for component in design.allComponents:
            for body in component.bRepBodies:
                body.isVisible = False
        
        # Also hide all the sketches
        for component in design.allComponents:
            for sketch in component.sketches:
                sketch.isVisible = False

        # Then we loop over each sketch and export a PNG
        for component in design.allComponents:
            for sketch in component.sketches:
                self.__export_sketch_png(sketch, temp_dir.name)
        
        return self.__zip_dir(temp_dir.name)

    def __export_sketch_png(self, sketch, dir):
        """Export a single sketch as png files"""
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Show the sketch
        sketch.isVisible = True

        # Get the existing camera and modify it
        camera = self.app.activeViewport.camera
        # TopView will look at the XY plane
        # TODO: We need to orient the camera to face the sketch here
        # currently this assumes the sketch is on the XY plane
        camera.viewOrientation = adsk.core.ViewOrientations.TopViewOrientation
        # Set this once to fit to the camera view
        # But fit() needs to also be called below
        camera.isFitView = True 
        self.app.activeViewport.camera = camera  # Update the viewport
        # Call fit to the screen after we have changed to top view
        self.app.activeViewport.fit()

        # Save image
        png_file = os.path.join(dir, f"{sketch.name}.png")
        self.app.activeViewport.saveAsImageFile(png_file, 800, 600)
        self.logger.log_text(f"Sketch png temp file written to: {png_file}")
        # Hide the sketch ready for the next export
        sketch.isVisible = False

    def __export_sketch_dxfs(self):
        """Export all sketches as dxf files and return a zip file"""
        temp_dir = tempfile.TemporaryDirectory()
        design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Then we loop over each sketch and export a DXF
        for component in design.allComponents:
            for sketch in component.sketches:
                try:
                    dxf_file = os.path.join(temp_dir.name, f"{sketch.name}.dxf")
                    sketch.saveAsDXF(dxf_file)
                except:
                    # If the sketch is Null then keep on to the next
                    pass
        return self.__zip_dir(temp_dir.name)

    def __zip_dir(self, dir):
        """Create a temp zip file of all the files in a given folder"""
        zip_file = tempfile.NamedTemporaryFile(suffix=".zip")
        zip_file.close()
        with ZipFile(zip_file.name, "w") as zip_obj:
            # Iterate over all the files in directory
            for folder_name, subfolders, files in os.walk(dir):
                for file in files:
                    #create complete filepath of file in directory
                    file_path = os.path.join(folder_name, file)
                    # Add file to zip
                    zip_obj.write(file_path, file)
            self.logger.log_text(f"Sketch zip temp file written to: {zip_file.name}")
        return zip_file.name

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

        
