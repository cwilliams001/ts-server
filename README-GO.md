# TS File Server - Go Edition

**Cross-platform file sharing server with embedded Tailscale Funnel**

This is a Go rewrite of the Python ts-server, designed to run as a single self-contained binary on any platform (Windows, macOS, Linux, ARM, etc.) without requiring Python or a pre-installed Tailscale daemon.

## Key Features

- **Cross-Platform**: Single binary works on Windows, macOS, Linux, ARM, and more
- **Zero Dependencies**: No Python, no Tailscale installation required
- **Embedded Tailscale**: Uses tsnet to embed Tailscale directly in the app
- **OAuth Authentication**: Use Tailscale OAuth for seamless multi-system deployment
- **Secure by Default**: HTTPS via Tailscale Funnel, security headers, timing-safe auth
- **File Upload/Download**: Drag & drop HTML interface + curl support
- **Dark Theme UI**: Modern, responsive interface

## Prerequisites

**To build:**
- Go 1.21+ ([download](https://go.dev/dl/))

**To run:**
- Tailscale account (free tier works)
- OAuth client credentials OR auth key OR browser for interactive login

## Installation

### Option 1: Build from Source

```bash
# Install Go (Arch Linux example)
sudo pacman -S go

# Clone and build
git clone https://github.com/cwilliams001/ts-server
cd ts-server
git checkout feature/go-tsnet-rewrite

# Initialize Go module
go mod init github.com/cwilliams001/ts-server
go mod tidy

# Build for your platform
go build -o ts-server

# Or build for all platforms
./build.sh
```

### Option 2: Download Pre-built Binary

*(Coming soon - will be available in GitHub Releases)*

```bash
# Linux amd64
wget https://github.com/cwilliams001/ts-server/releases/download/v2.0.0/ts-server-linux-amd64
chmod +x ts-server-linux-amd64

# macOS arm64
wget https://github.com/cwilliams001/ts-server/releases/download/v2.0.0/ts-server-darwin-arm64
chmod +x ts-server-darwin-arm64

# Windows amd64
curl -O https://github.com/cwilliams001/ts-server/releases/download/v2.0.0/ts-server-windows-amd64.exe
```

## Authentication Setup

### Recommended: OAuth Client (Multi-System)

**One-time setup:**

1. Create OAuth client at https://login.tailscale.com/admin/settings/oauth
   - Click "Generate OAuth client"
   - **Scopes**: `devices:write`
   - **Tags**: `tag:fileserver` (create if doesn't exist)
   - Copy **Client ID** and **Client Secret**

2. Set environment variables (add to `~/.bashrc` or `~/.zshrc`):
   ```bash
   export TS_OAUTH_CLIENT_ID=your-client-id-here
   export TS_OAUTH_CLIENT_SECRET=your-client-secret-here
   ```

3. Run on any system:
   ```bash
   ./ts-server --dir ~/Documents
   ```

**Benefits:**
- Same credentials work on all systems
- No manual auth key generation
- Centrally revokable
- Auto-generates ephemeral keys

### Alternative: Auth Key

```bash
# Generate at https://login.tailscale.com/admin/settings/keys
TS_AUTHKEY=tskey-auth-xxx ./ts-server
```

### Alternative: Interactive Login

```bash
# No credentials - opens browser login
./ts-server
# Visit the displayed URL to authenticate
```

## Usage

### Basic Usage

```bash
# Serve current directory
./ts-server

# Serve specific directory
./ts-server --dir ~/Downloads

# Enable HTTP basic auth (generates random password)
./ts-server --auth

# Custom hostname
./ts-server --hostname myfileserver

# All options
./ts-server \
  --dir ~/files \
  --hostname fileserver \
  --auth \
  --port 443 \
  --state ~/.ts-server-state
```

### Command-Line Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--dir` | `.` | Directory to serve and save files |
| `--hostname` | `fileserver` | Tailscale hostname |
| `--auth` | `false` | Enable HTTP basic authentication |
| `--port` | `443` | Port to listen on |
| `--state` | `~/.ts-server` | State directory for Tailscale credentials |
| `--oauth-id` | - | OAuth client ID (or use `TS_OAUTH_CLIENT_ID`) |
| `--oauth-secret` | - | OAuth client secret (or use `TS_OAUTH_CLIENT_SECRET`) |
| `--authkey` | - | Auth key (or use `TS_AUTHKEY`) |
| `--tailnet` | `-` | Tailnet name (default: primary) |
| `--version` | - | Show version and exit |

### Upload Files

**Via Browser:**
1. Open the public URL (displayed when server starts)
2. Drag & drop files or click to select
3. Click "Upload Files"

**Via curl:**
```bash
# Without auth
curl -X POST -F "file=@document.pdf" https://your-url.ts.net/

# With auth
curl -u user:password -X POST -F "file=@document.pdf" https://your-url.ts.net/

# Multiple files
curl -X POST -F "file=@file1.txt" -F "file=@file2.pdf" https://your-url.ts.net/
```

### Download Files

**Via Browser:**
- Click file name or download button

**Via curl:**
```bash
curl https://your-url.ts.net/document.pdf -O

# With auth
curl -u user:password https://your-url.ts.net/document.pdf -O
```

### List Files (JSON)

```bash
curl https://your-url.ts.net/list

# Returns:
# [{"name":"file1.txt","size":1024},{"name":"file2.pdf","size":2048}]
```

## Building for Multiple Platforms

Use the included build script:

```bash
./build.sh
```

This creates binaries for:
- Linux (amd64, arm64)
- macOS (amd64, arm64)
- Windows (amd64, arm64)
- FreeBSD (amd64)

Binaries are placed in `./build/` directory.

**Manual cross-compilation:**
```bash
# Linux
GOOS=linux GOARCH=amd64 go build -o ts-server-linux-amd64

# macOS
GOOS=darwin GOARCH=arm64 go build -o ts-server-darwin-arm64

# Windows
GOOS=windows GOARCH=amd64 go build -o ts-server-windows-amd64.exe

# Raspberry Pi
GOOS=linux GOARCH=arm64 go build -o ts-server-linux-arm64
```

## Security Features

- **HTTPS**: All traffic encrypted via Tailscale Funnel
- **Security Headers**: XSS protection, clickjacking prevention, etc.
- **Timing-Safe Auth**: Constant-time comparison prevents timing attacks
- **Filename Sanitization**: Prevents path traversal and dangerous characters
- **Ephemeral Keys**: OAuth-generated keys auto-expire
- **Tagged Devices**: All instances tagged for easy ACL management

## Comparison: Python vs Go

| Feature | Python Version | Go Version |
|---------|---------------|------------|
| **Dependencies** | Python + Tailscale CLI | None (self-contained) |
| **Binary Size** | N/A (script) | ~15-20MB |
| **Platforms** | Any with Python | Linux, macOS, Windows, ARM, BSD |
| **Tailscale** | External daemon required | Embedded via tsnet |
| **Deployment** | Copy script + install deps | Copy single binary |
| **Performance** | Interpreted | Compiled (faster) |
| **Funnel Setup** | Subprocess call | Native API |
| **OAuth Support** | No | Yes |

## Migrating from Python Version

The Go version is **feature-complete** and maintains compatibility:

- Same HTML interface
- Same API endpoints (`/`, `/list`)
- Same upload/download behavior
- Same authentication flow
- Same security features

**Differences:**
- No need for `sudo` (tsnet doesn't require root)
- No need for Tailscale pre-installed
- OAuth support for easier multi-system deployment
- Faster startup and lower memory usage

## Example: Multi-System Deployment

**Setup once:**
```bash
# On your first system
export TS_OAUTH_CLIENT_ID=k12ABC...
export TS_OAUTH_CLIENT_SECRET=tscs-k12XYZ...
```

**Deploy everywhere:**
```bash
# Laptop (macOS)
./ts-server-darwin-arm64 --hostname laptop-share --dir ~/Desktop

# VPS (Linux)
./ts-server-linux-amd64 --hostname vps-share --dir /data/public

# Home Server (Raspberry Pi)
./ts-server-linux-arm64 --hostname homeserver-share --dir /mnt/storage

# Windows PC
ts-server-windows-amd64.exe --hostname win-share --dir C:\Share
```

Each gets its own public URL:
- `https://laptop-share.your-tailnet.ts.net`
- `https://vps-share.your-tailnet.ts.net`
- `https://homeserver-share.your-tailnet.ts.net`
- `https://win-share.your-tailnet.ts.net`

## Troubleshooting

**"OAuth credentials not found"**
- Set `TS_OAUTH_CLIENT_ID` and `TS_OAUTH_CLIENT_SECRET` environment variables
- Or use `--oauth-id` and `--oauth-secret` flags
- Or use an auth key with `TS_AUTHKEY`

**"Failed to start Funnel"**
- Ensure your Tailscale account has Funnel enabled
- Check firewall/network allows outbound HTTPS
- Verify OAuth client has correct scopes (`devices:write`)

**"Permission denied" on port 443**
- Go version doesn't need sudo (tsnet handles privileged ports)
- If still having issues, use `--port 8080` or another high port

**"Device already exists"**
- Use a different `--hostname`
- Or delete old device from Tailscale admin console
- Or use `--state` to specify different state directory

## Additional Resources

- [tsnet Documentation](https://tailscale.com/kb/1244/tsnet)
- [Tailscale Funnel](https://tailscale.com/kb/1223/tailscale-funnel)
- [OAuth Clients](https://tailscale.com/kb/1215/oauth-clients)
- [Tailscale ACLs](https://tailscale.com/kb/1018/acls)

## License

Same as the Python version - see main repository for license details.

## Contributing

Contributions welcome! Please submit issues or PRs to the main repository.

---

**Questions?** Open an issue or check the Tailscale documentation.
