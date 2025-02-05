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
import logging
import shutil
import atexit
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import cgi
import json

# Configure logging for consistent output
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def generate_password(length=12):
    """Generate a random password of the given length."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

class AuthHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, use_auth=False, password='', **kwargs):
        self.use_auth = use_auth
        self.username = 'user'
        self.password = password
        super().__init__(*args, **kwargs)

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Restricted Access"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def authenticate(self, auth_header):
        """Safely parse and validate the basic authentication header."""
        try:
            encoded_credentials = auth_header.split()[1]
            auth_decoded = base64.b64decode(encoded_credentials).decode('ascii')
            provided_username, provided_password = auth_decoded.split(':', 1)
            return provided_username == self.username and provided_password == self.password
        except Exception as e:
            logging.warning("Failed to parse authentication header: %s", e)
            return False

    def do_GET(self):
        """Handle GET requests - serve files or the upload page."""
        if self.use_auth:
            auth_header = self.headers.get('Authorization')
            if not auth_header or not self.authenticate(auth_header):
                self.do_AUTHHEAD()
                self.wfile.write(b'Authentication required')
                return

        # Serve the file list as JSON
        if self.path == '/list':
            files = self.list_directory_json()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(files).encode())
            return

        # Serve the upload page for the root path
        if self.path == '/':
            self.send_upload_page()
            return
        
        # Serve files for other paths
        super().do_GET()

    def list_directory_json(self):
        """Return a JSON list of files in the current directory."""
        files = []
        try:
            file_list = os.listdir(self.directory)
            for name in file_list:
                if name.startswith('.'):
                    continue
                fullname = os.path.join(self.directory, name)
                if os.path.isfile(fullname):
                    size = os.path.getsize(fullname)
                    files.append({
                        'name': name,
                        'size': size
                    })
            return files
        except OSError:
            return []

    def sanitize_filename(self, filename):
        """Sanitize the filename to prevent directory traversal attacks."""
        return os.path.basename(filename)

    def do_POST(self):
        """Handle POST requests for file uploads."""
        if self.use_auth:
            auth_header = self.headers.get('Authorization')
            if not auth_header or not self.authenticate(auth_header):
                self.do_AUTHHEAD()
                self.wfile.write(b'Authentication required')
                return

        content_type = self.headers.get('Content-Type')
        if not content_type or 'multipart/form-data' not in content_type:
            self.send_error(400, "Content-Type must be multipart/form-data")
            return

        # Process the upload
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD': 'POST'}
            )

            files_received = False
            for field in form.keys():
                field_item = form[field]
                if field_item.filename:
                    original_filename = self.sanitize_filename(field_item.filename)
                    
                    try:
                        with open(original_filename, 'wb') as f:
                            shutil.copyfileobj(field_item.file, f)
                        logging.info("Received and saved file: %s", original_filename)
                        files_received = True
                    except Exception as e:
                        logging.error("Error saving file %s: %s", original_filename, e)
                        self.send_error(500, f"Error saving file {original_filename}")
                        return

            if files_received:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b"File(s) received and saved successfully.\n")
            else:
                self.send_error(400, "No valid files were uploaded")

        except Exception as e:
            logging.error("Error processing upload: %s", e)
            self.send_error(500, "Internal server error")
    def send_upload_page(self):
        """Send the HTML upload page."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>Secure File Sharing</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        :root {
            --bg-color: #1a1a1a;
            --container-bg: #2d2d2d;
            --text-color: #ffffff;
            --border-color: #404040;
            --hover-color: #3d3d3d;
            --button-bg: #388E3C;
            --button-hover: #2E7D32;
            --copy-button-bg: #1976D2;
            --copy-button-hover: #1565C0;
            --drop-zone-bg: #333333;
        }

        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 20px auto;
            padding: 0 20px;
            background-color: var(--bg-color);
            color: var(--text-color);
        }

        .container {
            background-color: var(--container-bg);
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .upload-section {
            margin-bottom: 30px;
            padding: 20px;
            border: 2px dashed var(--border-color);
            border-radius: 8px;
        }

        .file-list {
            margin-top: 20px;
        }

        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            border-bottom: 1px solid var(--border-color);
        }

        .file-item a {
            color: var(--text-color);
            text-decoration: none;
        }

        .file-item a:hover {
            text-decoration: underline;
        }

        .upload-button {
            background-color: var(--button-bg);
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }

        .upload-button:hover {
            background-color: var(--button-hover);
        }

        #drop-zone {
            padding: 40px;
            text-align: center;
            border: 2px dashed var(--border-color);
            margin: 20px 0;
            background-color: var(--drop-zone-bg);
            cursor: pointer;
            transition: all 0.3s ease;
        }

        #drop-zone.dragover {
            background-color: var(--hover-color);
            border-color: var(--button-bg);
        }

        #upload-progress {
            display: none;
            margin-top: 10px;
        }

        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: var(--border-color);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 5px;
        }

        .progress {
            width: 0%;
            height: 100%;
            background-color: var(--button-bg);
            transition: width 0.3s ease;
        }

        .copy-button {
            background-color: var(--copy-button-bg);
            color: white;
            padding: 5px 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
        }

        .copy-button:hover {
            background-color: var(--copy-button-hover);
        }

        .error {
            color: #f44336;
            margin-top: 10px;
        }

        .success {
            color: #4CAF50;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>TS Server</h1>
        
        <div class="upload-section">
            <h2>Upload Files</h2>
            <form id="upload-form" enctype="multipart/form-data" method="post">
                <div id="drop-zone">
                    Drag & drop files here or click to select
                    <br><br>
                    <input type="file" name="file" multiple style="display: none;" id="file-input">
                </div>
                <div id="upload-progress">
                    <div class="progress-bar">
                        <div class="progress"></div>
                    </div>
                    <div id="progress-text">0%</div>
                </div>
                <div id="status-message"></div>
                <button type="submit" class="upload-button">Upload Files</button>
            </form>
        </div>

        <div class="file-list">
            <h2>Available Files</h2>
            <div id="files">
                <!-- Files will be listed here -->
            </div>
        </div>
    </div>

    <script>
        const dropZone = document.getElementById('drop-zone');
        const fileInput = document.getElementById('file-input');
        const uploadForm = document.getElementById('upload-form');
        const progressBar = document.querySelector('.progress');
        const progressText = document.getElementById('progress-text');
        const uploadProgress = document.getElementById('upload-progress');
        const statusMessage = document.getElementById('status-message');

        dropZone.onclick = () => fileInput.click();

        dropZone.ondragover = (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        };

        dropZone.ondragleave = () => {
            dropZone.classList.remove('dragover');
        };

        dropZone.ondrop = (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            fileInput.files = e.dataTransfer.files;
        };

        uploadForm.onsubmit = async (e) => {
            e.preventDefault();
            const formData = new FormData(uploadForm);
            uploadProgress.style.display = 'block';
            statusMessage.textContent = '';

            try {
                const xhr = new XMLHttpRequest();
                xhr.upload.onprogress = (event) => {
                    const percent = (event.loaded / event.total) * 100;
                    progressBar.style.width = percent + '%';
                    progressText.textContent = Math.round(percent) + '%';
                };

                xhr.onload = function() {
                    if (xhr.status === 200) {
                        statusMessage.className = 'success';
                        statusMessage.textContent = 'Files uploaded successfully!';
                        loadFiles();
                        uploadForm.reset();
                    } else {
                        statusMessage.className = 'error';
                        statusMessage.textContent = 'Upload failed!';
                    }
                    uploadProgress.style.display = 'none';
                };

                xhr.onerror = function() {
                    statusMessage.className = 'error';
                    statusMessage.textContent = 'Upload failed!';
                    uploadProgress.style.display = 'none';
                };

                xhr.open('POST', '/');
                xhr.send(formData);
            } catch (error) {
                statusMessage.className = 'error';
                statusMessage.textContent = 'Upload failed: ' + error;
                uploadProgress.style.display = 'none';
            }
        };

        function formatFileSize(bytes) {
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            let size = bytes;
            let unitIndex = 0;
            while (size >= 1024 && unitIndex < units.length - 1) {
                size /= 1024;
                unitIndex++;
            }
            return `${size.toFixed(1)} ${units[unitIndex]}`;
        }

        async function loadFiles() {
            try {
                const response = await fetch('/list');
                const files = await response.json();
                const filesDiv = document.getElementById('files');
                filesDiv.innerHTML = '';

                files.forEach(file => {
                    const fileDiv = document.createElement('div');
                    fileDiv.className = 'file-item';
                    
                    const fileLink = document.createElement('a');
                    fileLink.href = '/' + file.name;
                    fileLink.textContent = `${file.name} (${formatFileSize(file.size)})`;
                    
                    const copyButton = document.createElement('button');
                    copyButton.className = 'copy-button';
                    copyButton.textContent = 'Copy Link';
                    copyButton.onclick = (e) => {
                        e.preventDefault();
                        navigator.clipboard.writeText(window.location.origin + '/' + file.name);
                        copyButton.textContent = 'Copied!';
                        setTimeout(() => {
                            copyButton.textContent = 'Copy Link';
                        }, 2000);
                    };

                    fileDiv.appendChild(fileLink);
                    fileDiv.appendChild(copyButton);
                    filesDiv.appendChild(fileDiv);
                });
            } catch (error) {
                console.error('Error loading files:', error);
            }
        }

        loadFiles();
    </script>
</body>
</html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

def run_server(port, use_auth, password):
    """Start the multithreaded HTTP server."""
    handler = partial(AuthHandler, use_auth=use_auth, password=password)
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, handler)
    
    # Print server information
    logging.info("=" * 50)
    logging.info("Server Information:")
    logging.info("-" * 50)
    logging.info(f"Directory: {os.getcwd()}")
    logging.info(f"Port: {port}")
    
    if use_auth:
        logging.info("\nAuthentication Required:")
        logging.info("-" * 50)
        logging.info(f"Username: user")
        logging.info(f"Password: {password}")
    
    logging.info("=" * 50)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logging.info("\nServer interrupted by user.")
    finally:
        httpd.server_close()

