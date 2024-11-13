Got it! Let's make the README more **user-friendly** and **organized** with clearer sections, concise explanations, and examples. We'll structure it to provide a quick overview of usage, features, and common scenarios (like file serving/uploading with or without authentication), keeping in mind both simplicity and completeness.

---

# Secure File Sharing and Uploads with Tailscale Funnel

This project provides a simple and secure way to serve files and accept file uploads over the internet using Python's built-in HTTP server and **Tailscale Funnel**. Optional authentication allows restricted access to prevent unauthorized file downloads and uploads.

## 🚀 Features
- **Easy File Sharing:** Share files using Python’s `SimpleHTTPRequestHandler`.
- **Secure, Public Access via Tailscale Funnel:** Integrated with **Tailscale Funnel** to expose the server securely to the public.
- **File Uploads with Dynamic Filenames:** Supports file uploads and saves uploaded files with their original names.
- **Optional Basic Authentication:** Protect your shared content with basic authentication (username & password).
- **Customizable:** Set the port and the directory to serve or upload files to.

---

## 📝 Prerequisites
Make sure the following are installed and set up:

- Python 3.6+  
- **Tailscale** installed and configured on your system (with **Tailscale Funnel** feature enabled).
- If running under root is not preferred, run Tailscale as a non-root operator (example: `'tailscale up --operator=$USER'`).

---

## 📥 Installation

1. **Clone the repository** or manually download the `ts-server.py` script.
2. Ensure you have **Python 3.6 or later** installed.
3. Make sure **Tailscale** is installed and configured on your system.

---

## ⚙️ Usage

Run the script from any directory:

```bash
sudo python3 ts-server.py [port] [--auth] [--dir PATH]
```

- **`[port]` [optional]**: Specify the port to use (default: 8080).
- **`--auth` [optional]**: Enables basic authentication for added security.
- **`--dir PATH` [optional]**: Specify which directory to serve / save files to. Defaults to the current directory.

### 📂 Example Scenarios:

1. **Serve the current directory** on the default port (8080):
   ```bash
   sudo python3 ts-server.py
   ```

2. **Serve files from a custom directory** (e.g., `/home/user/Documents`) on a specified port (9000):
   ```bash
   sudo python3 ts-server.py 9000 --dir /home/user/Documents
   ```

3. **Add basic authentication** with random password generation, serving the current directory:
   ```bash
   sudo python3 ts-server.py --auth
   ```

   Output:
   ```
   Generated Credentials:
   Username: user
   Password: FjK2kjsdaT2M
   ```

---

## 🔄 Uploading Files

Users can upload files to the server. The uploaded files will be saved with their **original filenames** in the directory being served.

### Uploading Files Using `curl`:

#### With Authentication:
If **authentication** is enabled, the following command will upload a file:
```bash
curl -u user:generated_password -X POST -F "file=@/path/to/your/test-file.txt" https://your-funnel-url/
```

#### Without Authentication:
If no authentication is enabled:
```bash
curl -X POST -F "file=@/path/to/your/test-file.txt" https://your-funnel-url/
```

---

## 🔑 Authentication

If launched with the `--auth` flag, the server will generate a **random password** and require basic authentication (username: **user**, password: generated). The credentials will be shown in the terminal where the server is running.

- Example credentials:
  ```bash
  Username: user
  Password: FjK2kjsdaT2M
  ```

---

## 🗂️ Accessing Shared and Uploaded Files

To access shared and uploaded files, users can use the **Tailscale Funnel** link provided in the server’s terminal output.

- **Download via Browser**: Visit the link in a web browser to browse or download files.
- **Download via `curl`** (with authentication):
  ```bash
  curl -u user:generated_password https://your-funnel-url/test-file.txt -O
  ```

### Download Example:
```bash
curl -u user:FjK2kjsdaT2M https://your-funnel-url/test-file.txt -O
```

---

## 🛑 Stopping the Server

To stop both the server and the **Tailscale Funnel**, press `Ctrl + C` in the terminal where the Python server is running. This will terminate the Python HTTP server and reset the Funnel.

---

## ⛑️ Security Considerations

- **Use authentication** for private or sensitive file sharing.
- Be cautious about **what files you're serving** or accepting via uploads.
- **Basic Authentication** sends credentials in base64, so it’s recommended to enable HTTPS or use it within trusted networks via Tailscale.
- **Sanitization**: Uploaded files will be sanitized to prevent directory traversal attacks.

---

## 🆚 Troubleshooting

- **Ensure Tailscale Funnel is active**: Confirm that **Tailscale Funnel** is enabled and running.
- **Authentication Issues**: Double-check that the password generated at startup is being used correctly when uploading or downloading files.
- **File uploads failing**: Make sure you are using `multipart/form-data` when uploading with `curl` or Python.

---

## Global Installation (Optional)

To run the script globally from anywhere on your system:
1. Create a **symbolic link** to the script:
   ```bash
   sudo ln -s /path/to/ts-server.py /usr/local/bin/ts-server
   ```

   Then, use it like this:
   ```bash
   sudo ts-server [arguments]
   ```

2. Alternatively, add the script's folder to your **system PATH** by adding the following line to `.bashrc` or `.zshrc`:
   ```bash
   export PATH=$PATH:/path/to/your/scripts
   ```

After this setup, you can run the server from any directory.

---

## 🌐 Additional Resources

Learn more about **Tailscale Funnel** and its setup from the official [Tailscale documentation](https://tailscale.com/kb/1223/tailscale-funnel/).

---

### Example Full Workflow

1. **Start server with authentication**:
   ```bash
   sudo python3 ts-server.py --auth
   ```

2. **Upload a file**:
   ```bash
   curl -u user:FjK2kjsdaT2M -X POST -F "file=@/path/to/your/test-file.txt" https://your-funnel-url/
   ```

3. **Download a file**:
   ```bash
   curl -u user:FjK2kjsdaT2M https://your-funnel-url/test-file.txt -O
   ```

