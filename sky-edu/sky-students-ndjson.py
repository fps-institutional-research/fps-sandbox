import requests
import json
import os
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
        response = requests.get(roles_url, headers=headers)
        response.raise_for_status()
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
                
            response = requests.get(next_url, headers=headers)
            response.raise_for_status()
            users_data = response.json()
            
            page_students = users_data.get("value", [])
            students.extend(page_students)
            print(f"Fetched {len(page_students)} students (Total: {len(students)})...")
            
            next_url = users_data.get("next_link")
        
        print(f"Total students found: {len(students)}")
        
        # 4. Export to Desktop in NDJSON
        desktop_path = os.path.expanduser("~/Desktop/students.ndjson")
        print(f"Exporting to {desktop_path}...")
        
        with open(desktop_path, "w", encoding="utf-8") as f:
            for student in students:
                f.write(json.dumps(student) + "\n")
        
        print(f"Successfully exported {len(students)} students to Desktop in NDJSON format.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    export_students()
