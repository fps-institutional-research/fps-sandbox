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

def get_institutional_research_lists(headers):
    """
    Fetches all lists and filters for those in the named category.
    """
    print("Fetching list of all available lists...")
    url = "https://api.sky.blackbaud.com/school/v1/lists"
    response = get_with_retry(url, headers)
    data = response.json()
    
    # Handle both direct list response and 'value' wrapper
    all_lists = data.get("value", data) if isinstance(data, dict) else data
    
    # Filtering for category
    category = "Institutional Research - Test"
    ir_lists = []
    for l in all_lists:
        l_category = l.get("category_name", l.get("category", ""))
        if l_category == category:
            ir_lists.append(l)
            #print(l.get("id"))
    
    print(f"Found {len(ir_lists)} list(s) in '{category}' category.")
    return ir_lists

def export_list(list_id, list_name, headers):
    """
    Fetches a single advanced list with pagination and saves to Desktop.
    """
    print(f"\nProcessing List: {list_name} (ID: {list_id})...")

    base_url = f"https://api.sky.blackbaud.com/school/v1/lists/advanced/{list_id}"
    all_rows = []
    page = 1

    while True:
        url = f"{base_url}?page={page}"
        print(f"  Fetching page {page}...")
        try:
            response = get_with_retry(url, headers)
            data = response.json()
        except Exception as e:
            print(f"  Failed to fetch page {page}: {e}")
            break

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
        print(f"  No data found for list {list_id}. Skipping export.")
        return

    # Export data to Desktop in NDJSON
    # Clean list name for filename
    clean_name = "".join([c if c.isalnum() else "_" for c in list_name])
    #desktop_path = os.path.expanduser(f"~/Desktop/Data/Advanced Lists/Academic/{list_id}_{clean_name}.ndjson")
    desktop_path = os.path.expanduser(f"~/Desktop/Data/Advanced Lists/academic/{clean_name}.ndjson")
    
    print(f"  Exporting {len(all_rows)} rows to {desktop_path}...")
    with open(desktop_path, "w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row) + "\n")
    print(f"  Successfully exported {list_name}.")

def main():
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

    # 2. Get list of Institutional Research IDs
    ir_lists = get_institutional_research_lists(headers)
    
    # OPTIONAL: Filter for a single list ID (uncomment the line below to use)
    #ir_lists = [l for l in ir_lists if str(l.get("id")) == "152690"]
    
    # 3. Iterate and Export
    for l in ir_lists:
        list_id = l.get("id")
        list_name = l.get("name", f"list_{list_id}")
        export_list(list_id, list_name, headers)

    print("\nAll tasks completed.")

if __name__ == "__main__":
    main()
