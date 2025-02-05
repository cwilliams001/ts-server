# Secure File Sharing and Uploads with Tailscale Funnel

This project provides a simple and secure way to share files and accept file uploads over the internet using Python’s built-in HTTP server and **Tailscale Funnel**. The updated server now features an enhanced HTML upload interface with drag & drop support, real-time progress feedback, and a JSON API for listing available files.

## 🚀 Features
- **Enhanced File Sharing & Uploads:**
  - Serve files from any directory using Python’s built-in HTTP server.
  - Upload files via an intuitive HTML interface that supports drag & drop, multiple file selection, and real-time progress updates.
- **Secure Public Access via Tailscale Funnel:**
  - Expose your server safely to the internet using **Tailscale Funnel**.
- **Optional Basic Authentication:**
  - Protect your server with HTTP Basic authentication. When enabled, a random password is generated at startup.
- **JSON File Listing API:**
  - Access a JSON-formatted list of files (name and size) by visiting the `/list` endpoint.
- **Customizable:**
  - Easily set the port and the directory to serve/upload files from.

---

## 📝 Prerequisites
Ensure you have the following installed and set up:
- **Python 3.6+**
- **Tailscale** with **Tailscale Funnel** enabled.  
  _Tip: If you prefer not to run as root, run Tailscale as a non-root operator (e.g., `tailscale up --operator=$USER`)._

---

## 📥 Installation

1. **Clone the repository** or download the `ts-server.py` script.
2. Make sure you have **Python 3.6 or later** installed.
3. Install and configure **Tailscale** on your system.

---

## ⚙️ Usage

Run the script from any directory:

```bash
sudo python3 ts-server.py [port] [--auth] [--dir PATH]
```

- **`[port]` [optional]:** Port to run the server on (default: 8080).
- **`--auth` [optional]:** Enable basic authentication. When used, the server will generate and display a random password.
- **`--dir PATH` [optional]:** Specify the directory to serve and save files (default: current directory).

### 📂 Example Scenarios

1. **Serve the current directory** on the default port (8080):
   ```bash
   sudo python3 ts-server.py
   ```

2. **Serve files from a custom directory** (e.g., `/home/user/Documents`) on a specific port (9000):
   ```bash
   sudo python3 ts-server.py 9000 --dir /home/user/Documents
   ```

3. **Enable basic authentication** (serving the current directory):
   ```bash
   sudo python3 ts-server.py --auth
   ```
   On startup, the terminal will display something like:
   ```bash
   [INFO] Serving directory: /current/directory
   [INFO] Generated credentials - Username: user, Password: SPx8gDJdTVvp
   [INFO] Available on the internet:
   [INFO]
   [INFO] https://your-funnel-url.ts.net/
   [INFO] Share this link: https://your-funnel-url.ts.net/
   [INFO] ==================================================
   [INFO] Server Information:
   [INFO] --------------------------------------------------
   [INFO] Directory: /current/directory
   [INFO] Port: 8080
   [INFO]
   [INFO] Authentication Required:
   [INFO] --------------------------------------------------
   [INFO] Username: user
   [INFO] Password: SPx8gDJdTVvp
   [INFO] ==================================================
   
   ```

---

## 🌐 Web Interface & API Endpoints

### HTML Upload Page
- **Access:** Open `https://<your-funnel-url>/` in your browser.
- **Features:**
  - Drag & drop file uploads.
  - Multiple file selection.
  - Real-time upload progress.
  - Dynamic refresh of the file list.

### JSON File Listing
- **Endpoint:** `https://<your-funnel-url>/list`
- **Response:** A JSON array where each object contains the `name` and `size` (in bytes) of a file.

### File Download
- Download files by clicking on the file links in the HTML interface or directly visiting `https://<your-funnel-url>/<filename>`.

---

## 🔄 Uploading Files via Command Line

You can upload files using `curl` as well:

#### With Authentication:
```bash
curl -u user:<generated_password> -X POST -F "file=@/path/to/your/file.txt" https://<your-funnel-url>/
```

#### Without Authentication:
```bash
curl -X POST -F "file=@/path/to/your/file.txt" https://<your-funnel-url>/
```

---

## 🔑 Authentication

When you launch the server with the `--auth` flag, it generates a random password and requires basic authentication:
- **Username:** user
- **Password:** (Displayed in the terminal on startup)

---

## 🛑 Stopping the Server

To stop the HTTP server and the Tailscale Funnel process, press `Ctrl + C` in the terminal where the server is running. This will gracefully terminate both the server and the funnel.

---

## ⛑️ Security Considerations

- **Authentication:** Enable basic authentication when sharing sensitive or private files.
- **HTTPS:** While Tailscale Funnel secures the connection, keep in mind that Basic Authentication transmits credentials in Base64. Use it within trusted networks or over HTTPS.
- **Filename Sanitization:** Uploaded filenames are sanitized to prevent directory traversal attacks.
- **Content Control:** Only serve directories and files that you trust.

---

## 🆚 Troubleshooting

- **Tailscale Funnel Issues:**  
  Ensure Tailscale Funnel is active and properly configured.
- **Authentication Errors:**  
  Double-check that you’re using the correct generated password.
- **File Upload Failures:**  
  Verify that your file upload requests are encoded as `multipart/form-data`.

---

## Global Installation (Optional)

To run the script from anywhere on your system:

1. Create a symbolic link to the script:
   ```bash
   sudo ln -s /path/to/ts-server.py /usr/local/bin/ts-server
   ```
   Then use:
   ```bash
   sudo ts-server [arguments]
   ```

2. Alternatively, add the script’s directory to your system PATH by adding the following line to your `.bashrc` or `.zshrc`:
   ```bash
   export PATH=$PATH:/path/to/your/scripts
   ```

---

## 🌟 Additional Resources

- [Tailscale Funnel Documentation](https://tailscale.com/kb/1223/tailscale-funnel/)
- [Python HTTP Server Documentation](https://docs.python.org/3/library/http.server.html)

---

### Example Full Workflow

1. **Start the server with authentication:**
   ```bash
   sudo python3 ts-server.py --auth
   ```
   The terminal will display:
   ```
   [INFO] Serving directory: /current/directory
   [INFO] Generated credentials - Username: user, Password: SPx8gDJdTVvp
   [INFO] Available on the internet:
   [INFO]
   [INFO] https://your-funnel-url.ts.net/
   [INFO] Share this link: https://your-funnel-url.ts.net/
   [INFO] ==================================================
   [INFO] Server Information:
   [INFO] --------------------------------------------------
   [INFO] Directory: /current/directory
   [INFO] Port: 8080
   [INFO]
   [INFO] Authentication Required:
   [INFO] --------------------------------------------------
   [INFO] Username: user
   [INFO] Password: SPx8gDJdTVvp
   [INFO] ==================================================
   ```

2. **Upload a file via the HTML interface:**
   - Open `https://<your-funnel-url>/` in your browser.
   - Drag and drop your file(s) into the upload area and click "Upload Files".

3. **Upload a file via `curl` (with authentication):**
   ```bash
   curl -u user:<generated_password> -X POST -F "file=@/path/to/your/file.txt" https://<your-funnel-url>/
   ```

4. **Download a file:**
   - From the browser: Click the file link in the HTML interface.
   - From the command line:
     ```bash
     curl -u user:<generated_password> https://<your-funnel-url>/file.txt -O
     ```

