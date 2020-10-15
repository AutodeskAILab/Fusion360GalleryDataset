import adsk.core
import adsk.fusion
import traceback
import json
import os
import sys
import time
import copy
from pathlib import Path
from importlib import reload
from collections import OrderedDict 


# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

import name
import exporter
import regraph
import serialize
import exceptions
reload(regraph)
from logger import Logger
from sketch_extrude_importer import SketchExtrudeImporter
from regraph import Regraph
from regraph import RegraphTester
from regraph import RegraphWriter


# Set the graph mode to either PerExtrude or PerFace
GRAPH_MODE = "PerExtrude"
# GRAPH_MODE = "PerFace"

# Event handlers
handlers = []


class OnlineStatusChangedHandler(adsk.core.ApplicationEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        # Start the server when onlineStatusChanged handler returns
        start()


class RegraphExporter():
    """Reconstruction Graph
        Takes a reconstruction json file and converts it
        into a graph representing B-Rep topology"""

    def __init__(self, json_file, logger=None, mode="PerExtrude"):
        self.json_file = json_file
        self.logger = logger
        if self.logger is None:
            self.logger = Logger()
        # The mode we want
        self.mode = mode

        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        # Create a component for reconstruction
        self.reconstruction = self.design.rootComponent.occurrences.addNewComponent(
            adsk.core.Matrix3D.create()
        )

    def export(self, output_dir, results_file, results):
        """Reconstruct the design from the json file"""
        self.output_dir = output_dir
        self.results = results
        self.results_file = results_file
        # Immediately log this in case we crash
        self.results[self.json_file.name] = []
        self.save_results()
        return_result = False
        try:
            with open(self.json_file, encoding="utf8") as f:
                json_data = json.load(f, object_pairs_hook=OrderedDict)

            # Graph generation
            # First ask if this is supported, to avoid reconstruction and save time
            supported, reason = Regraph.is_design_supported(json_data, self.mode)
            if not supported and self.mode == "PerFace":
                self.logger.log(f"Skipping {json_data['metadata']['parent_project']} early: {reason}")
                self.results[self.json_file.name].append({
                    "status": "Skip",
                    "reason": reason
                })
                return_result = False
            else:
                # Reconstruct from json to the reconstruction component
                importer = SketchExtrudeImporter(json_data)
                importer.reconstruct(reconstruction=self.reconstruction.component)
                # Generate and write out the graph
                regraph_writer = RegraphWriter(
                    logger=self.logger,
                    mode=self.mode,
                    include_labels=True
                )
                # Write out the graph from the reconstruction component
                writer_data = regraph_writer.write(
                    self.json_file,
                    output_dir,
                    reconstruction=self.reconstruction
                )
                # writer_data returns a dict of the form
                # [filename] = [{
                #   "graph": graph data
                #   "status": Success or some other reason for failure
                # }]
                return_result = self.update_results_status(output_dir, writer_data)                
        except Exception as ex:
            self.logger.log(f"Exception: {ex.__class__.__name__}")
            trace = traceback.format_exc()
            self.results[self.json_file.name].append({
                        "status": "Exception",
                        "exception": ex.__class__.__name__,
                        "exception_args": " ".join(ex.args),
                        "trace": trace
                    })
            return_result = False
        self.save_results()
        return return_result

    def update_results_status(self, output_dir, writer_data):
        """Update the results status"""
        return_result = True
        if writer_data is None:
            self.results[self.json_file.name].append({
                "status": "Skip",
                "reason": "No graph data returned"
            })
            return_result = False
        else:
            for graph_file_name, data in writer_data.items():
                result = {
                    "status": "Success",
                    "file": graph_file_name
                }
                if "status" in data:
                    if data["status"] != "Success":
                        result["status"] = "Skip"
                        result["reason"] = data["status"]
                        return_result = False
                graph_file = output_dir / graph_file_name
                if not graph_file.exists():
                    result["status"] = "Skip"
                    result["reason"] = "Graph file does not exists"
                    return_result = False
                self.results[self.json_file.name].append(result)
        return return_result

    def save_results(self):
        """Save out the results of conversion"""
        with open(self.results_file, "w", encoding="utf8") as f:
            json.dump(self.results, f, indent=4)


# -------------------------------------------------------------------------
# PROCESSING
# -------------------------------------------------------------------------


def load_results(results_file):
    """Load the results of conversion"""
    if results_file.exists():
        with open(results_file, "r", encoding="utf8") as f:
            return json.load(f)
    return {}


def start():
    app = adsk.core.Application.get()
    # Logger to print to the text commands window in Fusion
    logger = Logger()
    # Fusion requires an absolute path
    current_dir = Path(__file__).resolve().parent
    data_dir = current_dir.parent / "testdata"
    output_dir = data_dir / "output"
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    results_file = output_dir / "regraph_results.json"
    results = load_results(results_file)

    # Get all the files in the data folder
    json_files = [
        data_dir / "Couch.json",
        data_dir / "SingleSketchExtrude.json"
    ]

    json_count = len(json_files)
    success_count = 0
    for i, json_file in enumerate(json_files, start=1):
        if json_file.name in results:
            logger.log(f"[{i}/{json_count}] Skipping {json_file}")
        else:
            try:
                logger.log(f"[{i}/{json_count}] Processing {json_file}")
                regraph_exporter = RegraphExporter(
                    json_file, logger=logger, mode=GRAPH_MODE)
                result = regraph_exporter.export(output_dir, results_file, results)
                if result:
                    success_count += 1
            except Exception as ex:
                logger.log(f"Error exporting: {ex}")
                logger.log(traceback.format_exc())
            finally:
                # Close the document
                # Fusion automatically opens a new window
                # after the last one is closed
                app.activeDocument.close(False)
    logger.log("----------------------------")
    logger.log(f"[{success_count}/{json_count}] designs processed successfully")


def run(context):
    try:
        app = adsk.core.Application.get()
        # If we have started manually
        # we go ahead and startup
        if app.isStartupComplete:
            start()
        else:
            # If we are being started on startup
            # then we subscribe to ‘onlineStatusChanged’ event
            # This event is triggered on Fusion startup
            print("Setting up online status changed handler...")
            on_online_status_changed = OnlineStatusChangedHandler()
            app.onlineStatusChanged.add(on_online_status_changed)
            handlers.append(on_online_status_changed)

    except:
        print(traceback.format_exc())
