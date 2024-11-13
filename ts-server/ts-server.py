#!/usr/bin/python3

import os
import sys
import subprocess
import signal
import re
import base64
import secrets
import string
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial

def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

class AuthHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.use_auth = kwargs.pop('use_auth', False)
        self.username = 'user'
        self.password = kwargs.pop('password', '')
        super().__init__(*args, **kwargs)

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Restricted Access"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        if self.use_auth:
            auth_header = self.headers.get('Authorization')
            if auth_header is None:
                self.do_AUTHHEAD()
                self.wfile.write(b'Authentication required')
                return
            elif not self.authenticate(auth_header):
                self.do_AUTHHEAD()
                self.wfile.write(b'Invalid credentials')
                return
        return SimpleHTTPRequestHandler.do_GET(self)

    def authenticate(self, auth_header):
        auth_decoded = base64.b64decode(auth_header.split()[1]).decode('ascii')
        provided_username, provided_password = auth_decoded.split(':')
        return provided_username == self.username and provided_password == self.password

def run_server(port, use_auth, password=None):
    handler = partial(AuthHandler, use_auth=use_auth, password=password)
    httpd = HTTPServer(('', port), handler)
    print(f"Serving at port {port}")
    httpd.serve_forever()

def run_funnel(port):
    try:
        process = subprocess.Popen(['tailscale', 'funnel', str(port)], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True)
        for line in process.stdout:
            print(line, end='')
            if "https://" in line:
                match = re.search(r'(https://\S+)', line)
                if match:
                    print(f"\nShare this link: {match.group(1)}")
                break
        return process
    except subprocess.CalledProcessError as e:
        print(f"Error setting up Tailscale Funnel: {e}")
        sys.exit(1)

def stop_funnel(process):
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    subprocess.run(['tailscale', 'funnel', 'reset'], check=False)

def signal_handler(sig, frame):
    print("\nStopping server and funnel...")
    if 'funnel_process' in globals():
        stop_funnel(funnel_process)
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="File sharing server with optional authentication.")
    parser.add_argument("port", type=int, nargs="?", default=8080, help="Port to run the server on (default: 8080)")
    parser.add_argument("--auth", action="store_true", help="Enable basic authentication")
    parser.add_argument("--dir", type=str, default=".", help="Directory to serve (default: current directory)")
    args = parser.parse_args()

    port = args.port
    use_auth = args.auth
    serve_dir = os.path.abspath(args.dir)

    if not os.path.exists(serve_dir):
        print(f"Error: Directory '{serve_dir}' does not exist.")
        sys.exit(1)

    os.chdir(serve_dir)
    print(f"Serving directory: {serve_dir}")

    password = None
    if use_auth:
        password = generate_password()
        print(f"Generated credentials:")
        print(f"Username: user")
        print(f"Password: {password}")

    signal.signal(signal.SIGINT, signal_handler)

    funnel_process = run_funnel(port)
    run_server(port, use_auth, password)