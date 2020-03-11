
import adsk.core, adsk.fusion, traceback
import json
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler


HOST_NAME = '127.0.0.1'
PORT_NUMBER = 8080


def start_server():
    print('Starting server...')
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), Server)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()

class OnlineStatusChangedHandler(adsk.core.ApplicationEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        # Start the server when onlineStatusChanged handler returns
        start_server()

class Server(BaseHTTPRequestHandler):
    def do_HEAD(self):
        return
        
    def do_POST(self): 
        print("Post received!")
        try:
            app = adsk.core.Application.get()
            if app.isStartupComplete:
                self.respond(status=200, out_message="Post Received")
            else:
                self.respond(status=500, error_message='Start-up is not completed')
        except Exception as ex:
            self.respond(status=500, error_message= str(ex.args))

    def do_GET(self):
        print("Get received!")
        try:
            app = adsk.core.Application.get()
            if app.isStartupComplete:
                self.respond(status=200, out_message="Get Received")
            else:
                self.respond(status=500, error_message='Start-up is not completed')
        except Exception as ex:
            self.respond(status=500, error_message= str(ex.args))
        

    def handle_http(self, status, content_type, out_msg, excep=' '):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.end_headers()
        if status == 200:
            return bytes(out_msg, 'UTF-8')
        return bytes('FAILED {}'.format(excep),'UTF-8')
    
    def respond(self, status, out_message='OK', error_message=''):
        content = self.handle_http(status, 'text/plain', out_message, error_message)
        self.wfile.write(content)



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
            print('Setting up online status changed handler...')
            onOnlineStatusChanged = OnlineStatusChangedHandler()
            app.onlineStatusChanged.add(onOnlineStatusChanged)
        
        
    except:
        print(traceback.format_exc())