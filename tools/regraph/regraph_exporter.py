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
        # References to the Fusion design
        self.app = adsk.core.Application.get()
        self.design = adsk.fusion.Design.cast(self.app.activeProduct)
        self.product = self.app.activeProduct
        self.timeline = self.app.activeProduct.timeline
        # Current extrude index
        self.current_extrude_index = 0
        # Current overall action index
        self.current_action_index = 0
        # The mode we want
        self.mode = mode

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def export(self, output_dir, results_file, results):
        """Reconstruct the design from the json file"""
        self.output_dir = output_dir
        self.results = results
        self.results_file = results_file
        # Immediately log this in case we crash
        self.results[self.json_file.name] = []
        self.save_results()
        try:
            with open(self.json_file, encoding="utf8") as f:
                json_data = json.load(f, object_pairs_hook=OrderedDict)
            
            # Graph generation
            regraph = Regraph(mode=self.mode)
            # First ask if this is supported, to avoid reconstruction and save time
            supported, reason = regraph.is_design_supported(json_data)
            # We abort if in PerFace mode
            # as there may be some partial designs we can use in PerExtrude mode
            if not supported and self.mode == "PerFace":
                self.results[self.json_file.name].append({
                    "status": "Skip",
                    "reason": reason
                })
            else:
                importer = SketchExtrudeImporter(json_data)
                importer.reconstruct()
                
                # By default regraph assumes the geometry is in the rootComponent
                graph_data = regraph.generate()
                if len(graph_data["graphs"]) > 0:
                    regraph_tester = RegraphTester(mode=self.mode)
                    regraph_tester.test(graph_data)
                    if self.mode == "PerFace":
                        regraph_tester.reconstruct(graph_data)
                    self.export_graph_data(graph_data)
                self.update_results_status(graph_data)
        except Exception as ex:
            self.logger.log(f"Exception: {ex.__class__.__name__}")
            trace = traceback.format_exc()
            self.results[self.json_file.name].append({
                        "status": "Exception",
                        "exception": ex.__class__.__name__,
                        "exception_args": " ".join(ex.args),
                        "trace": trace
                    })
        self.save_results()

    def export_graph_data(self, graph_data):
        """Export the graph data generated from regraph"""
        for index, graph in enumerate(graph_data["graphs"]):
            self.export_extrude_graph(graph, index)
        for seq_data in graph_data["sequences"]:
            self.export_sequence(seq_data)

    def get_export_path(self, name):
        """Get the export path from a name"""
        return self.output_dir / f"{self.json_file.stem}_{name}.json"

    def export_extrude_graph(self, graph, extrude_index):
        """Export a graph from an extrude operation"""
        if self.mode == "PerFace":
            graph_file = self.get_export_path("target")
        else:
            graph_file = self.get_export_path(f"{extrude_index:04}")
        self.export_graph(graph_file, graph)

    def export_graph(self, graph_file, graph):
        """Export a graph as json"""
        self.logger.log(f"Exporting {graph_file}")
        exporter.export_json(graph_file, graph)
        if graph_file.exists():
            self.results[self.json_file.name].append({
                "file": graph_file.name
            })
            self.save_results()
        else:
            self.logger.log(f"Error exporting {graph_file}")

    def export_sequence(self, seq_data):
        """Export the sequence data"""
        seq_file = self.output_dir / f"{self.json_file.stem}_sequence.json"
        with open(seq_file, "w", encoding="utf8") as f:
            json.dump(seq_data, f, indent=4)

    def update_results_status(self, graph_data):
        """Update the results status"""
        for index, status in enumerate(graph_data["status"]):
            reason = status
            if status != "Success":
                status = "Skip"
            if index < len(self.results[self.json_file.name]):
                self.results[self.json_file.name][index]["status"] = status
                self.results[self.json_file.name][index]["reason"] = reason
            else:
                self.results[self.json_file.name].append({
                    "status": status,
                    "reason": reason
                })

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
    output_dir = current_dir / "output"
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    results_file = output_dir / "regraph_results.json"
    results = load_results(results_file)

    # Get all the files in the data folder
    json_files = [f for f in data_dir.glob("**/*.json")]
    # json_files = [f for f in data_dir.glob("**/*_[0-9][0-9][0-9][0-9].json")]
    # json_files = [
    #     # data_dir / "Couch.json"
    #     # data_dir / "SingleSketchExtrude_RootComponent.json"
    # ]

    json_count = len(json_files)
    for i, json_file in enumerate(json_files, start=1):
        if json_file.name in results:
            logger.log(f"[{i}/{json_count}] Skipping {json_file}")
        else:
            try:
                logger.log(f"[{i}/{json_count}] Processing {json_file}")
                regraph_exporter = RegraphExporter(
                    json_file, logger=logger, mode="PerFace")
                regraph_exporter.export(output_dir, results_file, results)

            except Exception as ex:
                logger.log(f"Error exporting: {ex}")
                logger.log(traceback.format_exc())
            finally:
                # Close the document
                # Fusion automatically opens a new window
                # after the last one is closed
                app.activeDocument.close(False)


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
