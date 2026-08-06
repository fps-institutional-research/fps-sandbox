import requests
import json
import os
from google.cloud import secretmanager

# Configuration
GCP_PROJECT_ID = "amazing-hub-484421-v9"
ACCESS_TOKEN_SECRET_ID = "blackbaud-api-access-token"
SUBSCRIPTION_KEY_SECRET_ID = "blackbaud-api-subscription-key"

def access_secret_version(secret_id, version_id="latest"):
    """
    Accesses the payload for the given secret version from GCP Secret Manager.
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"Error accessing secret {secret_id}: {str(e)}")
        return None

def export_testscores():
    # 1. Fetch Credentials
    print("Fetching credentials...")
    access_token = access_secret_version(ACCESS_TOKEN_SECRET_ID)
    subscription_key = access_secret_version(SUBSCRIPTION_KEY_SECRET_ID)
    
    if not access_token or not subscription_key:
        print("FAILED: Missing credentials.")
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "bb-api-subscription-key": subscription_key,
        "Content-Type": "application/json"
    }

    # 2. Query for test scores with pagination
    print("Querying for test scores...")
    testscores = []
    # Initial endpoint
    next_url = "https://api.sky.blackbaud.com/school/v1/testscores/all"
    
    try:
        while next_url:
            # Handle relative URLs if they occur
            if next_url.startswith("/"):
                next_url = f"https://api.sky.blackbaud.com/school{next_url}"
                
            print(f"Fetching: {next_url}")
            response = requests.get(next_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            page_scores = data.get("value", [])
            testscores.extend(page_scores)
            print(f"Fetched {len(page_scores)} test scores (Total: {len(testscores)})...")
            
            # Check for next page
            next_url = data.get("next_link")
        
        print(f"Total test scores found: {len(testscores)}")
        
        # 3. Export to Desktop in NDJSON
        desktop_path = os.path.expanduser("~/Desktop/testscores.ndjson")
        print(f"Exporting to {desktop_path}...")
        
        with open(desktop_path, "w", encoding="utf-8") as f:
            for score in testscores:
                f.write(json.dumps(score) + "\n")
        
        print(f"Successfully exported {len(testscores)} test scores to Desktop in NDJSON format.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    export_testscores()
