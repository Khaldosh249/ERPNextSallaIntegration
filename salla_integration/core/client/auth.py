"""
OAuth 2.0 authentication handler for Salla API.
Handles token management, refresh, and OAuth flow.
"""

import frappe
import requests
import urllib.parse
from frappe.utils import now_datetime, add_to_date, get_datetime

from salla_integration.core.client.exceptions import SallaAuthenticationError


class SallaAuth:
    """Handles OAuth 2.0 authentication with Salla."""
    
    OAUTH_AUTH_URL = "https://accounts.salla.sa/oauth2/auth"
    OAUTH_TOKEN_URL = "https://accounts.salla.sa/oauth2/token"
    
    def __init__(self):
        self.settings = frappe.get_single("Salla Settings")
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None
        self._load_tokens()
    
    def _load_tokens(self):
        """Load tokens from Salla Settings."""
        self._access_token = self.settings.get_password("access_token")
        self._refresh_token = self.settings.get_password("refresh_token")
        if self.settings.token_expires_at:
            self._token_expires_at = get_datetime(self.settings.token_expires_at)
    
    @property
    def access_token(self) -> str:
        """Get access token, refreshing if expired."""
        if self.is_token_expired():
            self.refresh_access_token()
        return self._access_token
    
    @property
    def client_id(self) -> str:
        return self.settings.client_id
    
    @property
    def client_secret(self) -> str:
        return self.settings.client_secret
    
    def is_token_expired(self) -> bool:
        """Check if the access token is expired or about to expire."""
        if not self._token_expires_at:
            return True
        # Add 60 second buffer to handle edge cases
        return now_datetime() >= add_to_date(self._token_expires_at, seconds=-60)
    
    def is_authenticated(self) -> bool:
        """Check if we have valid authentication credentials."""
        return bool(self._access_token and not self.is_token_expired())
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate the OAuth authorization URL."""
        if not state:
            state = frappe.generate_hash(length=16)
        print(f"Redirect URl: {self.get_redirect_uri()}")
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.get_redirect_uri(),
            "state": state
        }
        
        return f"{self.OAUTH_AUTH_URL}?{urllib.parse.urlencode(params)}"
    
    def get_redirect_uri(self) -> str:
        """Get the OAuth callback redirect URI."""
        url = frappe.utils.get_url()
        # Force HTTPS protocol
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
        return url + "/api/method/salla_integration.core.client.auth.oauth_callback"
    
    def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for access and refresh tokens."""
        try:
            response = requests.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.get_redirect_uri(),
                    "code": code,
                },
                timeout=20
            )
            
            response.raise_for_status()
            token_data = response.json()
            self._save_tokens(token_data)
            return token_data
            
        except requests.RequestException as e:
            raise SallaAuthenticationError(
                message=f"Failed to exchange authorization code: {str(e)}"
            )
    
    def refresh_access_token(self) -> dict:
        """Refresh the access token using the refresh token."""
        if not self._refresh_token:
            raise SallaAuthenticationError(
                message="No refresh token available. Please re-authenticate."
            )
        
        try:
            response = requests.post(
                self.OAUTH_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self._refresh_token,
                },
                timeout=20
            )
            response.raise_for_status()
            token_data = response.json()
            self._save_tokens(token_data)
            return token_data
            
        except requests.RequestException as e:
            raise SallaAuthenticationError(
                message=f"Failed to refresh access token: {str(e)}"
            )
    
    def _save_tokens(self, token_data: dict):
        """Save tokens to Salla Settings and update local cache."""
        self._access_token = token_data["access_token"]
        self._refresh_token = token_data["refresh_token"]
        self._token_expires_at = add_to_date(
            now_datetime(),
            seconds=token_data["expires_in"]
        )
        
        # Update settings
        self.settings.access_token = self._access_token
        self.settings.refresh_token = self._refresh_token
        self.settings.token_expires_at = self._token_expires_at
        self.settings.save(ignore_permissions=True)
        frappe.db.commit()
    
    def get_auth_headers(self) -> dict:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }


# Whitelisted API methods for OAuth flow

@frappe.whitelist()
def start_oauth():
    """Start the OAuth authorization flow."""
    auth = SallaAuth()
    url = auth.get_authorization_url()
    
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = url


@frappe.whitelist(allow_guest=True)
def oauth_callback(code=None, **kwargs):
    """Handle OAuth callback from Salla."""
    if not code:
        frappe.throw("Authorization code missing")
    
    auth = SallaAuth()
    auth.exchange_code_for_tokens(code)
    
    frappe.msgprint("Salla connected successfully 🎉")
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/app/salla-settings"
