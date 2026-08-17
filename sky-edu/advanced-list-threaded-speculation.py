"""
This program downloads a specific Advanced List from the Blackbaud SKY API.
It uses speculative pagination to download the list in parallel.
Unfortunately, the database timeout is only 1 minute, so resource contention
will likely occur when downloading large lists ( > 1000 rows).

DO NOT USE.
"""

import requests
import json
import csv
import os
import time
import io
import threading
import concurrent.futures
from collections import deque
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
LIST_ID = 155665
MAX_CALLS_PER_SECOND = 9

# Terminal text colors
RED = '\033[31m'
GREEN = '\033[32m'
YELLOW = '\033[33m'
RESET = '\033[0m'  # Crucial to reset color back to default

# ------------------------
# --- Rate Limiter -------
# ------------------------
class RateLimiter:
    """
    Thread-safe rate limiter enforcing max_calls within period_seconds across all threads.
    Uses timestamp reservation so threads sleep independently without holding the lock.
    """
    def __init__(self, max_calls=9, period_seconds=1.0):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.lock = threading.Lock()
        self.timestamps = deque()

    def wait(self):
        with self.lock:
            now = time.time()
            # Remove timestamps outside the rolling window relative to now
            while self.timestamps and now - self.timestamps[0] >= self.period_seconds:
                self.timestamps.popleft()

            if len(self.timestamps) >= self.max_calls:
                scheduled = max(now, self.timestamps[-self.max_calls] + self.period_seconds)
            else:
                scheduled = now

            sleep_time = scheduled - now
            self.timestamps.append(scheduled)

        if sleep_time > 0:
            time.sleep(sleep_time)


# Global rate limiter instance
rate_limiter = RateLimiter(max_calls=MAX_CALLS_PER_SECOND, period_seconds=1.0)
AUTH_LOCK = threading.Lock()

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


def get_with_retry(url, headers, max_retries=3, timeout=59, report_name="", category=""):
    """
    Performs a GET request with rate limiting and retry logic for:
      - 429 Too Many Requests: waits Retry-After seconds and retries.
      - 401 Unauthorized: re-authenticates safely using AUTH_LOCK.
      - 5xx Server Errors & Timeouts: retries up to max_retries with backoff.
    """
    thread_name = threading.current_thread().name
    cat_label = category.replace("Institutional Research - ", "").strip() if category else ""
    cat_tag = f" [{cat_label}]" if cat_label else ""
    rep_tag = f" '{report_name}'" if report_name else ""
    prefix = f"[{thread_name}]{cat_tag}{rep_tag}"
    auth_retried = False
    retries = 0
    while True:
        rate_limiter.wait()
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            retries += 1
            if retries <= max_retries:
                wait_sec = retries * 5
                print(f"{YELLOW}{prefix} get_with_retry - Connection/Timeout error ({e}). Retrying ({retries}/{max_retries}) in {wait_sec}s...{RESET}")
                time.sleep(wait_sec)
                continue
            else:
                raise

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            print(f"{YELLOW}{prefix} get_with_retry - Rate limited (429). Waiting {retry_after}s...{RESET}")
            time.sleep(retry_after)
            continue

        if response.status_code == 401 and not auth_retried:
            print(f"{YELLOW}{prefix} get_with_retry - Unauthorized (401). Re-authenticating across threads...{RESET}")
            with AUTH_LOCK:
                new_headers = authenticate()
                if new_headers:
                    headers.update(new_headers)
                    auth_retried = True
                    continue
                else:
                    print(f"{RED}{prefix} get_with_retry - Re-authentication failed. Aborting request.{RESET}")

        if response.status_code >= 500:
            retries += 1
            if retries <= max_retries:
                wait_sec = retries * 5
                print(f"{YELLOW}{prefix} get_with_retry - Server Error {response.status_code} ({response.text[:100]}). Retrying ({retries}/{max_retries}) in {wait_sec}s...{RESET}")
                time.sleep(wait_sec)
                continue

        if not response.ok:
            print(f"{RED}{prefix} get_with_retry - Error {response.status_code}: {response.text}{RESET}")

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
    
    print(f"\t get_list_of_advanced_lists - Found {len(ir_lists)} list(s) in '{category}'")
    return ir_lists

