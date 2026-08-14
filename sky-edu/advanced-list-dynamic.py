import requests
import json
import csv
import os
import time
import io
from google.cloud import secretmanager
from google.cloud import storage

# ---------------------
# --- Configuration ---
# ---------------------

# Google Cloud resources
GCP_PROJECT_ID = "institutional-sandbox"
GCS_STAGING_BUCKET = "495616-bemdam-staging-sandbox"
BLACKBAUD_SKY_ACCESS_TOKEN = "blackbaud-sky-access-token"
BLACKBAUD_SKY_SUBSCRIPTION_KEY = "blackbaud-sky-subscription-key"

# Terminal text colors
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RESET = '\033[0m'  # Crucial to reset color back to default

# ------------------------
# --- Helper Functions ---
# ------------------------
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
        print(f"{RED}Error accessing secret {secret_id}: {str(e)}{RESET}")
        return None

def authenticate():
    """
    Returns a dictionary of headers for authentication.
    """
    access_token = access_secret_version(BLACKBAUD_SKY_ACCESS_TOKEN)
    subscription_key = access_secret_version(BLACKBAUD_SKY_SUBSCRIPTION_KEY)

    if not access_token or not subscription_key:
        print(f"{RED}\t authenticate - FAILED: Missing credentials.{RESET}")
        return None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "bb-api-subscription-key": subscription_key,
        "Accept": "application/json"
    }
    return headers

def get_with_retry(url, headers):
    """
    Performs a GET request with retry logic for:
      - 429 Too Many Requests: waits Retry-After seconds and retries.
      - 401 Unauthorized: re-authenticates (token may have expired) and retries once.
    """
    auth_retried = False
    while True:
        response = requests.get(url, headers=headers)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            print(f"{YELLOW}\t get_with_retry - Rate limited (429). Waiting {retry_after}s...{RESET}")
            time.sleep(retry_after)
            continue

        if response.status_code == 401 and not auth_retried:
            print(f"{YELLOW}\t get_with_retry - Unauthorized (401). Token may have expired — re-authenticating...{RESET}")
            new_headers = authenticate()
            if new_headers:
                headers.update(new_headers)  # mutate in-place so callers see the refresh
                auth_retried = True
                continue
            else:
                print(f"{RED}\t get_with_retry - Re-authentication failed. Aborting request.{RESET}")

        if not response.ok:
            print(f"{RED}\t get_with_retry - Error {response.status_code}: {response.text}{RESET}")

        response.raise_for_status()
        return response

# ----------------------
# --- Core Functions ---
# ----------------------
def get_list_of_advanced_lists(headers, category="Academics"):
    """
    Fetches all lists and filters for those in the named category.
    """
    print(f"\n\t get_list_of_advanced_lists - Fetching advanced lists in '{category}'...")
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
    
    print(f"\t get_list_of_advanced_lists - Found {len(ir_lists)} list(s) in '{category}'")
    return ir_lists

def export_list(list_id, list_name, headers, category="Academics"):
    """
    Fetches a single advanced list with pagination and exports to destination.
    """
    print(f"\n\t\t export_list - Processing List: {list_name} (ID: {list_id})")

    base_url = f"https://api.sky.blackbaud.com/school/v1/lists/advanced/{list_id}"
    all_rows = []
    page = 1

    while True:
        url = f"{base_url}?page={page}"
        print(f"\t\t export_list - Fetching page {page}...")
        try:
            response = get_with_retry(url, headers)
            data = response.json()
        except Exception as e:
            print(f"\t\t export_list - Failed to fetch page {page}: {e}")
            break

        # Response shape: {"count": N, "page": N, "results": {"rows": [...]}}
        rows = data.get("results", {}).get("rows", [])
        count = data.get("count", 0)

        # Flatten each row's columns list [{"name":..., "value":...}] into a plain dict
        flat_rows = [{col["name"]: col.get("value") for col in row.get("columns", [])} for row in rows]
        all_rows.extend(flat_rows)

        print(f"\t\t export_list - Page {page}: {count} record(s) returned (running total: {len(all_rows)})")

        # Stop when the page returns no records or fewer than a full page
        if count == 0 or not rows or count < 1000:
            break

        page += 1

    if not all_rows:
        print(f"\t\t export_list - No data found for list {list_id}. Skipping export.")
        return

    # 1. Generate CSV content
    fieldnames = list({key: None for row in all_rows for key in row.keys()}.keys())
    output_buffer = io.StringIO()
    writer = csv.DictWriter(output_buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)
    csv_text = output_buffer.getvalue()

    # 2. Export data to Desktop in CSV
    # desktop_path = os.path.expanduser(f"~/Desktop/Data/{category}/{list_name}.csv")
    # print(f"\tExporting {len(all_rows)} rows to Desktop: {desktop_path}...")
    # os.makedirs(os.path.dirname(desktop_path), exist_ok=True)
    # with open(desktop_path, "w", encoding="utf-8") as f:
    #     f.write(csv_text)
    # print(f"\tSuccessfully exported to Desktop.")

    # 3. Publish CSV to Google Cloud Storage
    clean_category = category.replace("Institutional Research - ", "").strip().lower()
    gcs_blob_path = f"{clean_category}/{list_name.lower()}.csv"
    print(f"\t\t export_list - Publishing to GCS... (gs://{GCS_STAGING_BUCKET}/{gcs_blob_path})")
    try:
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(GCS_STAGING_BUCKET)
        blob = bucket.blob(gcs_blob_path)
        blob.upload_from_string(data=csv_text, content_type="text/csv")
        print(f"{GREEN}\t\t export_list - Successfully published {list_name.lower()}.csv to GCS{RESET}")
    except Exception as e:
        print(f"{RED}\t\t export_list - Error uploading to GCS: {e}{RESET}")

# ----------------------
# --- Orchestration ----
# ----------------------

def run_lists_pipeline():

    # Categories to process
    categories = [
        # "Institutional Research - Absence"
        # ,"Institutional Research - Academic"
        # ,"Institutional Research - Activity"
        # ,"Institutional Research - Advisory"
        # ,"Institutional Research - Assessment"
        # ,"Institutional Research - Athletic"
        # ,"Institutional Research - Comment"
        # ,"Institutional Research - Community Group"
        # ,"Institutional Research - Constituent"
        # ,"Institutional Research - Employee"
        # ,"Institutional Research - Grade Average"
        "Institutional Research - Gradebook"
        ,"Institutional Research - Grading"
        ,"Institutional Research - Graduation Class"
        ,"Institutional Research - Honor Roll"
        ,"Institutional Research - Platform"
        ,"Institutional Research - Reportcard Definition"
        ,"Institutional Research - School"
    ]
    
    # Fetch credentials only once as they are valid for 1 hour
    print(f"run_lists_pipeline - Fetching credentials...")
    headers = authenticate()
    
    # Iterate through categories and export lists
    for category in categories:   
        print(f"\nrun_lists_pipeline - Processing Category: {category}")
        list_of_advanced_lists = get_list_of_advanced_lists(headers, category=category)
        for advanced_list in list_of_advanced_lists:
            export_list(advanced_list.get("id"), advanced_list.get("name", f"list_{advanced_list.get('id')}"), headers, category=category)

    print("run_lists_pipeline - All tasks completed.")

def http_entry_point(request: object = None) -> tuple:
    try:
        run_lists_pipeline()
        return "http_entry_point - Workflow completed successfully", 200
    except Exception as e:
        return f"http_entry_point - Error during workflow execution: {e}", 500


# ------------
# --- Main ---
# ------------
if __name__ == "__main__":
    run_lists_pipeline()