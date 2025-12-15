package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
)

// getAuthKey retrieves a Tailscale auth key using OAuth or from environment
func getAuthKey() (string, error) {
	// Check for direct auth key first
	if key := getDirectAuthKey(); key != "" {
		return key, nil
	}

	// Try OAuth flow
	clientID, clientSecret := getOAuthCredentials()
	if clientID != "" && clientSecret != "" {
		return generateAuthKeyViaOAuth(clientID, clientSecret, *tailnetName)
	}

	// No credentials found - will fall back to interactive login
	return "", nil
}

// getDirectAuthKey checks for a pre-generated auth key
func getDirectAuthKey() string {
	// Check flag first
	if *authKey != "" {
		return *authKey
	}
	// Check environment variable
	return os.Getenv("TS_AUTHKEY")
}

// getOAuthCredentials retrieves OAuth client ID and secret
func getOAuthCredentials() (string, string) {
	// Check flags first
	clientID := *oauthID
	clientSecret := *oauthSecret

	// Fall back to environment variables
	if clientID == "" {
		clientID = os.Getenv("TS_OAUTH_CLIENT_ID")
	}
	if clientSecret == "" {
		clientSecret = os.Getenv("TS_OAUTH_CLIENT_SECRET")
	}

	return clientID, clientSecret
}

// generateAuthKeyViaOAuth uses OAuth to generate an ephemeral auth key
func generateAuthKeyViaOAuth(clientID, clientSecret, tailnet string) (string, error) {
	// Step 1: Get OAuth access token
	accessToken, err := getOAuthAccessToken(clientID, clientSecret)
	if err != nil {
		return "", fmt.Errorf("failed to get OAuth access token: %w", err)
	}

	// Step 2: Generate auth key using the access token
	authKey, err := createAuthKey(accessToken, tailnet)
	if err != nil {
		return "", fmt.Errorf("failed to create auth key: %w", err)
	}

	return authKey, nil
}

// getOAuthAccessToken exchanges OAuth credentials for an access token
func getOAuthAccessToken(clientID, clientSecret string) (string, error) {
	data := url.Values{}
	data.Set("client_id", clientID)
	data.Set("client_secret", clientSecret)

	resp, err := http.PostForm("https://api.tailscale.com/api/v2/oauth/token", data)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("OAuth token request failed (status %d): %s", resp.StatusCode, body)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	var result struct {
		AccessToken string `json:"access_token"`
		TokenType   string `json:"token_type"`
		ExpiresIn   int    `json:"expires_in"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return "", err
	}

	if result.AccessToken == "" {
		return "", fmt.Errorf("no access token in response")
	}

	return result.AccessToken, nil
}

// createAuthKey uses the Tailscale API to create an ephemeral auth key
func createAuthKey(accessToken, tailnet string) (string, error) {
	// Prepare the request payload
	payload := map[string]interface{}{
		"capabilities": map[string]interface{}{
			"devices": map[string]interface{}{
				"create": map[string]interface{}{
					"reusable":      false,
					"ephemeral":     true,
					"preauthorized": true,
					"tags":          []string{"tag:fileserver"},
				},
			},
		},
		"expirySeconds": 3600, // 1 hour
		"description":   fmt.Sprintf("ts-server on %s", *hostname),
	}

	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return "", err
	}

	// Create the API request
	apiURL := fmt.Sprintf("https://api.tailscale.com/api/v2/tailnet/%s/keys", tailnet)
	req, err := http.NewRequest("POST", apiURL, strings.NewReader(string(payloadBytes)))
	if err != nil {
		return "", err
	}

	req.Header.Set("Authorization", "Bearer "+accessToken)
	req.Header.Set("Content-Type", "application/json")

	// Send the request
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("auth key creation failed (status %d): %s", resp.StatusCode, body)
	}

	var result struct {
		Key         string `json:"key"`
		ID          string `json:"id"`
		Description string `json:"description"`
		Created     string `json:"created"`
		Expires     string `json:"expires"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return "", err
	}

	if result.Key == "" {
		return "", fmt.Errorf("no auth key in response")
	}

	return result.Key, nil
}
