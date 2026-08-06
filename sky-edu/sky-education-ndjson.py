import requests
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        response.raise_for_status()
        return response

def export_students():
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

    # 2. Query for roles to find the correct Student ID
    print("Querying for roles...")
    roles_url = "https://api.sky.blackbaud.com/school/v1/roles"
    
    try:
        response = get_with_retry(roles_url, headers)
        roles_data = response.json()
        roles = roles_data.get("value", [])
        
        student_role_id = None
        for role in roles:
            if role.get("name") == "Student":
                student_role_id = role.get("id")
                break
        
        if not student_role_id:
            print("FAILED: Could not find 'Student' role.")
            return

        # 3. Query for students using the ID with pagination
        print(f"Querying for students (Role ID: {student_role_id})...")
        students = []
        next_url = f"https://api.sky.blackbaud.com/school/v1/users?roles={student_role_id}"
        
        while next_url:
            if next_url.startswith("/"):
                next_url = f"https://api.sky.blackbaud.com/school{next_url}"
                
            response = get_with_retry(next_url, headers)
            users_data = response.json()
            
            page_students = users_data.get("value", [])
            students.extend(page_students)
            print(f"Fetched {len(page_students)} students (Total: {len(students)})...")
            
            next_url = users_data.get("next_link")
        
        print(f"Total students found: {len(students)}")

        # 4. Fetch education data for each student (concurrent, max 10 workers)
        print("Fetching education records for each student (concurrent)...")
        education_records = []
        completed_count = 0

        def fetch_education(student):
            user_id = student.get("id")
            if not user_id:
                return []
            edu_url = f"https://api.sky.blackbaud.com/school/v1/users/{user_id}/education"
            
            try:
                edu_response = get_with_retry(edu_url, headers)
                edu_data = edu_response.json()
                records = edu_data.get("value", [])
                for record in records:
                    record["user_id"] = user_id
                return records
            except Exception as e:
                print(f"  Warning: Failed to fetch education for user {user_id}: {e}")
                return []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {}
            for s in students:
                futures[executor.submit(fetch_education, s)] = s
                time.sleep(.15)  # rate-limit to max 10 requests/sec
            for future in as_completed(futures):
                records = future.result()
                education_records.extend(records)
                completed_count += 1
                if completed_count % 100 == 0:
                    print(f"  Processed {completed_count}/{len(students)} students ({len(education_records)} education records so far)...")

        print(f"Total education records found: {len(education_records)}")

        # 5. Export students to Desktop in NDJSON
        desktop_path = os.path.expanduser("~/Desktop/students.ndjson")
        print(f"Exporting students to {desktop_path}...")
        with open(desktop_path, "w", encoding="utf-8") as f:
            for student in students:
                f.write(json.dumps(student) + "\n")
        print(f"Successfully exported {len(students)} students.")
 
        # 6. Export education records to Desktop in NDJSON
        edu_desktop_path = os.path.expanduser("~/Desktop/student_education.ndjson")
        print(f"Exporting education records to {edu_desktop_path}...")
        with open(edu_desktop_path, "w", encoding="utf-8") as f:
            for record in education_records:
                f.write(json.dumps(record) + "\n")
        print(f"Successfully exported {len(education_records)} education records to Desktop.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    export_students()
