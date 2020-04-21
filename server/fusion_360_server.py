
import adsk.core
import adsk.fusion
import traceback
import json
import threading
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
from .command_runner import CommandRunner
from .logging_util import LoggingUtil


HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080

# Global logger
logger = None
# Global command runner
runner = None


class OnlineStatusChangedHandler(adsk.core.ApplicationEventHandler):
    def notify(self, args):
        # Start the server when onlineStatusChanged handler returns
        start_server()


class Fusion360ServerRequestHandler(BaseHTTPRequestHandler):

    def do_HEAD(self):
        return

    def do_POST(self):
        try:
            post_data = self.get_post_data()
            logger.log_text("Post received!")
            logger.log_text(json.dumps(post_data))
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
                self.detach()
            
            data = None
            if "data" in post_data:
                data = post_data["data"]

            status_code, message = runner.run_command(command, data)
            self.respond(status_code, message)

        except Exception as ex:
            self.respond(500, str(ex.args))

    def do_GET(self):
        self.respond(400, "GET not supported, use POST")

    def get_post_data(self):
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        logger.log_text(f"post_body: {post_body}")
        post_body_json = json.loads(post_body)
        return post_body_json

    def respond(self, status, message):
        logger.log_text(f"[{status}] {message}")
        data = {
            "status": status,
            "message": message
        }
        json_string = json.dumps(data)
        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json_string.encode(encoding='utf_8'))

    def detach(self):
        # We have to shutdown the server from a separate thread to avoid deadlock
        logger.log_text("Shutting down...")
        server_shutdown_thread = threading.Thread(target=self.server.shutdown)
        server_shutdown_thread.daemon = True
        server_shutdown_thread.start()



def start_server():
    """Start the server"""
    # Setup the logger globally after Fusion has started
    global logger
    logger = LoggingUtil()
    logger.log_text("Started server...")
    # Set up the command runner we use to execute commands
    global runner
    runner = CommandRunner()
    runner.set_logger(logger)

    # Launch the server which will block the UI thread
    server = HTTPServer((HOST_NAME, PORT_NUMBER), Fusion360ServerRequestHandler)
    try:
        server.serve_forever(poll_interval=1.0)
    except KeyboardInterrupt:
        pass
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
            onOnlineStatusChanged = OnlineStatusChangedHandler()
            app.onlineStatusChanged.add(onOnlineStatusChanged)
    except:
        print(traceback.format_exc())
