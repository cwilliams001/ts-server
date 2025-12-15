package main

import (
	"crypto/rand"
	"crypto/subtle"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"html/template"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"tailscale.com/tsnet"
)

const version = "2.0.0-go"

// ANSI color codes
const (
	colorReset  = "\033[0m"
	colorRed    = "\033[31m"
	colorGreen  = "\033[32m"
	colorYellow = "\033[33m"
	colorBlue   = "\033[34m"
	colorPurple = "\033[35m"
	colorCyan   = "\033[36m"
	colorGray   = "\033[90m"
	colorBold   = "\033[1m"
)

const banner = `
 _____ ____        ____
|_   _/ ___|      / ___|  ___ _ ____   _____ _ __
  | | \___ \ _____\___ \ / _ \ '__\ \ / / _ \ '__|
  | |  ___) |_____|___) |  __/ |   \ V /  __/ |
  |_| |____/      |____/ \___|_|    \_/ \___|_|
`

var (
	// Command-line flags
	port         = flag.Int("port", 443, "Port to listen on")
	serveDir     = flag.String("dir", ".", "Directory to serve and save files")
	useAuth      = flag.Bool("auth", false, "Enable HTTP basic authentication")
	hostname     = flag.String("hostname", "fileserver", "Tailscale hostname")
	stateDir     = flag.String("state", "", "State directory (default: ~/.ts-server)")
	oauthID      = flag.String("oauth-id", "", "Tailscale OAuth client ID (or use TS_OAUTH_CLIENT_ID)")
	oauthSecret  = flag.String("oauth-secret", "", "Tailscale OAuth client secret (or use TS_OAUTH_CLIENT_SECRET)")
	authKey      = flag.String("authkey", "", "Tailscale auth key (or use TS_AUTHKEY)")
	tailnetName  = flag.String("tailnet", "-", "Tailscale tailnet name (default: primary tailnet)")
	showVersion  = flag.Bool("version", false, "Show version and exit")

	// Runtime configuration
	httpUsername = "user"
	httpPassword = ""
)

// FileInfo represents a file in the directory
type FileInfo struct {
	Name string `json:"name"`
	Size int64  `json:"size"`
}

// Server holds the application state
type Server struct {
	dir     string
	useAuth bool
}

