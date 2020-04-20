
import adsk.core
import adsk.fusion
import traceback
import json
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler
from .command_runner import CommandRunner
from .logging_util import LoggingUtil


HOST_NAME = "127.0.0.1"
PORT_NUMBER = 8080

# Global logger
logger = None


def start_server():
    # Setup the logger globally after Fusion has started
    global logger
    logger = LoggingUtil()
    logger.log_text("Starting server...")
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), Fusion360Server)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()


class OnlineStatusChangedHandler(adsk.core.ApplicationEventHandler):

    def notify(self, args):
        # Start the server when onlineStatusChanged handler returns
        start_server()


class Fusion360Server(BaseHTTPRequestHandler):

    def __init__(self, request, client_address, server):
        BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        self.runner = CommandRunner()

    def do_HEAD(self):
        return

    def do_POST(self):
        try:
            data = self.get_post_json()
            logger.log_text("Post received!")
            logger.log_text(json.dumps(data))
            if "command" not in data:
                self.respond(400, "Command not present")
                return

            app = adsk.core.Application.get()
            if not app.isStartupComplete:
                self.respond(500, "Start-up is not completed")
                return

            command = data["command"]
            if command == "detach":
                self.detach()

            status_code, message = self.runner.run_command(command, data)
            self.respond(status_code, message)

        except Exception as ex:
            self.respond(500, str(ex.args))

    def do_GET(self):
        self.respond(400, "GET not supported, use POST")

    def get_post_data(self):
        content_len = int(self.headers.get("Content-length", 0))
        post_body = self.rfile.read(content_len)
        return json.loads(post_body.decode("utf-8"))

    def handle_http(self, status, content_type, message):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.end_headers()
        return bytes(message, "UTF-8")

    def respond(self, status, message):
        logger.log_text(f"[{status}] {message}")
        content = self.handle_http(status, "text/plain", message)
        self.wfile.write(content)

    def detach(self):
        self.server.shutdown()
        exit()


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
