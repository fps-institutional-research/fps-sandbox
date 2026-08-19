import apache_beam as beam
import os
# Enable gRPC fork support to resolve fork_posix.cc errors with Cloud SDKs
os.environ['GRPC_ENABLE_FORK_SUPPORT'] = 'true'
from apache_beam import Reshuffle
from apache_beam.io.requestresponse import (
    Caller, 
    RequestResponseIO, 
    UserCodeExecutionException, 
    UserCodeQuotaException,
    DefaultThrottler,
    ExponentialBackOffRepeater
)
from apache_beam.options.pipeline_options import PipelineOptions
from google.cloud import secretmanager
from google.cloud import storage
import requests
import random
import json
import logging
import math
import time
from datetime import datetime
from requests_oauthlib import OAuth2Session

# Generate a timestamped log filename
# Configure logging to write to the terminal
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
LOGGER = logging.getLogger(__name__)

# =============================================================================
# PHASE 0: CONFIGURATION
# =============================================================================
GCP_PROJECT_ID = "amazing-hub-484421-v9"
GCS_BUCKET_NAME = "amazing-hub-484421-v9-bq-staging"
PAGE_SIZE = 50000 # The number of records to request from the API at a time

# We use a global timestamp to group all files from this run
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def access_secret_version(secret_id, version_id="latest"):
    """Fetches a secret from GCP Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")





# =============================================================================
# PHASE 1: DISCOVER — Get total counts for each endpoint (runs before pipeline)
# =============================================================================

def discover_endpoints(endpoints: list[str], session: OAuth2Session, api_subscription_key: str) -> list[str]:
    """
    For each base endpoint URL, make a single request with limit=1 to discover
    the total record count, then generate all paginated URLs (offset=0, 100, 200...).
    
    Returns a flat list of all page URLs to fetch in parallel.
    """
    headers = {
        'bb-api-subscription-key': api_subscription_key,
    }

    all_page_urls = []

    for base_url in endpoints:
        endpoint_name = base_url.strip('/').split('/')[-1]
        discovery_url = f"{base_url}?limit=1&offset=0"

        LOGGER.info(f"[Discover] Probing {endpoint_name}: {discovery_url}")

        try:
            time.sleep(random.uniform(0.5,1.5))

            response = session.get(discovery_url, headers=headers)

            if response.status_code != 200:
                LOGGER.warning(f"[Discover] {endpoint_name} returned HTTP {response.status_code}. Skipping.")
                continue

            # --- Extract total count ---
            total_count = None
            data = response.json()

            # Check X-Total-Count header (common OneRoster convention)
            header_total = response.headers.get('X-Total-Count')
            if header_total is not None:
                total_count = int(header_total)

            # Check response body for total count
            if total_count is None and isinstance(data, dict):
                status_info = data.get('imsx_statusInfo')
                if isinstance(status_info, dict):
                    tc = status_info.get('totalCount')
                    if tc is not None:
                        total_count = int(tc)
                if total_count is None:
                    tc = data.get('totalCount') or data.get('count')
                    if tc is not None:
                        total_count = int(tc)

            if total_count is None or total_count == 0:
                # Check if there's at least some data on the first page
                page_items = []
                if isinstance(data, list):
                    page_items = data
                elif isinstance(data, dict):
                    for key in ['value', endpoint_name]:
                        if key in data and isinstance(data[key], list):
                            page_items = data[key]
                            break
                    if not page_items:
                        list_keys = [k for k, v in data.items() if isinstance(v, list)]
                        if list_keys:
                            page_items = data[list_keys[0]]

                if not page_items:
                    LOGGER.info(f"[Discover] {endpoint_name}: 0 records. Skipping.")
                    continue
                elif total_count is None:
                    # Can't determine total —- fall back to single URL without offset
                    LOGGER.warning(f"[Discover] {endpoint_name}: total count unknown. Fetching with single-page fallback.")
                    all_page_urls.append(base_url)
                    continue

            # --- Generate all page URLs ---
            num_pages = math.ceil(total_count / PAGE_SIZE)
            LOGGER.info(f"[Discover] {endpoint_name}: {total_count} records → {num_pages} pages ({num_pages} API calls)")

            for page_idx in range(num_pages):
                offset = page_idx * PAGE_SIZE
                page_url = f"{base_url}?limit={PAGE_SIZE}&offset={offset}"
                all_page_urls.append(page_url)

        except Exception as e:
            LOGGER.error(f"[Discover] Error probing {endpoint_name}: {e}")
            continue

        time.sleep(0.3)  # Brief delay between discovery probes

    LOGGER.info(f"[Discover] Complete: {len(all_page_urls)} total page URLs to fetch across {len(endpoints)} endpoints")
    return all_page_urls


# =============================================================================
# PHASE 2: FETCH — Single-page Caller for parallel execution
# =============================================================================

class OneRosterPageCaller(Caller):
    """
    A simple single-page Caller. Each invocation fetches exactly one page URL
    and returns the extracted records as JSON. No internal pagination loop —
    pagination is handled by the Discover phase generating all offset URLs.
    """
    def __init__(self, token_dict: dict, api_subscription_key: str):
        self.token_dict = token_dict
        self.api_subscription_key = api_subscription_key

    def __call__(self, page_url: str, *args, **kwargs) -> tuple:
        """
        Fetch a single page and return (base_endpoint_name, json_string_of_items).
        """
        try:
            LOGGER.info(f"[Fetch] {page_url}")
            # Use OAuth2Session with the provided token dict
            oauth = OAuth2Session(token=self.token_dict)
            response = oauth.get(
                page_url, 
                headers={'bb-api-subscription-key': self.api_subscription_key}
            )

            if response.status_code == 429:
                raise UserCodeQuotaException(f"Rate limited: {response.text}")
            elif response.status_code == 401:
                raise UserCodeExecutionException(f"Unauthorized. Check access token: {response.text}")
            elif response.status_code == 403:
                raise UserCodeExecutionException(f"Forbidden. Check API subscription key: {response.text}")
            elif response.status_code == 404:
                LOGGER.warning(f"[Fetch] {page_url} not found (404). Returning empty.")
                return page_url, json.dumps([])
            elif response.status_code >= 500:
                raise UserCodeExecutionException(f"Server error: {response.status_code} - {response.text}")
            elif 400 <= response.status_code < 500:
                raise UserCodeExecutionException(f"Client error: {response.status_code} - {response.text}")

            response.raise_for_status()
            data = response.json()

            # Extract the list of items from this page
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Try common data keys
                for key in ['value']:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                if not items:
                    # Try endpoint name as key
                    base_path = page_url.split('?')[0]
                    ep_name = base_path.strip('/').split('/')[-1]
                    if ep_name in data and isinstance(data[ep_name], list):
                        items = data[ep_name]
                if not items:
                    # Fallback: first list value in the dict
                    for k, v in data.items():
                        if isinstance(v, list):
                            items = v
                            break

            LOGGER.info(f"[Response] {page_url} → {len(items)} items")
            return page_url, json.dumps(items)

        except requests.exceptions.RequestException as e:
            raise UserCodeExecutionException(f"Request failed: {str(e)}")


# =============================================================================
# OUTPUT: Group pages by endpoint and write NDJSON files
# =============================================================================

def extract_endpoint_name(page_url: str) -> str:
    """Extract the base endpoint name from a paginated URL."""
    base_path = page_url.split('?')[0]
    return base_path.strip('/').split('/')[-1]

def upload_to_gcs(element):
    """
    Consolidates pages for an endpoint and uploads directly to GCS as NDJSON.
    element = (endpoint_name, [page1_json, page2_json, ...])
    """
    endpoint_name, pages_of_items = element
    
    storage_client = storage.Client(project=GCP_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    
    # Destination path in GCS: sky-oneroster-pipeline/<timestamp>/<endpoint_name>.ndjson
    destination_blob_name = f"sky-oneroster-pipeline/{endpoint_name}.ndjson"
    blob = bucket.blob(destination_blob_name)
    
    try:
        LOGGER.info(f"[GCS] Uploading {endpoint_name} to gs://{GCS_BUCKET_NAME}/{destination_blob_name}")
        
        # Stream the data to GCS to avoid local disk and manage memory for large datasets
        with blob.open("w", content_type="application/x-ndjson") as f:
            total_items = 0
            for page_json in pages_of_items:
                page_items = json.loads(page_json) if isinstance(page_json, str) else page_json
                if isinstance(page_items, list):
                    for item in page_items:
                        f.write(json.dumps(item) + '\n')
                        total_items += 1
        
        if total_items == 0:
            LOGGER.info(f"[GCS] {endpoint_name}: 0 items. Deleting empty blob.")
            blob.delete()
        else:
            LOGGER.info(f"[GCS] {endpoint_name} upload complete: {total_items} items.")
            
    except Exception as e:
        LOGGER.error(f"[GCS] Failed to upload {endpoint_name}: {e}")

    return element




# =============================================================================
# PIPELINE
# =============================================================================

def run_pipeline():
    """
    Two-phase ETL pipeline:
      Phase 1 (Discover): Probe each endpoint for total count, generate all page URLs.
      Phase 2 (Fetch):    Fan out page URLs across parallel workers via RequestResponseIO.
    """
    # --- FETCH SECRETS ---
    # Fetch secrets inside here to ensure gRPC is initialized after os setup
    sky_api_subscription_key = access_secret_version("sky-api-subscription-key")
    oneroster_access_token = access_secret_version("oneroster-access-token")
    oneroster_token_dict = {'access_token': oneroster_access_token, 'token_type': 'Bearer'}

    if not oneroster_access_token:
        LOGGER.error("Failed to obtain access token from Secret Manager. Exiting.")
        return

    # Use a dummy session for the discovery phase
    discovery_session = OAuth2Session(token=oneroster_token_dict)

    # List of base endpoints to fetch
    endpoints = [

        # Name: AcademicSessions all
        # Description: Returns a collection of academic sessions.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllAcademicSessions
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/academicSessions", #38KB-03/23/2026

        # Name: Categories all
        # Description: Returns a collection of categories.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllCategories
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/categories", #2KB-03/23/2026

        # Name: Classes all
        # Description: Returns a collection of classes.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllClasses
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/classes", #143KB-03/23/2026

        # Name: Courses all
        # Description: Returns a collection of courses.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllCourses
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/courses", #100KB-03/23/2026

        # Name: Demographics all
        # Description: Returns a collection of user's demographic data.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllDemographics
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/demographics", #53KB-03/23/2026

        # Name: Enrollments all
        # Description: Returns a collection of enrollments.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllEnrollments
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/enrollments", #99KB-03/23/2026

        # Name: GradingPeriods all
        # Description: Returns a collection of grading periods.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllGradingPeriods
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/gradingPeriods", #8KB-03/23/2026

        # Name: LineItems all
        # Description: Returns a collection of line items.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllLineItems
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/lineItems", #23B-03/23/2026

        # Name: Orgs all
        # Description: Returns a collection of organizations.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllOrgs
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/orgs", #24KB-03/23/2026

        # Name: Results all
        # Description: Returns a collection of results.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllResults
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/results", #21B-03/23/2026

        # Name: Schools all
        # Description: Returns a collection of schools.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllSchools
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/schools", #13KB-03/23/2026

        # Name: Students all
        # Description: Returns a collection of student user data.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllStudents
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/students", #189KB-03/23/2026

        # Name: Teachers all
        # Description: Returns a collection of teacher user data.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllTeachers
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/teachers", #123KB-03/23/2026

        # Name: Terms all
        # Description: Returns a collection of terms.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllTerms
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/terms", #22KB-03/23/2026

        # Name: Users all
        # Description: Returns a collection of user data.
        # URL: https://developer.sky.blackbaud.com/api#api=afe-rostr&operation=getAllUsers
        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/users", #171KB-03/23/2026

    ]

    # =========================================================================
    # PHASE 1: DISCOVER — probe each endpoint for total count, generate page URLs
    # =========================================================================
    LOGGER.info("=" * 70)
    LOGGER.info("PHASE 1: DISCOVER")
    LOGGER.info("=" * 70)

    page_urls = discover_endpoints(endpoints, discovery_session, sky_api_subscription_key)

    if not page_urls:
        LOGGER.warning("No page URLs generated. Nothing to fetch.")
        return

    # =========================================================================
    # PHASE 2: FETCH — fan out all page URLs in parallel
    # =========================================================================
    LOGGER.info("=" * 70)
    LOGGER.info(f"PHASE 2: FETCH — {len(page_urls)} page URLs across parallel workers")
    LOGGER.info("=" * 70)

    options = PipelineOptions(flags=[
        "--runner=DirectRunner",
        "--direct_num_workers=8" # Reduced for local stability
        ])

    with beam.Pipeline(options=options) as p:
        _ = (
            p
            | "Create Page URLs" >> beam.Create(page_urls)
            | "Break Fusion" >> Reshuffle()
            | "Fetch Pages" >> RequestResponseIO(
                caller=OneRosterPageCaller(
                    token_dict=oneroster_token_dict,
                    api_subscription_key=sky_api_subscription_key
                ),
                timeout=120.0,
                repeater=ExponentialBackOffRepeater(),
                throttler=DefaultThrottler(
                    window_ms=10000,
                    bucket_ms=1000,
                    overload_ratio=1.2
                )
            )
            | "Filter Empty Pages" >> beam.Filter(lambda x: len(x) > 0 and len(x[1]) > 2)  # skip "[]"
            | "Key By Endpoint" >> beam.Map(lambda x: (extract_endpoint_name(x[0]), x[1]))
            | "Group By Endpoint" >> beam.GroupByKey()
            | "Upload to GCS" >> beam.Map(upload_to_gcs)
        )
def run_pipeline_http(request):
    """
    HTTP Cloud Function entry point.
    This allows the script to be triggered via an HTTP request (e.g. from Cloud Scheduler).
    """
    try:
        run_pipeline()
        return "Pipeline completed successfully", 200
    except Exception as e:
        return f"Error during pipeline: {e}", 500

if __name__ == "__main__":
    run_pipeline()
