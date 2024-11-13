# Secure File Sharing with Tailscale Funnel

This project provides a simple and secure way to share files over the internet using Python's built-in HTTP server and Tailscale Funnel. It offers optional basic authentication for added security.

## Features

- Easy file sharing using Python's SimpleHTTPServer
- Integration with Tailscale Funnel for secure, public access
- Optional basic authentication
- Randomly generated password when authentication is enabled
- Customizable port selection

## Prerequisites

- Python 3.6+
- Tailscale installed and configured on your system
- Tailscale Funnel feature enabled for your account

## Installation

1. Clone this repository or download the `ts-server.py` script.
2. Ensure you have Python 3.6 or later installed.
3. Make sure Tailscale is installed and configured on your system.

## Usage

Run the script from the directory you want to share:

```
python3 file_share_auth.py [port] [--auth]
```

- `[port]`: Optional. Specify the port number (default is 8080).
- `--auth`: Optional flag. Enable basic authentication.

### Examples

1. Run on default port (8080) without authentication:
   ```
   python3 file_share_auth.py
   ```

2. Run on port 9000 without authentication:
   ```
   python3 file_share_auth.py 9000
   ```

3. Run on default port with authentication:
   ```
   python3 file_share_auth.py --auth
   ```

4. Run on port 8080 with authentication:
   ```
   python3 file_share_auth.py 8080 --auth
   ```

## Authentication

When the `--auth` flag is used, the script generates a random password. The username is always set to "user". The generated credentials will be displayed in the console when the server starts.

## Accessing Shared Files

After running the script, it will display a Tailscale Funnel URL. Share this URL with others to grant them access to the files in the directory where the script was run.

If authentication is enabled, users will need to enter the username and password when prompted by their browser.

## Stopping the Server

To stop the server and Tailscale Funnel, press Ctrl+C in the terminal where the script is running.

## Security Considerations

- Use authentication when sharing sensitive files.
- Be cautious about what files you're sharing.
- Remember that basic authentication sends credentials in base64 encoding, which is not secure over non-HTTPS connections.
- For production use, consider implementing more secure authentication methods.

## Troubleshooting

- Ensure Tailscale is running and connected.
- Verify that the Tailscale Funnel feature is enabled for your account.