def run_funnel(port):
    """Start the Tailscale Funnel process and print the public URL."""
    try:
        process = subprocess.Popen(['tailscale', 'funnel', str(port)],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE,
                                   text=True)
        for line in process.stdout:
            logging.info(line.strip())
            if "https://" in line:
                match = re.search(r'(https://\S+)', line)
                if match:
                    logging.info("Share this link: %s", match.group(1))
                break
        return process
    except subprocess.CalledProcessError as e:
        logging.error("Error setting up Tailscale Funnel: %s", e)
        sys.exit(1)

def stop_funnel(process):
    """Terminate the Tailscale Funnel process and reset the funnel."""
    if process:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
    subprocess.run(['tailscale', 'funnel', 'reset'], check=False)

def signal_handler(sig, frame):
    logging.info("Stopping server and funnel...")
    if 'funnel_process' in globals():
        stop_funnel(funnel_process)
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Secure File Sharing Server with Tailscale Funnel")
    parser.add_argument("port", type=int, nargs="?", default=8080, help="Port to run the server on (default: 8080)")
    parser.add_argument("--auth", action="store_true", help="Enable basic authentication")
    parser.add_argument("--dir", type=str, default=".", help="Directory to serve (default: current directory)")
    args = parser.parse_args()

    port = args.port
    use_auth = args.auth
    serve_dir = os.path.abspath(args.dir)

    if not os.path.exists(serve_dir):
        logging.error("Error: Directory '%s' does not exist.", serve_dir)
        sys.exit(1)

    os.chdir(serve_dir)
    logging.info("Serving directory: %s", serve_dir)

    password = ""
    if use_auth:
        password = generate_password()
        logging.info("Generated credentials - Username: user, Password: %s", password)

    # Set up signal handler and atexit
    signal.signal(signal.SIGINT, signal_handler)
    funnel_process = run_funnel(port)
    atexit.register(stop_funnel, funnel_process)

    # Start the server
    run_server(port, use_auth, password)