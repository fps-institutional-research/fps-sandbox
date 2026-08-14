"""
advanced-list-dataflow.py

Apache Beam pipeline that:
  1. Authenticates with Blackbaud SKY API via GCP Secret Manager once per worker bundle (in setup()).
  2. Discovers all Advanced Lists across specified target categories.
  3. Paginates and flattens list records concurrently while strictly respecting API rate limits (10 req/sec max).
  4. Manages errors with retries and routes failures to a Dead Letter Queue (DLQ).
  5. Groups records by list and exports formatted CSV files directly to Google Cloud Storage (GCS).

Supports local execution (DirectRunner) or Google Cloud Dataflow execution (DataflowRunner).
"""

import csv
import io
import json
import logging
import os
import threading
import time
from collections import deque
from typing import Any, Dict, List, Tuple

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions
from google.cloud import secretmanager, storage
import requests

# ---------------------------------------------------------------------------
# Pipeline Configuration Defaults
# ---------------------------------------------------------------------------
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "institutional-sandbox")
GCS_STAGING_BUCKET = os.environ.get("GCS_STAGING_BUCKET", "495616-bemdam-staging-sandbox")
BLACKBAUD_SKY_ACCESS_TOKEN = "blackbaud-sky-access-token"
BLACKBAUD_SKY_SUBSCRIPTION_KEY = "blackbaud-sky-subscription-key"

MAX_CALLS_PER_SECOND = 9

