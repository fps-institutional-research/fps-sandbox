"""
Summary:
    1. Accesses secrets from GCP Secret Manager.
    2. Refreshes the authentication tokens for the Blackbaud SKY API.
    3. Publishes both new tokens back to GCP Secret Manager, destroying the previous versions in the process.

--------------------
--- Design Notes ---
--------------------
Authentication considerations:
    - Access tokens are valid for 1 hour and must be refreshed hourly.
    - Refresh tokens have a 1-year validity.
    - Secrets are stored in GCP Secret Manager.
    - The rotation of tokens is handled by a Cloud Scheduler job that triggers this function.

"""

import os
import json
import sys
import logging
import argparse
import requests
from datetime import datetime
from google.cloud import secretmanager
import google.cloud.logging
from google.cloud.logging.handlers import StructuredLogHandler

# --- Configurations ---
# Google Cloud Project
GCP_PROJECT_ID = "institutional-sandbox" # "institutional-research-495616"

# Logging mode configuration:
# Set to True for GCP Structured JSON logging, False for standard console/stdout logging,
# or None to auto-detect based on GCP runtime environment variables.
USE_GCP_LOGGING = None

# Google Cloud Secret Manager Names
BLACKBAUD_APPLICATION_CLIENT_ID = "blackbaud-application-client-id"
BLACKBAUD_APPLICATION_CLIENT_SECRET = "blackbaud-application-client-secret"
BLACKBAUD_SKY_SUBSCRIPTION_KEY = "blackbaud-sky-subscription-key"
BLACKBAUD_SKY_ACCESS_TOKEN = "blackbaud-sky-access-token"
BLACKBAUD_SKY_REFRESH_TOKEN = "blackbaud-sky-refresh-token"

# Blackbaud API endpoint
TOKEN_URL = "https://oauth2.sky.blackbaud.com/token"

# LOGGER
LOGGER = logging.getLogger(__name__)

# --- Functions ---
def setup_logging() -> None:
    """
    Initializes logging handler with Python's standard logging.
    If USE_GCP_LOGGING is explicitly set (True or False), respects that setting directly.
    If USE_GCP_LOGGING is None, auto-detects GCP runtime environment (Cloud Run Services/Jobs, Cloud Functions, GAE).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Check for GCP runtime environments (including Cloud Run Jobs and Cloud Run Services)
    gcp_env_vars = ["CLOUD_RUN_JOB", "CLOUD_RUN_EXECUTION"]
    is_gcp_runtime = any(env in os.environ for env in gcp_env_vars)
    
    # Direct manual variable control if USE_GCP_LOGGING is explicitly set (True or False); fallback to auto-detection if None
    is_gcp = USE_GCP_LOGGING if USE_GCP_LOGGING is not None else is_gcp_runtime
    
    root_logger.handlers.clear()
    
    if is_gcp:
        root_logger.addHandler(StructuredLogHandler(stream=sys.stdout))
    else:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

def access_secret_version(secret_id: str, version_id: str = "latest") -> str:
    """
    Accesses the payload for the given secret version if one exists.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = client.secret_version_path(GCP_PROJECT_ID, secret_id, version_id)
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

def destroy_previous_versions(secret_id: str, current_version_name: str) -> None:
    """
    Disables all versions of the given secret except the current one.
    """
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}"
    
    for version in client.list_secret_versions(request={"parent": parent}):
        # Don't disable the current version or already disabled/destroyed versions
        if version.name != current_version_name and version.state == secretmanager.SecretVersion.State.ENABLED:
            client.destroy_secret_version(request={"name": version.name})
            LOGGER.info(f"Destroyed old secret version: {version.name}")

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
    LOGGER.info(f"Added new secret version: {response.name}")
    
    destroy_previous_versions(secret_id, response.name)
    
    return response.name

def rotate_token() -> None:
    """
    1. Fetches client_id, client_secret, refresh_token, and subscription_key from Google Cloud Secret Manager.
    2. Requests a new access token and refresh token from Blackbaud SKY API.
    3. Publishes both new tokens back to Google Cloud Secret Manager.
    """
    setup_logging()
    LOGGER.info(f"Token rotation started for GCP Project '{GCP_PROJECT_ID}'")
    
    try:
        # 1. Get credentials from Secret Manager
        LOGGER.info("Fetching credentials from Google Cloud Secret Manager...")
        client_id = access_secret_version(BLACKBAUD_APPLICATION_CLIENT_ID)
        client_secret = access_secret_version(BLACKBAUD_APPLICATION_CLIENT_SECRET)
        refresh_token = access_secret_version(BLACKBAUD_SKY_REFRESH_TOKEN)
        subscription_key = access_secret_version(BLACKBAUD_SKY_SUBSCRIPTION_KEY)
        
        # 2. Get a new token
        LOGGER.info("Requesting new access token from Blackbaud SKY API...")
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
        LOGGER.info(f"Publishing new access token to Google Cloud Secret Manager...")
        add_secret_version(BLACKBAUD_SKY_ACCESS_TOKEN, new_access_token)
        
        if new_refresh_token != refresh_token:
            LOGGER.info(f"Publishing new refresh token to Google Cloud Secret Manager...")
            add_secret_version(BLACKBAUD_SKY_REFRESH_TOKEN, new_refresh_token)
        
        LOGGER.info("Token rotation completed successfully")
        
    except Exception as e:
        LOGGER.error(f"ERROR during token rotation: {e}")
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
    # Every July 1st, set preserve_refresh_token to 'false' so that a new refresh token is issued (renewing the 365-day expiration window)
    preserve_refresh = 'false' if datetime.now().month == 7 and datetime.now().day == 1 else 'true'
    
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
        'preserve_refresh_token': preserve_refresh
    }
    
    headers = {
        'Bb-Api-Subscription-Key': subscription_key
    }
    
    response = requests.post(TOKEN_URL, data=data, headers=headers)
    
    if response.status_code != 200:
        LOGGER.error(f"Error: {response.status_code} - {response.text}")
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
    parser = argparse.ArgumentParser(description="Rotate Blackbaud access token in Google Secret Manager.")
    parser.add_argument("--project", help="GCP Project ID", default=GCP_PROJECT_ID)
    args = parser.parse_args()
    
    GCP_PROJECT_ID = args.project
    rotate_token()
