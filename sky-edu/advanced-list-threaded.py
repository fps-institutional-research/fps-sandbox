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

# Concurrency & Rate Limiting Configuration
# Blackbaud SKY API limit: 10 calls per second. 9 calls per second is a safe threshold.
MAX_CALLS_PER_SECOND = 9
MAX_WORKER_THREADS = 5

# Threading Lock
AUTH_LOCK = threading.Lock()

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
        print(f"{RED}authenticate - FAILED: Missing credentials.{RESET}")
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
    url = "https://api.sky.blackbaud.com/school/v1/lists"
    response = get_with_retry(url, headers, report_name=f"Catalog:{category}", category=category)
    data = response.json()
    
    # Handle both direct list response and 'value' wrapper
    all_lists = data.get("value", data) if isinstance(data, dict) else data
    
    # Filtering for category
    ir_lists = []
    for l in all_lists:
        l_category = l.get("category_name", l.get("category", ""))
        if l_category == category or l_category == f"Institutional Research - {category}" or l_category.strip().lower() == category.strip().lower():
            ir_lists.append(l)
    
    return ir_lists

def export_list(list_id, list_name, headers, category="Academics"):
    """
    Fetches a single advanced list with pagination and exports to GCS.
    """
    thread_name = threading.current_thread().name
    cat_label = category.replace("Institutional Research - ", "").strip()
    tag = f"[{thread_name}] [{cat_label}]"
    print(f"{tag} Starting report '{list_name}' (ID: {list_id})")

    base_url = f"https://api.sky.blackbaud.com/school/v1/lists/advanced/{list_id}"
    all_rows = []
    page = 1
    failed_page = False

    while True:
        url = f"{base_url}?page={page}"
        try:
            response = get_with_retry(url, headers, report_name=list_name, category=category)
            data = response.json()
        except Exception as e:
            print(f"{RED}{tag} Failed to fetch page {page} for '{list_name}': {e}{RESET}")
            failed_page = True
            break

        # Response shape: {"count": N, "page": N, "results": {"rows": [...]}}
        rows = data.get("results", {}).get("rows", [])
        count = data.get("count", 0)

        # Flatten each row's columns list [{"name":..., "value":...}] into a plain dict
        flat_rows = [{col["name"]: col.get("value") for col in row.get("columns", [])} for row in rows]
        all_rows.extend(flat_rows)

        # Log active page progress (including final partial page)
        if count > 0:
            print(f"{tag} '{list_name}' - Page {page} complete (+{count} rows | {len(all_rows)} total)")

        # Stop when the page returns no records or fewer than a full page (1000)
        if count == 0 or not rows or count < 1000:
            break

        page += 1

    if failed_page:
        print(f"{RED}{tag} Aborting GCS publish for '{list_name}' due to failed page fetch. Incomplete data was NOT uploaded.{RESET}")
        return

    if not all_rows:
        print(f"{YELLOW}{tag} No data found for '{list_name}' (ID: {list_id}). Skipping export.{RESET}")
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
    try:
        storage_client = storage.Client(project=GCP_PROJECT_ID)
        bucket = storage_client.bucket(GCS_STAGING_BUCKET)
        blob = bucket.blob(gcs_blob_path)
        blob.upload_from_string(data=csv_text, content_type="text/csv")
        print(f"{GREEN}{tag}\tPublished '{list_name}' ({len(all_rows)} rows across {page} pages) -> gs://{GCS_STAGING_BUCKET}/{gcs_blob_path}{RESET}")
    except Exception as e:
        print(f"{RED}{tag}\tError uploading '{list_name}' to GCS: {e}{RESET}")

# ----------------------
# --- Orchestration ----
# ----------------------

def process_category(category, headers):
    """
    Worker function that fetches catalog and exports all lists within a single category sequentially.
    """
    thread_name = threading.current_thread().name
    print(f"[{thread_name}] Fetching list catalog for '{category}'...")
    
    list_of_advanced_lists = get_list_of_advanced_lists(headers, category=category)
    print(f"[{thread_name}] Discovered {len(list_of_advanced_lists)} list(s) in '{category}'. Exporting sequentially...")

    for advanced_list in list_of_advanced_lists:
        list_id = advanced_list.get("id")
        list_name = advanced_list.get("name", f"list_{list_id}")
        export_list(
            list_id=list_id,
            list_name=list_name,
            headers=headers,
            category=category
        )

    print(f"{GREEN}[{thread_name}] Category Completed: '{category}'{RESET}")

def run_lists_pipeline(max_workers=MAX_WORKER_THREADS):

    # Categories to process
    categories = [
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
    if not headers:
        print(f"{RED}\trun_lists_pipeline - Authentication failed. Exiting.{RESET}")
        return

    num_workers = min(max_workers, len(categories)) if max_workers else len(categories)
    print(f"run_lists_pipeline - Launching pipeline for {len(categories)} categories using {num_workers} category worker threads...")
    # Note: Categories run concurrently; reports run sequentially to avoid SQL table contention

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {executor.submit(process_category, category, headers): category for category in categories}
        for future in concurrent.futures.as_completed(futures):
            category = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"{RED}run_lists_pipeline - Error processing category '{category}': {e}{RESET}")

    print(f"{GREEN}run_lists_pipeline - All category pipelines completed successfully.{RESET}")

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
