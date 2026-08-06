"""
OneRoster API Preview / Discovery Script

Makes a single request per endpoint (with limit=1) to discover total record counts,
then calculates the number of pages and API calls needed to fetch all data.

Usage:
    python preview.py
"""

import requests
import json
import math
import time
from google.cloud import secretmanager

GCP_PROJECT_ID = "amazing-hub-484421-v9"

def access_secret_version(secret_id, version_id="latest"):
    """
    Accesses the payload for the given secret version if one exists.
    """
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

# --- 1. Retrieve credentials from Secret Manager ---
sky_api_subscription_key = access_secret_version("sky-api-subscription-key")
oneroster_access_token = access_secret_version("oneroster-access-token")

# Page size used by the full pipeline (OneRoster default)
PAGE_SIZE = 50000

# All OneRoster endpoints to check
ENDPOINTS = [
    ("AcademicSessions", "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/academicSessions"),
    ("Categories",       "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/categories"),
    ("Classes",          "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/classes"),
    ("Courses",          "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/courses"),
    ("Demographics",     "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/demographics"),
    ("Enrollments",      "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/enrollments"),
    ("GradingPeriods",   "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/gradingPeriods"),
    ("LineItems",        "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/lineItems"),
    ("Orgs",             "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/orgs"),
    ("Results",          "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/results"),
    ("Schools",          "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/schools"),
    ("Students",         "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/students"),
    ("Teachers",         "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/teachers"),
    ("Terms",            "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/terms"),
    ("Users",            "https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/users"),
]




def get_total_count(url, headers):
    """
    Fetch a single record from the endpoint and extract the total count
    from the response headers or body.
    """
    preview_url = f"{url}?limit=1&offset=0"
    response = requests.get(preview_url, headers=headers)

    if response.status_code != 200:
        return None, response.status_code, None

    # --- Try to get total count from response headers ---
    # OneRoster APIs commonly use X-Total-Count header
    total = response.headers.get('X-Total-Count')

    # --- Try to get total count from response body ---
    data = response.json()
    if total is None and isinstance(data, dict):
        # Check imsx_statusInfo (standard OneRoster)
        status_info = data.get('imsx_statusInfo')
        if isinstance(status_info, dict):
            total = status_info.get('totalCount')
        # Check root-level keys
        if total is None:
            total = data.get('totalCount') or data.get('count')

    # --- Determine actual record count from first page ---
    first_page_count = 0
    if isinstance(data, list):
        first_page_count = len(data)
    elif isinstance(data, dict):
        # Look for the data list in common keys
        for key in ['value', url.strip('/').split('/')[-1]]:
            if key in data and isinstance(data[key], list):
                first_page_count = len(data[key])
                break
        if first_page_count == 0:
            # Fallback: find first list value
            for k, v in data.items():
                if isinstance(v, list):
                    first_page_count = len(v)
                    break

    # --- Check for pagination Link header to confirm more pages exist ---
    has_next = False
    link_header = response.headers.get('Link', '')
    if 'rel="next"' in link_header or "rel='next'" in link_header:
        has_next = True
    if isinstance(data, dict):
        if data.get('nextLink') or data.get('next_link') or data.get('next'):
            has_next = True

    return total, response.status_code, {
        'first_page_count': first_page_count,
        'has_next': has_next,
        'response_keys': list(data.keys()) if isinstance(data, dict) else '[list]',
        'headers': dict(response.headers),
    }


def main():
    print("=" * 90)
    print("  OneRoster API Endpoint Preview")
    print("=" * 90)

    headers = {
        'Authorization': f'Bearer {oneroster_access_token}',
        'Content-Type': 'application/json',
        'bb-api-subscription-key': sky_api_subscription_key,
    }

    results = []
    total_records_all = 0
    total_api_calls_all = 0

    for name, url in ENDPOINTS:
        total, status_code, info = get_total_count(url, headers)
        time.sleep(0.5)  # Small delay to avoid rate limiting

        if status_code != 200:
            results.append({
                'name': name,
                'status': status_code,
                'total': None,
                'pages': None,
                'api_calls': None,
                'note': f'HTTP {status_code}',
            })
            continue

        total_int = int(total) if total is not None else None

        if total_int is not None:
            pages = math.ceil(total_int / PAGE_SIZE)
            api_calls = pages  # 1 API call per page
        elif info['has_next']:
            # We know there's more than 1 record but don't know total
            pages = None
            api_calls = None
        else:
            # Likely a small endpoint with ≤1 record
            pages = 1
            api_calls = 1
            total_int = info['first_page_count']

        results.append({
            'name': name,
            'status': status_code,
            'total': total_int,
            'pages': pages,
            'api_calls': api_calls,
            'first_page_count': info['first_page_count'],
            'has_next': info['has_next'],
        })

        if total_int is not None:
            total_records_all += total_int
        if api_calls is not None:
            total_api_calls_all += api_calls

    # --- Print Results Table ---
    print()
    print(f"  {'Endpoint':<20} {'Status':<8} {'Total Records':<15} {'Pages':<8} {'API Calls':<10}")
    print(f"  {'-'*20} {'-'*8} {'-'*15} {'-'*8} {'-'*10}")

    for r in results:
        status = str(r['status'])
        total = str(r['total']) if r['total'] is not None else 'unknown'
        pages = str(r['pages']) if r['pages'] is not None else 'unknown'
        api_calls = str(r['api_calls']) if r['api_calls'] is not None else 'unknown'

        if r['status'] != 200:
            print(f"  {r['name']:<20} {status:<8} {'—':<15} {'—':<8} {'—':<10}  ⚠ {r.get('note', '')}")
        else:
            print(f"  {r['name']:<20} {status:<8} {total:<15} {pages:<8} {api_calls:<10}")

    print(f"  {'-'*20} {'-'*8} {'-'*15} {'-'*8} {'-'*10}")
    print(f"  {'TOTAL':<20} {'':8} {str(total_records_all):<15} {'':8} {str(total_api_calls_all):<10}")
    print()
    print(f"  Page size: {PAGE_SIZE} records per API call")
    print(f"  Preview API calls used: {len(ENDPOINTS)} (1 per endpoint)")
    print("=" * 90)


if __name__ == '__main__':
    main()