def _fetch_page(page, base_url, headers):
    """Worker function to fetch a single page of an advanced list."""
    url = f"{base_url}?page={page}"
    try:
        response = get_with_retry(url, headers)
        data = response.json()
        rows = data.get("results", {}).get("rows", [])
        count = data.get("count", 0)
        flat_rows = [{col["name"]: col.get("value") for col in row.get("columns", [])} for row in rows]
        return page, count, flat_rows
    except Exception as e:
        print(f"\t\t _fetch_page - Failed to fetch page {page}: {e}")
        return page, 0, []

def export_list(list_id, list_name, headers, category="Academics"):
    """
    Fetches a single advanced list with threaded pagination and exports to destination.
    """
    print(f"\n\t\t export_list - Processing List: {list_name} (ID: {list_id})")

    base_url = f"https://api.sky.blackbaud.com/school/v1/lists/advanced/{list_id}"
    page_results = {}
    
    # We will speculatively fetch up to MAX_WORKERS pages at a time
    MAX_WORKERS = 5
    page = 1
    eof_reached = False

    print(f"\t\t export_list - Starting speculative pagination with {MAX_WORKERS} workers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        
        # Dispatch initial batch of pages
        for _ in range(MAX_WORKERS):
            futures[executor.submit(_fetch_page, page, base_url, headers)] = page
            page += 1
            
        while futures:
            # Wait for the first future(s) to complete
            done, _ = concurrent.futures.wait(futures.keys(), return_when=concurrent.futures.FIRST_COMPLETED)
            
            for future in done:
                p_returned = futures.pop(future)
                try:
                    p, count, flat_rows = future.result()
                    page_results[p] = flat_rows
                    print(f"\t\t export_list - Page {p}: {count} record(s) returned")
                    
                    # If a page returns less than 1000 items, we know it's the last valid page
                    if count < 1000:
                        eof_reached = True
                except Exception as e:
                    print(f"\t\t export_list - Error processing future for page {p_returned}: {e}")
                    eof_reached = True
                
                # If we haven't hit the end of the list, dispatch the next page
                if not eof_reached:
                    futures[executor.submit(_fetch_page, page, base_url, headers)] = page
                    page += 1

    # Reassemble pages in order
    all_rows = []
    for p in sorted(page_results.keys()):
        all_rows.extend(page_results[p])
        
    print(f"\t\t export_list - Finished pagination. Total records fetched: {len(all_rows)}")

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
    # 2. Publish CSV to Google Cloud Storage
    clean_category = category.replace("Institutional Research - ", "").strip().lower()
    gcs_blob_path = f"{clean_category}/{list_name.lower()}.csv"
    print(f"\t\t export_list - Publishing to GCS... (gs://{GCS_STAGING_BUCKET}/{gcs_blob_path})")
    try:
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(GCS_STAGING_BUCKET)
        blob = bucket.blob(gcs_blob_path)
        blob.upload_from_string(data=csv_text, content_type="text/csv")
        print(f"{GREEN}\t\t export_list - Successfully published {list_name} to GCS!{RESET}")
    except Exception as e:
        print(f"{RED}\t\t export_list - Error uploading to GCS: {e}{RESET}")

# ----------------------
# --- Orchestration ----
# ----------------------

def run_lists_pipeline():

    # Categories to process
    categories = [
        "Institutional Research - Absence"
        ,"Institutional Research - Academic"
        ,"Institutional Research - Activity"
        ,"Institutional Research - Advisory"
        ,"Institutional Research - Assessment"
        ,"Institutional Research - Athletic"
        ,"Institutional Research - Comment"
        ,"Institutional Research - Community Group"
        ,"Institutional Research - Constituent"
        ,"Institutional Research - Employee"
        ,"Institutional Research - Grade Average"
        ,"Institutional Research - Gradebook"
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
            if advanced_list.get("id") == LIST_ID:
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