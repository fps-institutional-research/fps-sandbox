"""
sky_api_pipeline.py

Dynamic, configuration-driven pipeline that:
  1. Reads the active schema + endpoint list from endpoint_config.py
  2. Authenticates with Blackbaud SKY API via OAuth 2.0 (Secret Manager)
  3. For each enabled schema → for each enabled endpoint:
       Extract → Flatten → Load into BigQuery
  4. Returns a summary of all sync results

Each schema maps to a different BigQuery dataset, allowing multiple
Blackbaud APIs (School, Enrollment Management, OneRoster) to be
synced in a single pipeline run.

Deploy as a Cloud Function:
    gcloud functions deploy sky-api-sync \
        --gen2 \
        --runtime python312 \
        --trigger-http \
        --entry-point run_pipeline \
        --source . \
        --set-env-vars GCP_PROJECT_ID=<your-project-id> \
        --timeout 540s
"""

import datetime
import json
import logging
import os
from typing import Any

import functions_framework
import requests
from google.cloud import bigquery

from sky_api_connection import get_authenticated_session
from endpoint_config import SCHEMAS

# ---------------------------------------------------------------------------
# Configuration — override via environment variables
# ---------------------------------------------------------------------------
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "your-project-id")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Generic SKY API extraction (works for any endpoint)
# ---------------------------------------------------------------------------

def fetch_endpoint(
    session: requests.Session,
    base_url: str,
    path: str,
    params: dict | None = None,
) -> list[dict]:
    """
    Fetch all records from a SKY API endpoint, handling pagination.

    The SKY API returns data in one of three shapes:
      A) Collection with pagination:  { "count": N, "value": [...], "next_link": "..." }
      B) Plain list / single object:  [ {...}, ... ]  or  { ... }
      C) OneRoster-style wrapper:     { "academicSessions": [...] }

    This function normalises all into a flat list of dicts.
    """
    url = f"{base_url}{path}"
    all_records: list[dict] = []

    while url:
        logger.info("  → GET %s", url)
        response = session.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

        # Clear params after first request — pagination uses next_link
        params = None

        # --- Normalise response shape ---
        if isinstance(payload, list):
            # Shape B: plain list
            all_records.extend(payload)
            url = None
        elif isinstance(payload, dict):
            if "value" in payload:
                # Shape A: collection wrapper (School API style)
                all_records.extend(payload["value"])
                next_link = payload.get("next_link")
                if next_link:
                    url = (
                        f"{base_url}{next_link}"
                        if next_link.startswith("/")
                        else next_link
                    )
                else:
                    url = None
            else:
                # Check for OneRoster-style wrapper: { "key": [...] }
                list_keys = [k for k, v in payload.items() if isinstance(v, list)]
                if list_keys:
                    # Shape C: named collection (e.g. "academicSessions")
                    all_records.extend(payload[list_keys[0]])
                    url = None
                else:
                    # Shape B: single object (e.g. /v1/timezone)
                    all_records.append(payload)
                    url = None
        else:
            url = None

    logger.info("  ✓ Fetched %d records from %s", len(all_records), path)
    return all_records


# ---------------------------------------------------------------------------
# Generic flattening
# ---------------------------------------------------------------------------

def flatten_record(record: dict, flatten_fields: list[str]) -> dict:
    """
    Flatten specified nested objects into prefixed top-level keys.

    Example:
        flatten_fields = ["address"]
        { "id": 1, "address": {"city": "NY"} }
        →
        { "id": 1, "address_city": "NY" }
    """
    flat: dict[str, Any] = {}

    for key, value in record.items():
        if key in flatten_fields and isinstance(value, dict):
            for sub_key, sub_value in value.items():
                flat[f"{key}_{sub_key}"] = sub_value
        else:
            flat[key] = value

    return flat


def transform_records(
    records: list[dict],
    flatten_fields: list[str],
) -> list[dict]:
    """Flatten + add metadata to a batch of records."""
    timestamp = datetime.datetime.utcnow().isoformat()
    transformed = []

    for rec in records:
        flat = flatten_record(rec, flatten_fields)
        flat["_load_timestamp"] = timestamp
        transformed.append(flat)

    return transformed


# ---------------------------------------------------------------------------
# BigQuery loading
# ---------------------------------------------------------------------------

def load_to_bigquery(
    records: list[dict],
    table_name: str,
    bq_dataset: str,
) -> int:
    """
    Load records into BigQuery table ``{PROJECT}.{bq_dataset}.{table_name}``.

    Uses WRITE_TRUNCATE for a clean snapshot each run and autodetect for schema.
    """
    client = bigquery.Client(project=GCP_PROJECT_ID)
    table_ref = f"{GCP_PROJECT_ID}.{bq_dataset}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=True,
    )

    load_job = client.load_table_from_json(
        records,
        table_ref,
        job_config=job_config,
    )
    load_job.result()  # Block until complete

    table = client.get_table(table_ref)
    logger.info(
        "  ✓ Loaded %d rows → %s (total rows: %d)",
        len(records),
        table_ref,
        table.num_rows,
    )
    return len(records)


