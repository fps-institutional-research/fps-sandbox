import os
import json
import sys
import argparse
import requests
from google.cloud import secretmanager

# --- Configurations ---
# Google Cloud Project
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT", "amazing-hub-484421-v9")

# Google Cloud Secret Manager Names
BLACKBAUD_CLIENT_ID = "blackbaud-application-client-id"
BLACKBAUD_CLIENT_SECRET = "blackbaud-application-client-secret"
BLACKBAUD_API_SUBSCRIPTION_KEY = "blackbaud-api-subscription-key"
BLACKBAUD_API_ACCESS_TOKEN = "blackbaud-api-access-token"
BLACKBAUD_API_REFRESH_TOKEN = "blackbaud-api-refresh-token"

# Blackbaud API endpoint
TOKEN_URL = "https://oauth2.sky.blackbaud.com/token"

# --- Functions ---
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
    1. Fetches client_id, client_secret, refresh_token, and subscription_key from GCP Secret Manager.
    2. Requests a new access token and refresh token from Blackbaud SKY API.
    3. Publishes both new tokens back to GCP Secret Manager.
    """
    print(f"--- Token Rotation Started for Project: {GCP_PROJECT_ID} ---")
    
    try:
        # 1. Get credentials from Secret Manager
        print("Fetching credentials from Secret Manager...")
        client_id = access_secret_version(BLACKBAUD_CLIENT_ID)
        client_secret = access_secret_version(BLACKBAUD_CLIENT_SECRET)
        refresh_token = access_secret_version(BLACKBAUD_API_REFRESH_TOKEN)
        subscription_key = access_secret_version(BLACKBAUD_API_SUBSCRIPTION_KEY)
        
        # 2. Get a new token
        print("Requesting new access token from Blackbaud SKY API...")
        token_response = refresh_access_token(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
            subscription_key=subscription_key
        )
        
        new_access_token = token_response.get('access_token')
        new_refresh_token = token_response.get('refresh_token')
        
        if not new_access_token:
            raise Exception(f"Failed to retrieve access token. Response: {token_response}")
            
        # 3. Publish the new tokens back to Secret Manager
        print("Publishing new access token...")
        add_secret_version(BLACKBAUD_API_ACCESS_TOKEN, new_access_token)
        
        if new_refresh_token:
            print("Publishing new refresh token...")
            add_secret_version(BLACKBAUD_API_REFRESH_TOKEN, new_refresh_token)
        
        print("--- Token Rotation Completed Successfully ---")
        
    except Exception as e:
        print(f"ERROR during token rotation: {e}")
        exit(1)

def refresh_access_token(
    client_id: str, 
    client_secret: str, 
    refresh_token: str, 
    subscription_key: str
) -> dict:
    """
    Refresh the access token using refresh token.
    Returns the full token response from Blackbaud as a dictionary.
    """
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    headers = {
        'Bb-Api-Subscription-Key': subscription_key
    }
    
    response = requests.post(TOKEN_URL, data=data, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}", file=sys.stderr)
        response.raise_for_status()
        
    return response.json()

def rotate_token_http(request: object = None) -> tuple:
    """
    HTTP Cloud Function entry point.
    """
    try:
        rotate_token()
        return "Token rotation completed successfully", 200
    except Exception as e:
        return f"Error during token rotation: {e}", 500

# --- Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotate Blackbaud access token in GCP Secret Manager.")
    parser.add_argument("--project", help="GCP Project ID", default=GCP_PROJECT_ID)
    args = parser.parse_args()
    
    GCP_PROJECT_ID = args.project
    rotate_token()
