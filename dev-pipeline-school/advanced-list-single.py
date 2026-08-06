# Calls specific list via SKY_API using ID

import requests
import json
import os
import time
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

def get_with_retry(url, headers):
    """
    Performs a GET request and retries on 429 Too Many Requests.
    """
    while True:
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            print(f"  Rate limited (429). Waiting {retry_after}s...")
            time.sleep(retry_after)
            continue
        
        if not response.ok:
            print(f"  Error {response.status_code}: {response.text}")
            
        response.raise_for_status()
        return response

def export_advanced_list():
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

    # 2. Fetch the advanced list with pagination
    list_id = "152656"
    print(f"Fetching advanced list (List ID: {list_id})...")

    base_url = f"https://api.sky.blackbaud.com/school/v1/lists/advanced/{list_id}"
    all_rows = []
    page = 1

    while True:
        url = f"{base_url}?page={page}"
        print(f"  Fetching page {page}...")
        response = get_with_retry(url, headers)
        data = response.json()

        # Response shape: {"count": N, "page": N, "results": {"rows": [...]}}
        rows = data.get("results", {}).get("rows", [])
        count = data.get("count", 0)

        # Flatten each row's columns list [{"name":..., "value":...}] into a plain dict
        flat_rows = [{col["name"]: col.get("value") for col in row.get("columns", [])} for row in rows]
        all_rows.extend(flat_rows)

        print(f"    Page {page}: {count} record(s) returned (running total: {len(all_rows)})")

        # Stop when the page returns no records
        if count == 0 or not rows:
            break

        page += 1

    print(f"Total rows fetched: {len(all_rows)}")

    # 3. Export data to Desktop in NDJSON
    desktop_path = os.path.expanduser(f"~/Desktop/advanced_list_{list_id}.ndjson")
    print(f"Exporting data to {desktop_path}...")
    with open(desktop_path, "w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row) + "\n")
    print(f"Successfully exported {len(all_rows)} rows.")

if __name__ == "__main__":
    export_advanced_list()