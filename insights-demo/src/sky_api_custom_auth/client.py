"""
Blackbaud API OAuth 2.0 Core Client

This module contains the shared logic for Blackbaud API authentication,
token management, and making authenticated requests.
"""

import json
import time
import urllib.request
import urllib.parse
import urllib.error
import http.server
from pathlib import Path
from typing import Optional, Dict, Any

# Define a default path for token storage relative to the project root
DEFAULT_TOKEN_PATH = Path(__file__).parent.parent / "data" / "blackbaud_tokens.json"

class BlackbaudOAuth:
    """
    Handles OAuth 2.0 authentication flow for Blackbaud API.
    """
    
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str = "http://localhost:8080/callback",
        environment: str = "sandbox"
    ):
        """
        Initialize Blackbaud OAuth client.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        
        # Blackbaud API endpoints
        self.auth_url = "https://oauth2.sky.blackbaud.com/authorization"
        self.token_url = "https://oauth2.sky.blackbaud.com/token"
        self.api_base = "https://api.sky.blackbaud.com"
        
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        
    def get_authorization_url(self, subscription_key: str) -> str:
        """
        Generate the authorization URL for OAuth flow.
        """
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'subscription_key': subscription_key
        }
        
        query_string = urllib.parse.urlencode(params)
        return f"{self.auth_url}?{query_string}"
    
    def exchange_code_for_token(self, authorization_code: str, subscription_key: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        """
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Bb-Api-Subscription-Key': subscription_key
        }
        
        data_encoded = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(self.token_url, data=data_encoded, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                token_data = json.loads(response.read().decode())
                self._update_token_state(token_data)
                return token_data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"Token exchange failed: {e.code} - {error_body}")
    
    def refresh_access_token(self, subscription_key: str) -> Dict[str, Any]:
        """
        Refresh the access token using refresh token.
        """
        if not self.refresh_token:
            raise Exception("No refresh token available. Please re-authenticate.")
        
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Bb-Api-Subscription-Key': subscription_key
        }
        
        data_encoded = urllib.parse.urlencode(data).encode('utf-8')
        req = urllib.request.Request(self.token_url, data=data_encoded, headers=headers)
        
        try:
            with urllib.request.urlopen(req) as response:
                token_data = json.loads(response.read().decode())
                self._update_token_state(token_data)
                return token_data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"Token refresh failed: {e.code} - {error_body}")

    def _update_token_state(self, token_data: Dict[str, Any]):
        """Internal helper to update class state from token response."""
        self.access_token = token_data.get('access_token')
        if 'refresh_token' in token_data:
            self.refresh_token = token_data.get('refresh_token')
        expires_in = token_data.get('expires_in', 3600)
        self.token_expires_at = time.time() + expires_in
    
    def is_token_expired(self) -> bool:
        """Check if the access token is expired or about to expire (within 5 mins)."""
        if not self.token_expires_at or not self.access_token:
            return True
        return time.time() >= (self.token_expires_at - 300)
    
    def ensure_valid_token(self, subscription_key: str):
        """Ensure we have a valid access token, refreshing if necessary."""
        if self.is_token_expired():
            if self.refresh_token:
                self.refresh_access_token(subscription_key)
            else:
                raise Exception("Token expired and no refresh token available. Please re-authenticate.")
    
    def make_authenticated_request(
        self,
        endpoint: str,
        subscription_key: str,
        method: str = 'GET',
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated API request to Blackbaud API.
        """
        self.ensure_valid_token(subscription_key)
        
        url = f"{self.api_base}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Bb-Api-Subscription-Key': subscription_key,
            'Content-Type': 'application/json'
        }
        
        if data:
            data_encoded = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=data_encoded, headers=headers)
        else:
            req = urllib.request.Request(url, headers=headers)
        
        req.get_method = lambda: method
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise Exception(f"API request failed: {e.code} - {error_body}")
    
    def save_tokens(self, filepath: Optional[str] = None):
        """Save tokens to a file for persistence."""
        token_path = Path(filepath) if filepath else DEFAULT_TOKEN_PATH
        token_path.parent.mkdir(parents=True, exist_ok=True)
        
        token_data = {
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_expires_at': self.token_expires_at
        }
        with open(token_path, 'w') as f:
            json.dump(token_data, f, indent=2)
    
    def load_tokens(self, filepath: Optional[str] = None):
        """Load tokens from a file."""
        token_path = Path(filepath) if filepath else DEFAULT_TOKEN_PATH
        try:
            with open(token_path, 'r') as f:
                token_data = json.load(f)
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_expires_at = token_data.get('token_expires_at')
        except (FileNotFoundError, json.JSONDecodeError):
            pass 


class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP server handler to receive OAuth callback."""
    
    def __init__(self, *args, auth_code_callback=None, **kwargs):
        self.auth_code_callback = auth_code_callback
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET request from OAuth redirect."""
        if self.path.startswith('/callback'):
            query_params = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query_params)
            
            if 'code' in params:
                code = params['code'][0]
                if self.auth_code_callback:
                    self.auth_code_callback(code)
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Authentication successful!</h1><p>You can close this window.</p></body></html>')
            else:
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Authentication failed</h1></body></html>')
        else:
            self.send_response(404)
            self.end_headers()
