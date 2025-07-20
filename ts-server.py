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
import hmac
import hashlib
import tempfile
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from email.message import EmailMessage
from email import message_from_bytes
import json

# Configure logging for consistent output
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

def parse_multipart_form_data(data, boundary):
    """Parse multipart/form-data without using deprecated cgi module."""
    parts = data.split(b'--' + boundary.encode())
    files = []
    
    for part in parts:
        if b'Content-Disposition: form-data' not in part:
            continue
            
        # Split headers and content
        if b'\r\n\r\n' in part:
            headers_section, content = part.split(b'\r\n\r\n', 1)
        else:
            continue
            
        # Remove trailing boundary markers
        content = content.rstrip(b'\r\n--')
        
        # Parse the Content-Disposition header
        headers_text = headers_section.decode('utf-8', errors='ignore')
        if 'filename=' in headers_text:
            # Extract filename
            filename_match = re.search(r'filename="([^"]*)"', headers_text)
            if filename_match:
                filename = filename_match.group(1)
                if filename:  # Only add if filename is not empty
                    files.append({
                        'filename': filename,
                        'content': content
                    })
    
    return files

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

    def add_security_headers(self):
        """Add security headers to prevent common attacks."""
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('X-XSS-Protection', '1; mode=block')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')

    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Restricted Access"')
        self.send_header('Content-type', 'text/html')
        self.add_security_headers()
        self.end_headers()

    def authenticate(self, auth_header):
        """Safely parse and validate the basic authentication header with timing attack protection."""
        try:
            encoded_credentials = auth_header.split()[1]
            auth_decoded = base64.b64decode(encoded_credentials).decode('ascii')
            provided_username, provided_password = auth_decoded.split(':', 1)
            
            # Use constant-time comparison to prevent timing attacks
            username_valid = hmac.compare_digest(provided_username, self.username)
            password_valid = hmac.compare_digest(provided_password, self.password)
            
            return username_valid and password_valid
        except Exception as e:
            logging.warning("Failed to parse authentication header")
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
            self.add_security_headers()
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
        if not filename:
            raise ValueError("Empty filename")
        
        # Remove any path components and dangerous characters
        safe_filename = os.path.basename(filename)
        
        # Additional sanitization - remove dangerous characters
        safe_filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', safe_filename)
        
        # Check for edge cases after sanitization
        if not safe_filename or safe_filename in ['.', '..']:
            safe_filename = f'uploaded_file_{secrets.token_hex(4)}'
        
        # Prevent hidden files and reserved names (check after edge case handling)
        if safe_filename.startswith('.') or safe_filename.lower() in ['con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9']:
            safe_filename = 'file_' + safe_filename
        
        return safe_filename

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
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "No content provided")
                return
            
            # Read the entire request body
            post_data = self.rfile.read(content_length)
            
            # Extract boundary from Content-Type header
            boundary_match = re.search(r'boundary=([^;]+)', content_type)
            if not boundary_match:
                self.send_error(400, "No boundary found in Content-Type")
                return
            
            boundary = boundary_match.group(1).strip('"')
            
            # Parse multipart form data
            uploaded_files = parse_multipart_form_data(post_data, boundary)
            
            files_received = False
            for file_data in uploaded_files:
                original_filename = self.sanitize_filename(file_data['filename'])
                
                try:
                    with open(original_filename, 'wb') as f:
                        f.write(file_data['content'])
                    logging.info("Received and saved file: %s", original_filename)
                    files_received = True
                except Exception as e:
                    logging.error("Error saving file %s: %s", original_filename, e)
                    self.send_error(500, "Error saving file")
                    return

            if files_received:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.add_security_headers()
                self.end_headers()
                self.wfile.write(b"File(s) received and saved successfully.\n")
            else:
                self.send_error(400, "No valid files were uploaded")

        except Exception as e:
            logging.error("Error processing upload: %s", e)
            self.send_error(500, "Internal server error")
    
    def send_upload_page(self):
        """Send a dark-themed, intuitive HTML upload page with usage instructions on top, aligned buttons, and file selection feedback."""
        html = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TS File Server</title>
  <!-- FontAwesome for icons -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
  <style>
    :root {
      --bg-color: #121212;
      --container-bg: #1e1e1e;
      --text-color: #e0e0e0;
      --border-color: #333333;
      --hover-color: #2c2c2c;
      --button-bg: #6200ea;
      --button-hover: #3700b3;
      --copy-button-bg: #03dac6;
      --copy-button-hover: #018786;
      --download-button-bg: #03a9f4;
      --download-button-hover: #0288d1;
      --drop-zone-bg: #2c2c2c;
    }
    body {
      background-color: var(--bg-color);
      color: var(--text-color);
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
    }
    .container {
      max-width: 800px;
      margin: 40px auto;
      background-color: var(--container-bg);
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.5);
    }
    h1, h2 {
      text-align: center;
      margin-bottom: 20px;
    }
    .instructions {
      margin-bottom: 30px;
      padding: 15px;
      background-color: var(--hover-color);
      border: 1px solid var(--border-color);
      border-radius: 8px;
    }
    .instructions pre {
      background: #1e1e1e;
      padding: 10px;
      border-radius: 4px;
      overflow-x: auto;
      margin: 10px 0;
    }
    .instructions p {
      font-size: 14px;
      line-height: 1.4;
    }
    .upload-section {
      margin-bottom: 30px;
      padding: 20px;
      border: 2px dashed var(--border-color);
      border-radius: 8px;
      text-align: center;
      transition: background-color 0.3s ease;
    }
    .upload-section:hover {
      background-color: var(--hover-color);
    }
    #drop-zone {
      padding: 40px;
      border: 2px dashed var(--border-color);
      border-radius: 8px;
      background-color: var(--drop-zone-bg);
      cursor: pointer;
      transition: background-color 0.3s ease;
    }
    #drop-zone.dragover {
      background-color: var(--hover-color);
    }
    .upload-button {
      background-color: var(--button-bg);
      color: #ffffff;
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      margin-top: 20px;
      font-size: 16px;
      transition: background-color 0.3s ease;
    }
    .upload-button:hover {
      background-color: var(--button-hover);
    }
    /* Style for selected files list */
    #selected-files {
      margin-top: 10px;
      font-size: 14px;
      text-align: left;
    }
    #selected-files ul {
      list-style-type: none;
      padding-left: 0;
      margin: 0;
    }
    #selected-files li {
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .file-list {
      margin-top: 30px;
    }
    .file-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px;
      border-bottom: 1px solid var(--border-color);
    }
    .file-info {
      flex: 1;
      margin-right: 10px;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .file-info a {
      color: var(--button-bg);
      text-decoration: none;
    }
    .file-info a:hover {
      text-decoration: underline;
    }
    .button-group {
      display: flex;
      gap: 5px;
      flex-shrink: 0;
    }
    .copy-button {
      background-color: var(--copy-button-bg);
      color: #000000;
      border: none;
      padding: 5px 10px;
      border-radius: 4px;
      cursor: pointer;
      transition: background-color 0.3s ease;
    }
    .copy-button:hover {
      background-color: var(--copy-button-hover);
    }
    .download-button {
      background-color: var(--download-button-bg);
      color: #000000;
      border: none;
      padding: 5px 10px;
      border-radius: 4px;
      cursor: pointer;
      transition: background-color 0.3s ease;
      text-decoration: none;
      display: inline-block;
    }
    .download-button:hover {
      background-color: var(--download-button-hover);
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
    }
    .progress {
      width: 0%;
      height: 100%;
      background-color: var(--button-bg);
      transition: width 0.3s ease;
    }
    .message {
      margin-top: 10px;
      font-size: 14px;
    }
    .error {
      color: #ff6b6b;
    }
    .success {
      color: #4caf50;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>TS File Server</h1>
    <div class="instructions">
      <h2>Usage Instructions</h2>
      <p><strong>1. Upload a file via the HTML interface:</strong><br>
         Open <code>https://&lt;your-funnel-url&gt;/</code> in your browser, drag and drop your file(s) into the upload area, and click "Upload Files".</p>
      <p><strong>2. Upload a file via <code>curl</code> (with authentication):</strong></p>
      <pre>curl -u user:&lt;generated_password&gt; -X POST -F "file=@/path/to/your/file.txt" https://&lt;your-funnel-url&gt;/</pre>
      <p><strong>3. Download a file:</strong><br>
         <em>From the browser:</em> Click the file link or the <strong>Download</strong> button.<br>
         <em>From the command line:</em></p>
      <pre>curl -u user:&lt;generated_password&gt; https://&lt;your-funnel-url&gt;/file.txt -O</pre>
    </div>
    <div class="upload-section">
      <h2>Upload Files</h2>
      <form id="upload-form" enctype="multipart/form-data" method="post">
        <div id="drop-zone">
          <i class="fas fa-cloud-upload-alt" style="font-size: 48px;"></i>
          <p>Drag & drop files here or click to select</p>
          <input type="file" name="file" multiple style="display: none;" id="file-input">
        </div>
        <!-- Display selected files -->
        <div id="selected-files"></div>
        <div id="upload-progress">
          <div class="progress-bar">
            <div class="progress"></div>
          </div>
          <div id="progress-text">0%</div>
        </div>
        <div id="status-message" class="message"></div>
        <button type="submit" class="upload-button">Upload Files</button>
      </form>
    </div>
    <div class="file-list">
      <h2>Available Files</h2>
      <div id="files">
        <!-- File list will load here -->
      </div>
    </div>
  </div>
  <script>
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const selectedFilesDiv = document.getElementById('selected-files');
    const uploadForm = document.getElementById('upload-form');
    const progressBar = document.querySelector('.progress');
    const progressText = document.getElementById('progress-text');
    const uploadProgress = document.getElementById('upload-progress');
    const statusMessage = document.getElementById('status-message');

    // Trigger file selector on drop zone click
    dropZone.onclick = () => fileInput.click();

    // Function to update the "selected files" list
    function updateSelectedFiles() {
      const files = fileInput.files;
      if (files.length > 0) {
        let fileListHTML = '<ul>';
        for (let i = 0; i < files.length; i++) {
          fileListHTML += `<li>${files[i].name} (${formatFileSize(files[i].size)})</li>`;
        }
        fileListHTML += '</ul>';
        selectedFilesDiv.innerHTML = fileListHTML;
      } else {
        selectedFilesDiv.innerHTML = '';
      }
    }

    // Listen for file selection changes
    fileInput.addEventListener('change', updateSelectedFiles);

    // Visual cue for drag and drop
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
      updateSelectedFiles();
    };

    uploadForm.onsubmit = async (e) => {
      e.preventDefault();
      const formData = new FormData(uploadForm);
      uploadProgress.style.display = 'block';
      statusMessage.textContent = '';
      try {
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = (event.loaded / event.total) * 100;
            progressBar.style.width = percent + '%';
            progressText.textContent = Math.round(percent) + '%';
          }
        };
        xhr.onload = function() {
          if (xhr.status === 200) {
            statusMessage.className = 'message success';
            statusMessage.textContent = 'Files uploaded successfully!';
            loadFiles();
            uploadForm.reset();
            updateSelectedFiles();
            progressBar.style.width = '0%';
            progressText.textContent = '0%';
          } else {
            statusMessage.className = 'message error';
            statusMessage.textContent = 'Upload failed!';
          }
          uploadProgress.style.display = 'none';
        };
        xhr.onerror = function() {
          statusMessage.className = 'message error';
          statusMessage.textContent = 'Upload failed!';
          uploadProgress.style.display = 'none';
        };
        xhr.open('POST', '/');
        xhr.send(formData);
      } catch (error) {
        statusMessage.className = 'message error';
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
          // Create container for the file entry
          const fileDiv = document.createElement('div');
          fileDiv.className = 'file-item';
          
          // Container for file info with text-overflow
          const fileInfo = document.createElement('div');
          fileInfo.className = 'file-info';
          const fileLink = document.createElement('a');
          fileLink.href = '/' + file.name;
          fileLink.textContent = `${file.name} (${formatFileSize(file.size)})`;
          fileInfo.appendChild(fileLink);
          
          // Container for the buttons
          const buttonGroup = document.createElement('div');
          buttonGroup.className = 'button-group';
          
          const copyButton = document.createElement('button');
          copyButton.className = 'copy-button';
          copyButton.innerHTML = '<i class="fas fa-copy"></i>';
          copyButton.onclick = (e) => {
            e.preventDefault();
            navigator.clipboard.writeText(window.location.origin + '/' + file.name);
            copyButton.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
              copyButton.innerHTML = '<i class="fas fa-copy"></i>';
            }, 2000);
          };

          const downloadButton = document.createElement('a');
          downloadButton.className = 'download-button';
          downloadButton.href = '/' + file.name;
          downloadButton.setAttribute('download', '');
          downloadButton.innerHTML = '<i class="fas fa-download"></i>';

          buttonGroup.appendChild(copyButton);
          buttonGroup.appendChild(downloadButton);
          
          fileDiv.appendChild(fileInfo);
          fileDiv.appendChild(buttonGroup);
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
        self.add_security_headers()
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