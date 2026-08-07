# Calls specific list via SKY_API using ID

import requests
import json
import csv
import os
import time
from google.cloud import secretmanager

# Configuration
GCP_PROJECT_ID = "institutional-sandbox"
BLACKBAUD_SKY_ACCESS_TOKEN = "blackbaud-sky-access-token"
BLACKBAUD_SKY_SUBSCRIPTION_KEY = "blackbaud-sky-subscription-key"
LIST_ID = "155155"

def access_secret_version(secret_id, version_id="latest"):
    """
    Accesses the payload for the given secret version from GCP Secret Manager.
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = client.secret_version_path(GCP_PROJECT_ID, secret_id, version_id)
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
    access_token = access_secret_version(BLACKBAUD_SKY_ACCESS_TOKEN)
    subscription_key = access_secret_version(BLACKBAUD_SKY_SUBSCRIPTION_KEY)
    
    if not access_token or not subscription_key:
        print("FAILED: Missing credentials.")
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "bb-api-subscription-key": subscription_key,
        "Content-Type": "application/json"
    }

    # 2. Fetch the advanced list with pagination
    
    print(f"Fetching advanced list (List ID: {LIST_ID})...")

    base_url = f"https://api.sky.blackbaud.com/school/v1/lists/advanced/{LIST_ID}"
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

    if not all_rows:
        print(f"No data found for list {LIST_ID}. Skipping export.")
        return

    # 3. Export data to Desktop in CSV
    desktop_path = os.path.expanduser(f"~/Desktop/advanced_list_{LIST_ID}.csv")
    print(f"Exporting data to {desktop_path}...")
    fieldnames = list({key: None for row in all_rows for key in row.keys()}.keys())
    with open(desktop_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Successfully exported {len(all_rows)} rows.")

if __name__ == "__main__":
    export_advanced_list()