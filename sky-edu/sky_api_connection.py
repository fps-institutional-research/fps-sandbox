"""
sky_api_connection.py

Reusable module for authenticating with the Blackbaud SKY API using OAuth 2.0.
Secrets (client_id, client_secret, refresh_token, subscription_key) are stored
in Google Cloud Secret Manager and retrieved at runtime.

This module implements industry best practices defined in RFC 6749 (OAuth 2.0):
1. Utilises HTTP Basic Authentication for confidential client credentials during
   token refresh, avoiding passing secrets in the request body.
2. Employs `requests_oauthlib.OAuth2Session` to manage the token lifecycle,
   including automatic token refreshment if it expires during a long-running
   pipeline execution.
"""

from google.cloud import secretmanager
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session


# ---------------------------------------------------------------------------
# Secret Manager helpers
# ---------------------------------------------------------------------------

def _get_secret(project_id: str, secret_id: str, version: str = "latest") -> str:
    """Retrieve a secret value from Google Cloud Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


def get_sky_api_credentials(project_id: str) -> dict:
    """
    Retrieve all Blackbaud SKY API credentials from Secret Manager.

    Expected secrets (create these in your GCP project):
        - sky_api_client_id        : OAuth 2.0 application client ID
        - sky_api_client_secret    : OAuth 2.0 application client secret
        - sky_api_refresh_token    : Long-lived refresh token from initial auth
        - sky_api_subscription_key : Blackbaud developer subscription key
    """
    return {
        "client_id": _get_secret(project_id, "sky_api_client_id"),
        "client_secret": _get_secret(project_id, "sky_api_client_secret"),
        "refresh_token": _get_secret(project_id, "sky_api_refresh_token"),
        "subscription_key": _get_secret(project_id, "sky_api_subscription_key"),
    }


# ---------------------------------------------------------------------------
# OAuth 2.0 Token Management
# ---------------------------------------------------------------------------

BLACKBAUD_TOKEN_URL = "https://oauth2.sky.blackbaud.com/token"


def update_refresh_token_if_rotated(
    project_id: str,
    old_refresh_token: str,
    new_refresh_token: str,
) -> None:
    """
    If Blackbaud returned a new (rotated) refresh token, store it back
    in Secret Manager so subsequent invocations use the latest token.
    """
    if new_refresh_token and new_refresh_token != old_refresh_token:
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project_id}/secrets/sky_api_refresh_token"
        client.add_secret_version(
            request={
                "parent": parent,
                "payload": {"data": new_refresh_token.encode("UTF-8")},
            }
        )


# ---------------------------------------------------------------------------
# High-level convenience function
# ---------------------------------------------------------------------------

def get_authenticated_session(project_id: str) -> tuple[OAuth2Session, dict]:
    """
    Create an ``OAuth2Session`` pre-configured to comply with OAuth 2.0 (RFC 6749).
    This setup:
        - Uses HTTP Basic Authentication for token refresh requests.
        - Automatically refreshes the access token if it expires during use.
        - Injects the required ``Bb-Api-Subscription-Key`` header.
        - Persists rotated refresh tokens back to Secret Manager.

    Returns:
        (session, token_response)
    """
    creds = get_sky_api_credentials(project_id)
    
    client_id = creds["client_id"]
    client_secret = creds["client_secret"]
    refresh_token = creds["refresh_token"]

    # RFC 6749 Section 2.3.1: Confidential clients should use HTTP Basic Auth
    auth = HTTPBasicAuth(client_id, client_secret)

    def token_updater(new_token: dict) -> None:
        """Callback invoked by OAuth2Session whenever a token is refreshed."""
        new_refresh = new_token.get("refresh_token")
        if new_refresh:
            update_refresh_token_if_rotated(
                project_id=project_id,
                old_refresh_token=creds["refresh_token"],
                new_refresh_token=new_refresh,
            )
            creds["refresh_token"] = new_refresh

    # Initialise the OAuth2Session without an active access_token so we can 
    # immediately trigger a refresh to fetch a valid one.
    session = OAuth2Session(
        client_id=client_id,
        auto_refresh_url=BLACKBAUD_TOKEN_URL,
        auto_refresh_kwargs={"auth": auth},
        token_updater=token_updater,
    )

    # Perform an initial token refresh to bootstrap the session
    token_data = session.refresh_token(
        BLACKBAUD_TOKEN_URL,
        refresh_token=refresh_token,
        auth=auth,
    )

    # Apply the Blackbaud subscription key for all subsequent API requests
    session.headers.update({
        "Bb-Api-Subscription-Key": creds["subscription_key"],
    })

    return session, token_data
