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

def get_list_of_advanced_lists(headers, category="Academics"):
    """
    Fetches all lists and filters for those in the named category.
    """
    print(f"Fetching list of all available lists for category: {category}...")
    url = "https://api.sky.blackbaud.com/school/v1/lists"
    response = get_with_retry(url, headers)
    data = response.json()
    
    # Handle both direct list response and 'value' wrapper
    all_lists = data.get("value", data) if isinstance(data, dict) else data
    
    # Filtering for category
    ir_lists = []
    for l in all_lists:
        l_category = l.get("category_name", l.get("category", ""))
        if l_category == category or l_category == f"Institutional Research - {category}" or l_category.strip().lower() == category.strip().lower():
            ir_lists.append(l)
            #print(l.get("id"))
    
    print(f"Found {len(ir_lists)} list(s) in '{category}' category.")
    return ir_lists

def export_list(list_id, list_name, headers, category="Academics"):
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

    # Export data to Desktop in CSV
    # Clean list name for filename
    # clean_name = "".join([c if c.isalnum() else "_" for c in list_name])
    # category_folder = "".join([c if c.isalnum() else "_" for c in category.lower()])
    # desktop_path = os.path.expanduser(f"~/Desktop/Data/Advanced Lists/{category_folder}/{clean_name}.csv")
    desktop_path = os.path.expanduser(f"~/Desktop/Data/Advanced Lists/{category}/{list_name}.csv")


    print(f"  Exporting {len(all_rows)} rows to {desktop_path}...")
    fieldnames = list({key: None for row in all_rows for key in row.keys()}.keys())
    
    os.makedirs(os.path.dirname(desktop_path), exist_ok=True)
    with open(desktop_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"  Successfully exported {list_name}.")

def main():
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

    # 2. Categories to process
    categories = [
        "Institutional Research - School",
        "Institutional Research - Platform"
    ]
    
    # 3. Iterate through categories and export lists
    for category in categories:
        print(f"\n==========================================")
        print(f"Processing Category: {category}")
        print(f"==========================================")
        list_of_advanced_lists = get_list_of_advanced_lists(headers, category=category)
        
        # OPTIONAL: Filter for a single list ID (uncomment the line below to use)
        # list_of_advanced_lists = [l for l in list_of_advanced_lists if str(l.get("id")) == "152690"]
        
        for advanced_list in list_of_advanced_lists:
            export_list(advanced_list.get("id"), advanced_list.get("name", f"list_{advanced_list.get('id')}"), headers, category=category)

    print("\nAll tasks completed.")

if __name__ == "__main__":
    main()
