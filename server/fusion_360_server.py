
import adsk.core
import adsk.fusion
import traceback
import json
import threading
import shutil
import os
import time
from pathlib import Path
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
from .command_runner import CommandRunner
from .logging_util import LoggingUtil


# Event handlers
handlers = []


class OnlineStatusChangedHandler(adsk.core.ApplicationEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        # Start the server when onlineStatusChanged handler returns
        start_server()


class Fusion360ServerRequestHandler(BaseHTTPRequestHandler):

    def do_HEAD(self):
        return

    def do_POST(self):
        try:
            logger = LoggingUtil()
            runner = CommandRunner()
            runner.set_logger(logger)

            post_data = self.get_post_data()
            logger.log_text("\n")
            # logger.log_text(json.dumps(post_data))
            if "command" not in post_data:
                self.respond(400, "Command not present")
                return

            app = adsk.core.Application.get()
            if not app.isStartupComplete:
                self.respond(500, "Start-up is not completed")
                return

            command = post_data["command"]
            logger.log_text(f"Command: {command}")
            if command == "detach":
                logger.log_text("Shutting down...")
                self.detach()
            
            data = None
            if "data" in post_data:
                data = post_data["data"]

            status_code, message, binary_file = runner.run_command(command, data)
            if binary_file is not None:
                logger.log_text(f"[{status_code}] {binary_file}")
                self.respond_binary_file(status_code, binary_file)
            else:
                logger.log_text(f"[{status_code}] {message}")
                self.respond(status_code, message)


        except Exception as ex:
            self.respond(500, str(ex.args))

    def do_GET(self):
        self.respond(400, "GET not supported, use POST")

    def get_post_data(self):
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        # logger.log_text(f"post_body: {post_body}")
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

    def respond(self, status_code, message):
        data = {
            "status": status_code,
            "message": message
        }
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
    host_name = "127.0.0.1"
    port_number = 8080
    # If we have a launch file then we find the host and port to use
    launch_json_file = Path(os.path.dirname(__file__)) / "launch.json"
    if launch_json_file.exists():
        with open(launch_json_file) as file_handle:
            launch_data = json.load(file_handle)
            host_name = launch_data["host"]
            port_number = launch_data["start_port"] + len(launch_data["servers"])
            launch_data["servers"].append({
                "host": host_name,
                "port": port_number,
                "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            })
        # Write out the changes
        # TODO: Handle possible issue if we don't launch each instance in sequence
        with open(launch_json_file, "w") as file_handle:
            json.dump(launch_data, file_handle, indent=4)
    return host_name, port_number

def start_server():
    """Start the server"""

    # Setup the logger globally after Fusion has started
    logger = LoggingUtil()
    logger.log_text("Started server...")
    # Set up the command runner we use to execute commands
    runner = CommandRunner()
    runner.set_logger(logger)

    # Check if we need to use a different host name and port
    host_name, port_number = get_launch_endpoint()

    # Launch the server which will block the UI thread
    logger.log_text(f"Connecting on: {host_name}:{port_number}")
    server = HTTPServer((host_name, port_number), Fusion360ServerRequestHandler)
    try:
        server.serve_forever(poll_interval=1.0)
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        logger.log_text(str(ex))
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
