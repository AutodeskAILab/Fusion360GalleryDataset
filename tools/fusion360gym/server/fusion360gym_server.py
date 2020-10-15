
import adsk.core
import adsk.fusion
import traceback
import json
import threading
import shutil
import os
import sys
import time
import importlib
from pathlib import Path
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

# Add the common folder to sys.path
COMMON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON_DIR not in sys.path:
    sys.path.append(COMMON_DIR)

from logger import Logger
from .command_runner import CommandRunner


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080

# Event handlers
handlers = []


class OnlineStatusChangedHandler(adsk.core.ApplicationEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        # Start the server when onlineStatusChanged handler returns
        start_server()


class Fusion360GymServerRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, logger, runner, *args):
        self.logger = logger
        self.runner = runner
        BaseHTTPRequestHandler.__init__(self, *args)

    def do_HEAD(self):
        return

    def do_POST(self):
        try:
            post_data = self.get_post_data()
            self.logger.log("\n")
            # logger.log(json.dumps(post_data))
            if "command" not in post_data:
                self.respond(400, "Command not present")
                return

            app = adsk.core.Application.get()
            if not app.isStartupComplete:
                self.respond(500, "Start-up is not completed")
                return

            command = post_data["command"]
            self.logger.log(f"Command: {command}")
            if command == "detach":
                self.logger.log("Shutting down...")
                self.detach()

            data = None
            if "data" in post_data:
                data = post_data["data"]

            status_code, message, return_data = self.runner.run_command(command, data)
            if return_data is not None and isinstance(return_data, Path):
                    self.logger.log(f"[{status_code}] {return_data}")
                    self.respond_binary_file(status_code, return_data)
            else:
                self.logger.log(f"[{status_code}] {message}")
                # if return_data is not None:
                #     self.logger.log(f"\t{return_data}")
                self.respond(status_code, message, return_data)

        except Exception as ex:
            message = f"""Error processing {command} command\n
                Exception of type {type(ex)} with args: {ex.args}\n
                {traceback.format_exc()}"""
            self.respond(500, ex)

    def do_GET(self):
        self.respond(400, "GET not supported, use POST")

    def get_post_data(self):
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        # self.logger.log(f"post_body: {post_body}")
        post_body_json = json.loads(post_body)
        return post_body_json

    def respond_binary_file(self, status_code, binary_file):
        self.send_response(status_code)
        self.send_header("Content-type", "application/octet-stream")
        self.end_headers()
        with open(binary_file, "rb") as file_handle:
            shutil.copyfileobj(file_handle, self.wfile)
        # Remove the file we made after we are done
        binary_file.unlink()

    def respond(self, status_code, message, return_data=None):
        data = {
            "status": status_code,
            "message": message
        }
        if return_data is not None:
            data["data"] = return_data
        json_string = json.dumps(data)
        self.send_response(status_code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json_string.encode(encoding='utf_8'))

    def detach(self):
        # We have to shutdown the server from a separate thread to avoid deadlock
        server_shutdown_thread = threading.Thread(target=self.server.shutdown)
        server_shutdown_thread.daemon = True
        server_shutdown_thread.start()


def get_launch_endpoint():
    """If we are launching multiple instances, find the right endpoint to use"""
    # Default endpoint
    host_name = DEFAULT_HOST
    port_number = DEFAULT_PORT
    # If we have a launch file then we find the host and port to use
    launch_json_file = Path(os.path.dirname(__file__)) / "launch.json"
    if launch_json_file.exists():
        with open(launch_json_file) as file_handle:
            launch_data = json.load(file_handle)
            for endpoint, server in launch_data.items():
                # If this server isn't connected, lets grab it and use it
                if not server["connected"]:
                    host_name = server["host"]
                    port_number = server["port"]
                    # Claim the server
                    server["connected"] = True
                    break
        # Write out the changes
        # TODO: Handle possible issue if we don't launch
        # each instance in sequence
        with open(launch_json_file, "w") as f:
            json.dump(launch_data, f, indent=4)
    return host_name, port_number


def start_server():
    """Start the server"""

    # # Setup the logger globally after Fusion has started
    logger = Logger()
    logger.log("Started server...")
    # # Set up the command runner we use to execute commands
    runner = CommandRunner()
    runner.set_logger(logger)

    # Workaround to pass the logger and runner
    def handler(*args):
        Fusion360GymServerRequestHandler(logger, runner, *args)

    # Check if we need to use a different host name and port
    host_name, port_number = get_launch_endpoint()

    # Launch the server which will block the UI thread
    logger.log(f"Connecting on: {host_name}:{port_number}")
    server = HTTPServer((host_name, port_number), handler)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        logger.log(str(ex))
    finally:
        server.server_close()


def run(context):
    try:
        app = adsk.core.Application.get()
        # If we have started the server manually
        # we go ahead and startup
        if app.isStartupComplete:
            start_server()
        else:
            # If the server is being started on startup
            # then we subscribe to ‘onlineStatusChanged’ event
            # This event is triggered on Fusion startup
            print("Setting up online status changed handler...")
            on_online_status_changed = OnlineStatusChangedHandler()
            app.onlineStatusChanged.add(on_online_status_changed)
            handlers.append(on_online_status_changed)
    except:
        print(traceback.format_exc())