func main() {
	flag.Parse()

	if *showVersion {
		fmt.Printf("ts-server version %s\n", version)
		os.Exit(0)
	}

	// Set default state directory
	if *stateDir == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			log.Fatal("Failed to get home directory:", err)
		}
		*stateDir = filepath.Join(home, ".ts-server")
	}

	// Validate and prepare serve directory
	absDir, err := filepath.Abs(*serveDir)
	if err != nil {
		log.Fatal("Invalid directory:", err)
	}
	if stat, err := os.Stat(absDir); err != nil || !stat.IsDir() {
		log.Fatalf("Directory does not exist: %s", absDir)
	}

	// Change to serve directory
	if err := os.Chdir(absDir); err != nil {
		log.Fatal("Failed to change to directory:", err)
	}

	// Print banner
	fmt.Print(colorCyan + banner + colorReset)
	fmt.Printf("%s[*]%s TS-Server v%s - Cross-platform file sharing via Tailscale Funnel\n", colorGray, colorReset, version)
	fmt.Println()

	log.Printf("%s[+]%s Serving directory: %s", colorGreen, colorReset, absDir)

	// Generate password if authentication is enabled
	if *useAuth {
		httpPassword = generatePassword(12)
		log.Printf("%s[+]%s Authentication enabled", colorYellow, colorReset)
		log.Printf("    Username: %s%s%s", colorCyan, httpUsername, colorReset)
		log.Printf("    Password: %s%s%s", colorCyan, httpPassword, colorReset)
	}

	// Get Tailscale auth key (OAuth or direct)
	tsAuthKey, err := getAuthKey()
	if err != nil {
		log.Printf("%s[!]%s %s", colorRed, colorReset, err)
		printAuthHelp()
		os.Exit(1)
	}

	// Start tsnet server
	log.Printf("%s[*]%s Authenticating with Tailscale...", colorBlue, colorReset)

	ts := &tsnet.Server{
		Dir:      *stateDir,
		Hostname: *hostname,
		AuthKey:  tsAuthKey,
		Logf:     func(format string, args ...any) {
			// Suppress verbose tsnet logs
			// Only show critical errors, not warnings or informational messages
			lower := strings.ToLower(format)

			// Filter out common non-critical messages
			if strings.Contains(lower, "warning") ||
			   strings.Contains(lower, "health(") ||
			   strings.Contains(lower, "magicsock") ||
			   strings.Contains(lower, "tsnet running") ||
			   strings.Contains(lower, "tsnet starting") ||
			   strings.Contains(lower, "warming-up") ||
			   strings.Contains(lower, "dns") {
				return
			}

			// Show critical errors only
			if strings.Contains(lower, "fatal") ||
			   strings.Contains(lower, "panic") ||
			   (strings.Contains(lower, "error") && !strings.Contains(lower, "health(")) {
				log.Printf(format, args...)
			}
		},
	}
	defer ts.Close()

	// Start Funnel listener
	ln, err := ts.ListenFunnel("tcp", fmt.Sprintf(":%d", *port))
	if err != nil {
		log.Fatalf("%s[!]%s Failed to start Funnel: %v", colorRed, colorReset, err)
	}
	defer ln.Close()

	// Get public URL
	domains := ts.CertDomains()
	if len(domains) > 0 {
		publicURL := fmt.Sprintf("https://%s", domains[0])
		fmt.Println()
		fmt.Println(colorGreen + strings.Repeat("─", 70) + colorReset)
		fmt.Printf("%s%s[✓] Server Online%s\n", colorBold, colorGreen, colorReset)
		fmt.Println(colorGreen + strings.Repeat("─", 70) + colorReset)
		fmt.Printf("  %sPublic URL:%s  %s%s%s\n", colorGray, colorReset, colorCyan, publicURL, colorReset)
		fmt.Printf("  %sDirectory:%s   %s\n", colorGray, colorReset, absDir)
		fmt.Printf("  %sPort:%s        %d\n", colorGray, colorReset, *port)
		if *useAuth {
			fmt.Println()
			fmt.Printf("  %s[AUTH REQUIRED]%s\n", colorYellow, colorReset)
			fmt.Printf("  %sUsername:%s %s%s%s\n", colorGray, colorReset, colorCyan, httpUsername, colorReset)
			fmt.Printf("  %sPassword:%s %s%s%s\n", colorGray, colorReset, colorCyan, httpPassword, colorReset)
		}
		fmt.Println(colorGreen + strings.Repeat("─", 70) + colorReset)
		fmt.Println()
		fmt.Printf("%s[→]%s Share this link (accessible from anywhere):\n", colorPurple, colorReset)
		fmt.Printf("    %s%s%s\n\n", colorBold+colorCyan, publicURL, colorReset)
	}

	// Create HTTP server
	srv := &Server{
		dir:     absDir,
		useAuth: *useAuth,
	}

	// Serve HTTP requests with logging middleware
	if err := http.Serve(ln, loggingMiddleware(srv)); err != nil {
		log.Fatalf("%s[!]%s HTTP server error: %v", colorRed, colorReset, err)
	}
}

// responseWriter wraps http.ResponseWriter to capture status code
type responseWriter struct {
	http.ResponseWriter
	statusCode int
	written    bool
}

func (rw *responseWriter) WriteHeader(code int) {
	if !rw.written {
		rw.statusCode = code
		rw.written = true
		rw.ResponseWriter.WriteHeader(code)
	}
}

func (rw *responseWriter) Write(b []byte) (int, error) {
	if !rw.written {
		rw.statusCode = http.StatusOK
		rw.written = true
	}
	return rw.ResponseWriter.Write(b)
}

