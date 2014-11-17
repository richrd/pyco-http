#!/usr/bin/python

import sys
import time
import socket
import select
import urllib
import urlparse

class PycoHTTP:
    def __init__(self):
        self.running = 0
        self.host = ""
        self.port = 8080
        self.socket = None
        self.eol = "\r\n"
        self.max_queued_conns = 5
        self.max_request_len = 2048 # 2kb max request size
        self.select_timeout = 0.05
        self.headers = {
            "Content-Type": "text/html",
            "Server": "PycoHTTP",
            "Connection": "close",
        }
        self.request_handler = None

    def log(self, s):
        print s

    def set_handler(self, request_handler):
        """Set the callback function for handling requests."""
        self.request_handler = request_handler

    def start(self, blocking=False):
        """Start the server."""
        self.running = 1
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Avoid "address already in use"
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.log("Hosting server...")
        try:
            self.socket.bind((self.host, self.port))
        except socket.error as msg:
            self.log('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            return False

        self.socket.listen(self.max_queued_conns)
        self.log('Socket now listening')

        if blocking:
            self.serve_blocking()
        return True

    def stop(self):
        """Stop the server."""
        self.running = 0

    def serve(self):
        """Needs to be called periodically to receive connections."""
        readable, writable, errored = select.select([self.socket], [], [], self.select_timeout)
        if self.socket in readable:
            conn, addr = self.socket.accept()
            self.handle_connection(conn, addr)

    def serve_blocking(self):
        """Accept connections in blocking mode."""
        while self.running:
            conn, addr = self.socket.accept()
            self.handle_connection(conn, addr)

    def parse_headers(self, lines):
        """Parse headers from list of lines in response."""
        headers = {}
        for line in lines:
            parts = line.split(":", 1)
            if len(parts) < 2: # Skip lines without a colon
                continue
            headers[parts[0].strip().lower()] = parts[1].strip()
        return headers


    def get_request_data(self, conn):
        """Receive HTTP request data."""
        # Loop and append received data until sufficent data is received
        received = ""
        while received[-4:] != self.eol*2:
            data = conn.recv(1024)
            if not data:
                break
            received += data
            if len(received) > self.max_request_len:
                received = received[:self.max_request_len]
                break

        # Check for empty requests
        if received.strip() == "":
            return False

        return received

    def parse_request(self, received, addr):
        # We don't support POST so get rid of request body
        needed = received.split(self.eol*2)[0]
        lines = needed.split(self.eol)

        # Get parts of the first request line
        first = lines[0].split(" ")
        lines.pop(0)

        # Extract request data
        req_type = first[0]
        req_url = first[1]

        # Get request heders
        headers = self.parse_headers(lines)
        request = {
            "client": addr,
            "type": req_type,
            "uri": req_url,
            "headers": headers,
        }

        return request

    def respond(self, conn, response):
        """Responde to a request."""

        # Build headers
        header_lines = []
        headers = self.headers
        if "headers" in response.keys():
            # Merge new headers into defaults
            headers = dict(self.headers.items() + response["headers"].items())            
        for header in headers.items():
            header_lines.append(header[0]+": "+header[1])

        # TODO: Response line should contain textual status too:
        # HTTP/1.0 200 OK
        data = "HTTP/1.1 " + str(response["status"]) + self.eol
        data += self.eol.join(header_lines) + (self.eol*2)
        data += response["data"]

        # Send the entire response
        # FIXME: may want to check for success and retry when necessary
        conn.sendall(data)

    def handle_connection(self, conn, addr):
        """Handle a HTTP connection."""
        self.log('Connected with ' + addr[0] + ':' + str(addr[1]))
        self.log("Getting request...")
        data = self.get_request_data(conn)
        request = False
        if data:
            request = self.parse_request(data, addr)
        if request:
            # If we have a request handler give it the request
            if self.request_handler:
                self.log("Handling reqest...")
                response = self.request_handler(request)
                if response:
                    self.respond(conn, response)
                    self.log("Response sent...")
        else:
            self.log("No request received!")
        conn.close()

# Example for a request handler
def handle_request(request):
    front_uris = ["/", "/index.html"]
    url = urlparse.urlparse(request["uri"])
    query = urllib.unquote(url.query)

    if url.path in front_uris:
        response = {
            "status": 200,
            "data": '<h1>Hello World!</h1>'
        }
    elif url.path == "/text.txt":
        response = {
            "status": 200,
            "headers": {"Content-Type": "text/plain"},
            "data": 'Hello World!\nNew line?'
        }
    elif url.path == "/close":
        response = False # Don't respond, just close connection
    else:
        response = {
            "status": 404,
            "data": 'Sorry, not found (404). <a href="/">Front page</a>'
        }

    return response

if __name__ == "__main__":
    srv = PycoHTTP()
    srv.set_handler(handle_request)
    srv.start()
    #srv.start(True) # Add true for a blocking server
    while True:
        srv.serve()
