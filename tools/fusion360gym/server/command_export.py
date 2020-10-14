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
import importlib

from .command_base import CommandBase

# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "common")
)
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

import exporter
import regraph
importlib.reload(regraph)
importlib.reload(exporter)
import view_control
import geometry
import serialize
from sketch_extrude_importer import SketchExtrudeImporter
from regraph import Regraph
from regraph import RegraphWriter


class CommandExport(CommandBase):

    def reconstruct(self, data):
        """Reconstruct a design from the provided json data"""
        importer = SketchExtrudeImporter(data)
        importer.reconstruct()
        return self.runner.return_success()

    def mesh(self, data, dest_dir=None):
        """Create a mesh in the given format (either .obj or .stl)
            and send it back as a binary file"""
        data_file, error = self.check_file(data, [".obj", ".stl"])
        suffix = data_file.suffix
        if error is not None:
            return self.runner.return_failure(error)
        temp_file = self.get_temp_file(data["file"], dest_dir)
        if suffix == ".obj":
            export_result = exporter.export_obj_from_component(
                temp_file, self.design_state.reconstruction.component
            )
        elif suffix == ".stl":
            export_result = exporter.export_stl_from_component(
                temp_file, self.design_state.reconstruction
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
        data_file, error = self.check_file(data, [".step", ".smt", ".f3d"])
        suffix = data_file.suffix
        if error is not None:
            return self.runner.return_failure(error)
        temp_file = self.get_temp_file(data["file"], dest_dir)
        if suffix == ".step":
            export_result = exporter.export_step_from_component(
                temp_file, self.design_state.reconstruction.component
            )
        elif suffix == ".smt":
            export_result = exporter.export_smt_from_component(
                temp_file, self.design_state.reconstruction.component
            )
        elif suffix == ".f3d":
            export_result = exporter.export_f3d(temp_file)
        file_exists = temp_file.exists()
        if export_result and file_exists:
            self.logger.log(f"BRep temp file written to: {temp_file}")
            return self.runner.return_success(temp_file)
        else:
            return self.runner.return_failure(f"{suffix} export failure")

    def sketches(self, data, dest_dir=None, use_zip=True):
        """Generate sketches in a given format (e.g. .png)
            and return as a binary zip file"""
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

    def screenshot(self, data, dest_dir=None):
        """Retreive a screenshot of the current design as a png image"""
        data_file, error = self.check_file(data, [".png"])
        suffix = data_file.suffix
        if error is not None:
            return self.runner.return_failure(error)
        width = 512
        if "width" in data:
            width = data["width"]
        height = 512
        if "height" in data:
            height = data["height"]
        fit_camera = True
        if "fit_camera" in data:
            fit_camera = data["fit_camera"]

        temp_file = self.get_temp_file(data["file"], dest_dir)
        if fit_camera:
            self.app.activeViewport.fit()
        export_result = self.app.activeViewport.saveAsImageFile(
            str(temp_file.resolve()), width, height)
        file_exists = temp_file.exists()
        if export_result and file_exists:
            self.logger.log(f"Screenshot temp file written to: {temp_file}")
            return self.runner.return_success(temp_file)
        else:
            return self.runner.return_failure(f"{suffix} export failure")

    def graph(self, data, dest_dir=None, use_zip=True):
        """Generate graphs in a given format
            and return as a binary zip file"""
        if "format" not in data:
            return self.runner.return_failure("format not specified")
        if "sequence" not in data:
            return self.runner.return_failure("sequence not specified")
        if "labels" not in data:
            return self.runner.return_failure("labels not specified")
        mode = data["format"]
        is_sequence = data["sequence"]
        include_labels = data["labels"]
        error = None
        if is_sequence:
            data_file, error = self.check_file(data, [".json"])
            if error is not None:
                return self.runner.return_failure(error)
        valid_formats = ["PerFace", "PerExtrude"]
        if mode not in valid_formats:
            return self.runner.return_failure("invalid format specified")
        if is_sequence:
            return_data, error = self.__export_graph_sequence(
                data_file, mode, include_labels, dest_dir, use_zip
            )
        else:
            return_data = self.__export_graph(mode, include_labels)
        if error is None:
            return self.runner.return_success(return_data)
        else:
            return self.runner.return_failure(error)

    def __export_graph(self, mode, include_labels):
        """Export the current design as a graph"""
        regraph_graph = Regraph(
            reconstruction=self.design_state.reconstruction,
            logger=self.logger,
            mode=mode,
            use_temp_id=True,
            include_labels=include_labels
        )
        graph = regraph_graph.generate_from_bodies(
            self.design_state.reconstruction.bRepBodies
        )
        bbox = geometry.get_bounding_box(self.design_state.reconstruction)
        bbox_data = serialize.bounding_box3d(bbox)
        return {
            "graph": graph,
            "bounding_box": bbox_data
        }

    def __export_graph_sequence(self, file, mode,
                                include_labels, dest_dir=None, use_zip=True):
        """Export the current timeline as a graph sequence and return a zip file"""
        if dest_dir is None:
            dest_dir = Path(tempfile.mkdtemp())
        regraph_writer = RegraphWriter(
            logger=self.logger,
            mode=mode,
            include_labels=include_labels
        )
        writer_data = regraph_writer.write(
            file,
            dest_dir,
            reconstruction=self.design_state.reconstruction
        )
        # writer_data returns a dict of the form
        # [filename] = [{
        #   "graph": graph data
        #   "status": Success or some other reason for failure
        # }]
        return_error = None
        for graph_file_name, data in writer_data.items():
            if "status" in data:
                if data["status"] != "Success":
                    return_error = data["status"]
                    break
            graph_file = dest_dir / graph_file_name
            if not graph_file.exists():
                return_error = "Graph file does not exists"
                break
        if use_zip:
            return self.__zip_dir(dest_dir), return_error
        else:
            return dest_dir, return_error

    def __export_sketch_pngs(self, dest_dir=None, use_zip=True):
        """Export all sketches as png files and return a zip file"""
        if dest_dir is None:
            dest_dir = Path(tempfile.mkdtemp())
        # Loop over each sketch and export a PNG
        comp = self.design_state.reconstruction.component
        for sketch in comp.sketches:
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
        # Then we loop over each sketch and export a DXF
        comp = self.design_state.reconstruction.component
        for sketch in comp.sketches:
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