// loggingMiddleware logs HTTP requests
func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Get client IP (handle both direct and forwarded connections)
		clientIP := r.RemoteAddr
		if colon := strings.LastIndex(clientIP, ":"); colon != -1 {
			clientIP = clientIP[:colon]
		}
		if strings.HasPrefix(clientIP, "[") && strings.HasSuffix(clientIP, "]") {
			clientIP = clientIP[1 : len(clientIP)-1]
		}

		// Wrap the response writer to capture status code
		rw := &responseWriter{
			ResponseWriter: w,
			statusCode:     http.StatusOK,
		}

		// Serve the request
		next.ServeHTTP(rw, r)

		// Log the request with color-coded status
		statusColor := colorGreen
		if rw.statusCode >= 400 && rw.statusCode < 500 {
			statusColor = colorYellow
		} else if rw.statusCode >= 500 {
			statusColor = colorRed
		}

		log.Printf("%s%-15s%s %s%-4s%s %s%3d%s %s",
			colorGray, clientIP, colorReset,
			colorCyan, r.Method, colorReset,
			statusColor, rw.statusCode, colorReset,
			r.URL.Path)
	})
}

// ServeHTTP implements http.Handler
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Add security headers
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("X-Frame-Options", "DENY")
	w.Header().Set("X-XSS-Protection", "1; mode=block")
	w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")

	// Check authentication
	if s.useAuth && !s.checkAuth(r) {
		w.Header().Set("WWW-Authenticate", `Basic realm="Restricted Access"`)
		http.Error(w, "Authentication required", http.StatusUnauthorized)
		return
	}

	// Route requests
	switch r.Method {
	case http.MethodGet:
		s.handleGet(w, r)
	case http.MethodPost:
		s.handlePost(w, r)
	default:
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
	}
}

// checkAuth validates HTTP Basic authentication
func (s *Server) checkAuth(r *http.Request) bool {
	auth := r.Header.Get("Authorization")
	if auth == "" {
		return false
	}

	// Parse Basic auth header
	const prefix = "Basic "
	if !strings.HasPrefix(auth, prefix) {
		return false
	}

	decoded, err := base64.StdEncoding.DecodeString(auth[len(prefix):])
	if err != nil {
		return false
	}

	parts := strings.SplitN(string(decoded), ":", 2)
	if len(parts) != 2 {
		return false
	}

	username, password := parts[0], parts[1]

	// Constant-time comparison to prevent timing attacks
	usernameMatch := subtle.ConstantTimeCompare([]byte(username), []byte(httpUsername)) == 1
	passwordMatch := subtle.ConstantTimeCompare([]byte(password), []byte(httpPassword)) == 1

	return usernameMatch && passwordMatch
}

// handleGet serves files and the upload page
func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	// JSON file list endpoint
	if r.URL.Path == "/list" {
		s.handleList(w, r)
		return
	}

	// Root path - serve upload page
	if r.URL.Path == "/" {
		s.handleUploadPage(w, r)
		return
	}

	// Serve static files
	http.ServeFile(w, r, filepath.Join(s.dir, filepath.Clean(r.URL.Path)))
}

// handleList returns JSON list of files
func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	files, err := os.ReadDir(s.dir)
	if err != nil {
		http.Error(w, "Failed to read directory", http.StatusInternalServerError)
		return
	}

	var fileList []FileInfo
	for _, file := range files {
		if file.IsDir() || strings.HasPrefix(file.Name(), ".") {
			continue
		}
		info, err := file.Info()
		if err != nil {
			continue
		}
		fileList = append(fileList, FileInfo{
			Name: file.Name(),
			Size: info.Size(),
		})
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(fileList)
}

// handlePost handles file uploads
func (s *Server) handlePost(w http.ResponseWriter, r *http.Request) {
	// Parse multipart form (32MB max)
	if err := r.ParseMultipartForm(32 << 20); err != nil {
		http.Error(w, "Failed to parse form", http.StatusBadRequest)
		return
	}

	files := r.MultipartForm.File["file"]
	if len(files) == 0 {
		http.Error(w, "No files uploaded", http.StatusBadRequest)
		return
	}

	savedCount := 0
	for _, fileHeader := range files {
		// Open uploaded file
		file, err := fileHeader.Open()
		if err != nil {
			log.Printf("Failed to open uploaded file: %v", err)
			continue
		}

		// Sanitize filename
		safeFilename := sanitizeFilename(fileHeader.Filename)
		if safeFilename == "" {
			file.Close()
			continue
		}

		// Save file
		dst, err := os.Create(filepath.Join(s.dir, safeFilename))
		if err != nil {
			log.Printf("Failed to create file %s: %v", safeFilename, err)
			file.Close()
			continue
		}

		_, err = io.Copy(dst, file)
		dst.Close()
		file.Close()

		if err != nil {
			log.Printf("Failed to save file %s: %v", safeFilename, err)
			continue
		}

		log.Printf("%s[↓]%s Received: %s", colorGreen, colorReset, safeFilename)
		savedCount++
	}

	if savedCount > 0 {
		w.Header().Set("Content-Type", "text/plain")
		fmt.Fprintf(w, "File(s) received and saved successfully.\n")
	} else {
		http.Error(w, "No valid files were uploaded", http.StatusBadRequest)
	}
}