CATEGORIES = [
    "Institutional Research - Gradebook",
    "Institutional Research - Grading",
    "Institutional Research - Graduation Class",
    "Institutional Research - Honor Roll",
    "Institutional Research - Platform",
    "Institutional Research - Reportcard Definition",
    "Institutional Research - School",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate Limiter
# ---------------------------------------------------------------------------
class ThreadSafeRateLimiter:
    """
    Thread-safe rate limiter enforcing max_calls per period_seconds.
    Uses timestamp reservation so workers sleep independently.
    """
    def __init__(self, max_calls: int = 9, period_seconds: float = 1.0):
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self.lock = threading.Lock()
        self.timestamps: deque = deque()

    def wait(self):
        with self.lock:
            now = time.time()
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


# Global rate limiter instance per worker process
rate_limiter = ThreadSafeRateLimiter(max_calls=MAX_CALLS_PER_SECOND, period_seconds=1.0)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def access_secret_version(secret_id: str, project_id: str = GCP_PROJECT_ID, version_id: str = "latest") -> str | None:
    """Accesses the payload for the given secret version from GCP Secret Manager."""
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Error accessing secret {secret_id}: {e}")
        return None


def authenticate(project_id: str = GCP_PROJECT_ID) -> Dict[str, str] | None:
    """Returns headers required for Blackbaud SKY API requests."""
    access_token = access_secret_version(BLACKBAUD_SKY_ACCESS_TOKEN, project_id=project_id)
    subscription_key = access_secret_version(BLACKBAUD_SKY_SUBSCRIPTION_KEY, project_id=project_id)

    if not access_token or not subscription_key:
        logger.error("Authentication failed: missing credentials in Secret Manager.")
        return None

    return {
        "Authorization": f"Bearer {access_token}",
        "bb-api-subscription-key": subscription_key,
        "Accept": "application/json",
    }


def get_with_retry(url: str, headers: Dict[str, str], project_id: str = GCP_PROJECT_ID) -> requests.Response:
    """
    Performs GET request with rate limiting and automatic retry logic for 429 & 401.
    """
    auth_retried = False
    while True:
        rate_limiter.wait()
        response = requests.get(url, headers=headers)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning(f"Rate limited (429). Retrying after {retry_after}s...")
            time.sleep(retry_after)
            continue

        if response.status_code == 401 and not auth_retried:
            logger.warning("Unauthorized (401). Refreshing token...")
            new_headers = authenticate(project_id=project_id)
            if new_headers:
                headers.update(new_headers)
                auth_retried = True
                continue
            else:
                logger.error("Re-authentication failed.")

        response.raise_for_status()
        return response


# ---------------------------------------------------------------------------
# Beam Transforms / DoFns
# ---------------------------------------------------------------------------
class FetchAdvancedListsFn(beam.DoFn):
    """
    DoFn to fetch list metadata for a target category.
    Per worker setup() fetches secret credentials once per bundle.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.headers = None

    def setup(self):
        """Fetch token once per worker process initialization."""
        self.headers = authenticate(project_id=self.project_id)

    def process(self, category: str):
        if not self.headers:
            yield beam.pvalue.TaggedOutput("dead_letter", {"category": category, "error": "Failed to authenticate"})
            return

        logger.info(f"Fetching list catalog for category: '{category}'")
        url = "https://api.sky.blackbaud.com/school/v1/lists"

        try:
            response = get_with_retry(url, self.headers, project_id=self.project_id)
            data = response.json()
            all_lists = data.get("value", data) if isinstance(data, dict) else data

            matched_count = 0
            for l in all_lists:
                l_category = l.get("category_name", l.get("category", ""))
                if (
                    l_category == category
                    or l_category == f"Institutional Research - {category}"
                    or l_category.strip().lower() == category.strip().lower()
                ):
                    list_id = l.get("id")
                    list_name = l.get("name", f"list_{list_id}")
                    matched_count += 1
                    yield {
                        "category": category,
                        "list_id": list_id,
                        "list_name": list_name,
                    }

            logger.info(f"Found {matched_count} list(s) in category '{category}'")

        except Exception as e:
            logger.exception(f"Error fetching catalog for category '{category}'")
            yield beam.pvalue.TaggedOutput("dead_letter", {"category": category, "error": str(e)})


class FetchListPagesFn(beam.DoFn):
    """
    DoFn to paginate through an advanced list and flatten records into key-value dicts.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.headers = None

    def setup(self):
        """Fetch token once per worker process initialization."""
        self.headers = authenticate(project_id=self.project_id)

    def process(self, list_info: Dict[str, Any]):
        if not self.headers:
            yield beam.pvalue.TaggedOutput("dead_letter", {"list_info": list_info, "error": "Failed to authenticate"})
            return

        category = list_info["category"]
        list_id = list_info["list_id"]
        list_name = list_info["list_name"]
        clean_category = category.replace("Institutional Research - ", "").strip().lower()

        logger.info(f"Processing Advanced List: {list_name} (ID: {list_id})")

        base_url = f"https://api.sky.blackbaud.com/school/v1/lists/advanced/{list_id}"
        page = 1
        total_rows = 0

        while True:
            url = f"{base_url}?page={page}"
            try:
                response = get_with_retry(url, self.headers, project_id=self.project_id)
                data = response.json()
            except Exception as e:
                logger.error(f"[{list_name}] Error on page {page}: {e}")
                yield beam.pvalue.TaggedOutput(
                    "dead_letter",
                    {"category": category, "list_id": list_id, "list_name": list_name, "page": page, "error": str(e)},
                )
                break

            rows = data.get("results", {}).get("rows", [])
            count = data.get("count", 0)

            for row in rows:
                flat_row = {col["name"]: col.get("value") for col in row.get("columns", [])}
                total_rows += 1
                yield {
                    "clean_category": clean_category,
                    "category": category,
                    "list_id": list_id,
                    "list_name": list_name,
                    "row": flat_row,
                }

            if count == 0 or not rows or count < 1000:
                break

            page += 1

        logger.info(f"Completed fetching {list_name}: {total_rows} row(s) across {page} page(s)")


class GroupAndExportToGCSFn(beam.DoFn):
    """
    DoFn to receive grouped rows for a specific list, format into CSV, and upload to GCS.
    """

    def __init__(self, project_id: str, bucket_name: str):
        self.project_id = project_id
        self.bucket_name = bucket_name
        self.storage_client = None

    def setup(self):
        """Initialize Google Cloud Storage client once per worker."""
        self.storage_client = storage.Client(project=self.project_id)

    def process(self, element: Tuple[Tuple[str, str], List[Dict[str, Any]]]):
        (clean_category, list_name), rows = element
        rows_list = list(rows)

        if not rows_list:
            logger.warning(f"No rows to export for {clean_category}/{list_name}")
            return

        gcs_blob_path = f"{clean_category}/{list_name.lower()}.csv"

        try:
            # 1. Format dynamic CSV
            fieldnames = list({key: None for row in rows_list for key in row.keys()}.keys())
            output_buffer = io.StringIO()
            writer = csv.DictWriter(output_buffer, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows_list)
            csv_text = output_buffer.getvalue()

            # 2. Upload to GCS
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(gcs_blob_path)
            blob.upload_from_string(data=csv_text, content_type="text/csv")

            logger.info(
                f"Successfully published gs://{self.bucket_name}/{gcs_blob_path} ({len(rows_list)} rows)"
            )
            yield {
                "status": "success",
                "category": clean_category,
                "list_name": list_name,
                "rows_count": len(rows_list),
                "gcs_path": f"gs://{self.bucket_name}/{gcs_blob_path}",
            }

        except Exception as e:
            logger.exception(f"Error uploading {gcs_blob_path} to GCS")
            yield beam.pvalue.TaggedOutput(
                "dead_letter",
                {"category": clean_category, "list_name": list_name, "error": str(e)},
            )


# ---------------------------------------------------------------------------
# Pipeline Construction & Execution
# ---------------------------------------------------------------------------
def run_pipeline(beam_args: List[str] | None = None) -> None:
    """Constructs and executes the Apache Beam data pipeline."""
    pipeline_options = PipelineOptions(beam_args)
    pipeline_options.view_as(SetupOptions).save_main_session = True

    logger.info("Starting Apache Beam Advanced List Pipeline...")

    with beam.Pipeline(options=pipeline_options) as p:
        # Step 1: Create initial categories PCollection
        categories_pcoll = p | "Create Target Categories" >> beam.Create(CATEGORIES)

        # Step 2: Fetch Advanced Lists catalog for categories
        catalog_results = categories_pcoll | "Fetch Advanced Lists Catalog" >> beam.ParDo(
            FetchAdvancedListsFn(project_id=GCP_PROJECT_ID)
        ).with_outputs("dead_letter", main="lists")

        lists_pcoll = catalog_results.lists
        catalog_dlq = catalog_results.dead_letter

        # Step 3: Paginate through list pages and flatten records
        row_results = lists_pcoll | "Fetch & Flatten List Pages" >> beam.ParDo(
            FetchListPagesFn(project_id=GCP_PROJECT_ID)
        ).with_outputs("dead_letter", main="rows")

        rows_pcoll = row_results.rows
        pages_dlq = row_results.dead_letter

        # Step 4: Key rows by (clean_category, list_name)
        keyed_rows = rows_pcoll | "Key Rows by List" >> beam.Map(
            lambda item: ((item["clean_category"], item["list_name"]), item["row"])
        )

        # Step 5: Group rows by list
        grouped_rows = keyed_rows | "Group Rows by List" >> beam.GroupByKey()

        # Step 6: Export CSVs to GCS
        export_results = grouped_rows | "Export CSVs to GCS" >> beam.ParDo(
            GroupAndExportToGCSFn(project_id=GCP_PROJECT_ID, bucket_name=GCS_STAGING_BUCKET)
        ).with_outputs("dead_letter", main="success")

        export_success = export_results.success
        export_dlq = export_results.dead_letter

        # Step 7: Flatten & Log DLQ records
        _ = (
            (catalog_dlq, pages_dlq, export_dlq)
            | "Flatten DLQ Records" >> beam.Flatten()
            | "Log DLQ Exceptions" >> beam.Map(lambda record: logger.error(f"DLQ Exception: {record}"))
        )

    logger.info("Apache Beam Advanced List Pipeline finished successfully.")


def http_entry_point(request: object = None) -> tuple:
    """HTTP entry point compatible with Cloud Functions or HTTP triggers."""
    try:
        run_pipeline()
        return "http_entry_point - Beam pipeline completed successfully", 200
    except Exception as e:
        logger.exception("Error executing Beam pipeline HTTP entry point")
        return f"http_entry_point - Error during Beam pipeline execution: {e}", 500


# ---------------------------------------------------------------------------
# Main Execution Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    run_pipeline()
