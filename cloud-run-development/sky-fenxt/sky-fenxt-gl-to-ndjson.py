import requests
import json
import os
from google.cloud import secretmanager

# Configuration
GCP_PROJECT_ID = "institutional-research-495616"
ACCESS_TOKEN_SECRET_ID = "blackbaud-sky-access-token"
SUBSCRIPTION_KEY_SECRET_ID = "blackbaud-sky-subscription-key"

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

def export_data():
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
        "Accept": "application/json"
    }

    # 2. Query for Fiscal Years
    print("Querying for fiscal years...")
    base_url = "https://api.sky.blackbaud.com/generalledger/v1/fiscalyears"
    fiscal_years = []
    next_url = base_url
    
    try:
        while next_url:
            # Handle relative next_links if they occur
            if next_url.startswith("/"):
                next_url = f"https://api.sky.blackbaud.com{next_url}"
                
            response = requests.get(next_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            page_data = data.get("value", [])
            fiscal_years.extend(page_data)
            print(f"Fetched {len(page_data)} fiscal years (Total: {len(fiscal_years)})...")
            
            next_url = data.get("next_link")
        
        print(f"Total fiscal years found: {len(fiscal_years)}")
        
        # 3. Export to Desktop in NDJSON
        desktop_path = os.path.expanduser("~/Desktop/fiscal_years.ndjson")
        print(f"Exporting to {desktop_path}...")
        
        with open(desktop_path, "w", encoding="utf-8") as f:
            for fy in fiscal_years:
                f.write(json.dumps(fy) + "\n")
        
        print(f"Successfully exported {len(fiscal_years)} fiscal years to Desktop in NDJSON format.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    export_data()