// handleUploadPage serves the HTML upload interface
func (s *Server) handleUploadPage(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	tmpl := template.Must(template.New("upload").Parse(uploadPageHTML))
	tmpl.Execute(w, nil)
}

// sanitizeFilename removes dangerous characters from filenames
func sanitizeFilename(filename string) string {
	if filename == "" {
		return ""
	}

	// Get basename (remove any path components)
	safe := filepath.Base(filename)

	// Remove dangerous characters
	re := regexp.MustCompile(`[<>:"/\\|?*\x00-\x1f]`)
	safe = re.ReplaceAllString(safe, "_")

	// Check for edge cases
	if safe == "" || safe == "." || safe == ".." {
		safe = fmt.Sprintf("uploaded_file_%s", randomHex(4))
	}

	// Prevent hidden files and reserved names
	reservedNames := []string{"con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "lpt1", "lpt2"}
	lowerSafe := strings.ToLower(safe)
	if strings.HasPrefix(safe, ".") {
		safe = "file_" + safe
	}
	for _, reserved := range reservedNames {
		if lowerSafe == reserved {
			safe = "file_" + safe
			break
		}
	}

	return safe
}

// generatePassword creates a random password
func generatePassword(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, length)
	rand.Read(b)
	for i := range b {
		b[i] = charset[int(b[i])%len(charset)]
	}
	return string(b)
}

// randomHex generates random hex string
func randomHex(n int) string {
	b := make([]byte, n)
	rand.Read(b)
	return fmt.Sprintf("%x", b)
}

// printAuthHelp shows authentication setup instructions
func printAuthHelp() {
	fmt.Println()
	fmt.Println(colorYellow + "┌─────────────────────────────────────────────────────────────────┐" + colorReset)
	fmt.Println(colorYellow + "│" + colorReset + "  AUTHENTICATION SETUP REQUIRED                                  " + colorYellow + "│" + colorReset)
	fmt.Println(colorYellow + "└─────────────────────────────────────────────────────────────────┘" + colorReset)
	fmt.Println()
	fmt.Printf("%s[1]%s OAuth Client %s(Recommended for multiple systems)%s\n", colorCyan, colorReset, colorGray, colorReset)
	fmt.Println("    1. Create OAuth client:")
	fmt.Println("       https://login.tailscale.com/admin/settings/oauth")
	fmt.Printf("       %s- Scopes:%s devices:write\n", colorGray, colorReset)
	fmt.Printf("       %s- Tags:%s tag:fileserver\n", colorGray, colorReset)
	fmt.Println("    2. Export credentials:")
	fmt.Printf("       %sexport TS_OAUTH_CLIENT_ID=<client-id>%s\n", colorGreen, colorReset)
	fmt.Printf("       %sexport TS_OAUTH_CLIENT_SECRET=<client-secret>%s\n", colorGreen, colorReset)
	fmt.Println()
	fmt.Printf("%s[2]%s Auth Key %s(Simple, single system)%s\n", colorCyan, colorReset, colorGray, colorReset)
	fmt.Println("    1. Generate key:")
	fmt.Println("       https://login.tailscale.com/admin/settings/keys")
	fmt.Println("    2. Run:")
	fmt.Printf("       %sTS_AUTHKEY=<key> ./ts-server%s\n", colorGreen, colorReset)
	fmt.Println()
	fmt.Printf("%s[3]%s Interactive Login %s(Browser-based)%s\n", colorCyan, colorReset, colorGray, colorReset)
	fmt.Println("    Run without credentials and follow the browser link")
	fmt.Println()
}
