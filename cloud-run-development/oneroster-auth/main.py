import os
import argparse
from google.cloud import secretmanager
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

# --- CONFIGURATION ---
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT", "institutional-research-495616")
ONEROSTER_CLIENT_KEY = "blackbaud-oneroster-client-key"
ONEROSTER_CLIENT_SECRET = "blackbaud-oneroster-client-secret"
ONEROSTER_ACCESS_TOKEN = "blackbaud-oneroster-access-token"

# Default Configuration
TOKEN_URL = "https://oauth2.sky.blackbaud.com/token"

# OneRoster scopes are typically URIs.
SCOPES = [
    "https://purl.imsglobal.org/spec/or/v1p1/scope/roster-demographics.readonly",
    "https://purl.imsglobal.org/spec/or/v1p1/scope/roster.readonly",
    "https://purl.imsglobal.org/spec/or/v1p1/scope/gradebook.readonly"
]

def get_oauth_session(client_id: str, client_secret: str) -> OAuth2Session:
    """
    Creates and returns an OAuth2Session using the provided credentials.
    """
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client, scope=SCOPES)
    
    # fetch_token handles the POST request, authentication, and response parsing
    oauth.fetch_token(
        token_url=TOKEN_URL,
        client_id=client_id,
        client_secret=client_secret,
        scope=SCOPES,
        include_client_id=True
    )

    return oauth

def access_secret_version(secret_id: str, version_id: str = "latest") -> str:
    """
    Accesses the payload for the given secret version if one exists.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def disable_previous_versions(secret_id: str, current_version_name: str) -> None:
    """
    Disables all versions of the given secret except the current one.
    """
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}"
    
    for version in client.list_secret_versions(request={"parent": parent}):
        # Don't disable the current version or already disabled/destroyed versions
        if version.name != current_version_name and version.state == secretmanager.SecretVersion.State.ENABLED:
            print(f"Disabling old secret version: {version.name}")
            client.disable_secret_version(request={"name": version.name})

def add_secret_version(secret_id: str, payload: str) -> str:
    """
    Adds a new secret version and disables all previous versions.
    """
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}"
    response = client.add_secret_version(
        request={
            "parent": parent,
            "payload": {"data": payload.encode("UTF-8")},
        }
    )
    print(f"Added secret version for {secret_id}: {response.name}")
    
    # Disable previous versions to ensure only the latest is active
    disable_previous_versions(secret_id, response.name)
    
    return response.name

def rotate_token() -> None:
    """
    1. Fetches client_id and client_secret from GCP Secret Manager.
    2. Requests a new OneRoster access token using oauthlib.
    3. Publishes the new access token back to GCP Secret Manager.
    """
    print(f"--- Token Rotation Started for Project: {GCP_PROJECT_ID} ---")
    
    try:
        # 1. Get credentials from Secret Manager
        print("Fetching credentials from Secret Manager...")
        client_id = access_secret_version(ONEROSTER_CLIENT_KEY)
        client_secret = access_secret_version(ONEROSTER_CLIENT_SECRET)
        
        # 2. Get a new token
        print("Requesting new access token from OneRoster...")
        session = get_oauth_session(client_id=client_id, client_secret=client_secret)
        new_token = session.token.get('access_token')
        
        if not new_token:
            raise Exception("Failed to retrieve access token from response.")
            
        # 3. Publish the new token back to Secret Manager
        print(f"Publishing new token to secret: {ONEROSTER_ACCESS_TOKEN}...")
        add_secret_version(ONEROSTER_ACCESS_TOKEN, new_token)
        
        print("--- Token Rotation Completed Successfully ---")
        
    except Exception as e:
        print(f"ERROR during token rotation: {e}")
        exit(1)

def rotate_token_http(request: object = None) -> tuple:
    """
    HTTP Cloud Function entry point.
    """
    try:
        rotate_token()
        return "Token rotation completed successfully", 200
    except Exception as e:
        return f"Error during token rotation: {e}", 500

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotate OneRoster access token in GCP Secret Manager.")
    parser.add_argument("--project", help="GCP Project ID", default=GCP_PROJECT_ID)
    args = parser.parse_args()
    
    GCP_PROJECT_ID = args.project
    rotate_token()