# ---------------------------------------------------------------------------
# Single-endpoint pipeline step
# ---------------------------------------------------------------------------

def sync_endpoint(
    session: requests.Session,
    base_url: str,
    bq_dataset: str,
    endpoint: dict,
) -> dict:
    """
    Run the full Extract → Transform → Load cycle for one endpoint config entry.

    Returns a result dict with status, row count, and any error message.
    """
    path = endpoint["path"]
    bq_table = endpoint["bq_table"]
    description = endpoint["description"]
    flatten_fields = endpoint.get("flatten_fields", [])
    required_params = endpoint.get("required_params", {})

    logger.info("━━━ Syncing: %s (%s) → %s.%s", description, path, bq_dataset, bq_table)

    try:
        # Extract
        raw = fetch_endpoint(session, base_url, path, params=required_params or None)

        if not raw:
            logger.warning("  ⚠ No records returned for %s", path)
            return {
                "endpoint": path,
                "table": f"{bq_dataset}.{bq_table}",
                "status": "skipped",
                "rows": 0,
                "message": "No records returned",
            }

        # Transform
        flat = transform_records(raw, flatten_fields)

        # Load
        rows = load_to_bigquery(flat, bq_table, bq_dataset)

        return {
            "endpoint": path,
            "table": f"{bq_dataset}.{bq_table}",
            "status": "success",
            "rows": rows,
        }

    except Exception as e:
        logger.exception("  ✗ Failed: %s", path)
        return {
            "endpoint": path,
            "table": f"{bq_dataset}.{bq_table}",
            "status": "error",
            "rows": 0,
            "message": str(e),
        }


# ---------------------------------------------------------------------------
# Cloud Function entry point
# ---------------------------------------------------------------------------

@functions_framework.http
def run_pipeline(request):
    """
    HTTP Cloud Function entry point.

    Processes every active (uncommented) schema and endpoint in
    endpoint_config.SCHEMAS.

    Returns a JSON summary of all sync operations.

    Optional query parameters:
        ?endpoints=core_school_levels,terms
            Limits the run to only the specified bq_table names (comma-separated).
        ?schemas=School,OneRoster
            Limits the run to only the specified schema api_names (comma-separated).
    """
    try:
        # --- Determine filters ---
        filter_tables = None
        filter_schemas = None

        if request and request.args.get("endpoints"):
            filter_tables = set(request.args["endpoints"].split(","))
            logger.info("Filtering to endpoints: %s", filter_tables)

        if request and request.args.get("schemas"):
            filter_schemas = set(request.args["schemas"].split(","))
            logger.info("Filtering to schemas: %s", filter_schemas)

        # --- Authenticate once, reuse session for all endpoints ---
        session, _ = get_authenticated_session(GCP_PROJECT_ID)

        # --- Process each schema ---
        all_results = []

        for schema in SCHEMAS:
            api_name = schema["api_name"]
            base_url = schema["base_url"]
            bq_dataset = schema["bq_dataset"]
            endpoints = schema["endpoints"]

            # Skip schema if filtered out
            if filter_schemas and api_name not in filter_schemas:
                logger.info("Skipping schema: %s (filtered)", api_name)
                continue

            # Filter endpoints if requested
            if filter_tables:
                endpoints = [ep for ep in endpoints if ep["bq_table"] in filter_tables]

            if not endpoints:
                logger.info("No active endpoints for schema: %s", api_name)
                continue

            logger.info(
                "╔══ Schema: %s — %d endpoint(s) to sync → dataset: %s",
                api_name, len(endpoints), bq_dataset,
            )

            for ep in endpoints:
                result = sync_endpoint(session, base_url, bq_dataset, ep)
                result["schema"] = api_name
                all_results.append(result)

        # --- Summary ---
        if not all_results:
            return (
                json.dumps({"status": "warning", "message": "No endpoints configured or matched."}),
                200,
                {"Content-Type": "application/json"},
            )

        succeeded = sum(1 for r in all_results if r["status"] == "success")
        failed = sum(1 for r in all_results if r["status"] == "error")
        skipped = sum(1 for r in all_results if r["status"] == "skipped")
        total_rows = sum(r["rows"] for r in all_results)

        summary = {
            "status": "complete",
            "endpoints_processed": len(all_results),
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "total_rows_loaded": total_rows,
            "details": all_results,
        }

        log_level = logging.WARNING if failed else logging.INFO
        logger.log(log_level, "Pipeline complete: %s", json.dumps(summary, indent=2))

        status_code = 200 if failed == 0 else 207  # 207 Multi-Status if partial failures
        return (json.dumps(summary, indent=2), status_code, {"Content-Type": "application/json"})

    except requests.exceptions.HTTPError as e:
        error_body = e.response.text if e.response is not None else str(e)
        logger.error("SKY API HTTP error: %s — %s", e, error_body)
        return (
            json.dumps({"status": "error", "message": str(e), "detail": error_body}),
            502,
            {"Content-Type": "application/json"},
        )

    except Exception as e:
        logger.exception("Pipeline failed")
        return (
            json.dumps({"status": "error", "message": str(e)}),
            500,
            {"Content-Type": "application/json"},
        )
