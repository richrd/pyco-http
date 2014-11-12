#!/usr/bin/python

""" PycoHTTP

Super minimal "pico sized" python HTTP server (or API interface)

Only supports:
- One request at a time, no concurrency
- Only GET requests
- Only responds with text/html
- Does NOT serve files (or anything) by default
- Responses are defined via a Python callback

Purpouse:
- Adding minimal web interfaces to Python apps.

Why do this?
- For learning purpouses
- To use in my projects
"""

import sys
import socket
import time

class PycoHTTP:
    def __init__(self):
        self.running = 0
        self.host = ""
        self.port = 8080
        self.socket = None
        self.eol = "\r\n"
        self.max_queued_conns = 5
        self.max_request_len = 2048 # 2kb max request size
        self.headers = [
            "Content-Type: text/html",
            "Server: MinHTTP",
            "Connection: close",
        ]
        self.request_handler = None

    def log(self, s):
        print s

    def set_handler(self, request_handler):
        """Set the function for handling requests."""
        self.request_handler = request_handler

    def listen(self):
        """Start the server and listen for connections."""
        self.running = 1
        self.log("Hosting server...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((self.host, self.port))
        except socket.error as msg:
            self.log('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()

        s.listen(self.max_queued_conns)
        self.log('Socket now listening')

        # Run until stopped
        while self.running:
            conn, addr = s.accept()
            self.handle_connection(conn, addr)

    def stop(self):
        """Stop listening."""
        # Should somehow cancel the blocking s.accept() too...
        self.running = 0

    def parse_headers(self, lines):
        """Parse headers from list of lines in response."""
        headers = {}
        for line in lines:
            parts = line.split(":", 1)
            if len(parts) < 2:
                continue
            headers[parts[0].strip().lower()] = parts[1].strip()
        return headers

    def get_request_data(self, conn):
        """Receive a request."""
        received = ""
        while received[-4:] != self.eol*2:
            data = conn.recv(1024)
            if not data:
                break
            received += data
            time.sleep(.00001)

        # We don't support POST so no need for request data
        needed = received.split(self.eol*2)[0]

        lines = needed.split(self.eol)
        first = lines[0].split(" ")
        lines.pop(0)
        req_type = first[0]
        req_url = first[1]
        headers = self.parse_headers(lines)
        request = {
            "type": req_type,
            "uri": req_url,
            "headers": headers,
        }
        return request

    def respond(self, conn, response):
        """Responde to a request."""
        # TODO: Response line should contain textual status too:
        # HTTP/1.0 200 OK
        data = "HTTP/1.1 " + str(response["status"]) + self.eol
        data += self.eol.join(self.headers) + (self.eol*2)
        data += response["data"]

        conn.sendall(data)

    def handle_connection(self, conn, addr):
        """Handle a HTTP connection."""
        self.log('Connected with ' + addr[0] + ':' + str(addr[1]))
        request = self.get_request_data(conn)
        if self.request_handler:
            response = self.request_handler(request)
            self.respond(conn, response)
        conn.close()

# Example for a request handler
def handle_request(request):
    front_uris = ["/", "/index.html"]
    if request["uri"] in front_uris:
        body = "<h1>Hello World!</h1>"
        response = {
            "status": 200,
            "data": body
        }
    else:
        response = {
            "status": 404,
            "data": "Sorry, can't find that (404)."
        }
    return response

srv = PycoHTTP()
srv.set_handler(handle_request)
srv.listen()
