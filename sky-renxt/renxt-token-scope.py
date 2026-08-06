import requests
import json
import logging
from google.cloud import secretmanager

# Configuration
GCP_PROJECT_ID = "amazing-hub-484421-v9"
ACCESS_TOKEN_SECRET_ID = "blackbaud-api-access-token"
SUBSCRIPTION_KEY_SECRET_ID = "blackbaud-api-subscription-key"

# Common RENXT Endpoints to test scope coverage
ENDPOINTS = [
    {
        "name": "Constituent Search (rnxt.r)",
        "url": "https://api.sky.blackbaud.com/constituent/v1/constituents?search_text=Smith",
        "description": "Basic constituent read access"
    },
    {
        "name": "Communication Preferences (rnxt.r)",
        "url": "https://api.sky.blackbaud.com/constituent/v1/communicationpreferences",
        "description": "Specific constituent preferences"
    },
    {
        "name": "Gifts (rnxt.r)",
        "url": "https://api.sky.blackbaud.com/gift/v1/gifts?limit=1",
        "description": "Fundraising/Gifts read access"
    },
    {
        "name": "Actions (rnxt.r)",
        "url": "https://api.sky.blackbaud.com/constituent/v1/actions?limit=1",
        "description": "Constituent actions read access"
    }
]

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

def test_token_scopes():
    print(f"=== SKY API Scope Test (Project: {GCP_PROJECT_ID}) ===")
    
    # 1. Fetch Credentials
    print("Fetching credentials from Secret Manager...")
    access_token = access_secret_version(ACCESS_TOKEN_SECRET_ID)
    subscription_key = access_secret_version(SUBSCRIPTION_KEY_SECRET_ID)
    
    if not access_token or not subscription_key:
        print("FAILED: Missing credentials. Ensure secrets exist in Secret Manager.")
        return

    headers = {
        "Authorization": f"Bearer {access_token}",
        "bb-api-subscription-key": subscription_key,
        "Content-Type": "application/json"
    }

    results = []

    # 2. Iterate through test endpoints
    for endpoint in ENDPOINTS:
        print(f"\nTesting: {endpoint['name']}...")
        print(f"URL: {endpoint['url']}")
        
        try:
            response = requests.get(endpoint["url"], headers=headers)
            
            status_code = response.status_code
            success = 200 <= status_code < 300
            
            error_message = ""
            if not success:
                try:
                    error_data = response.json()
                    error_message = error_data.get("message", response.text)
                except:
                    error_message = response.text

            results.append({
                "name": endpoint["name"],
                "status": status_code,
                "success": success,
                "error": error_message
            })
            
            if success:
                print(f"✅ SUCCESS ({status_code})")
                # Peek at the data
                data = response.json()
                count = len(data.get("value", [])) if isinstance(data, dict) else "N/A"
                print(f"   Received data. Items count: {count}")
            else:
                print(f"❌ FAILED ({status_code})")
                print(f"   Error: {error_message}")

        except Exception as e:
            print(f"💥 REQUEST ERROR: {str(e)}")
            results.append({
                "name": endpoint["name"],
                "status": "ERROR",
                "success": False,
                "error": str(e)
            })

    # 3. Final Summary
    print("\n" + "="*40)
    print("SCOPE TEST SUMMARY")
    print("="*40)
    for res in results:
        mark = "✅" if res["success"] else "❌"
        print(f"{mark} {res['name']:<30} Status: {res['status']}")
    
    print("\nNext Steps:")
    passed_none = all(not r["success"] for r in results)
    if passed_none:
        print("- Your token likely lacks ANY Raiser's Edge NXT (rnxt) scopes.")
        print("- Verify your SKY API Application has the appropriate permissions.")
        print("- Ensure the user who authorized the token has RENXT access.")
    else:
        print("- Scopes verified for successful endpoints.")
        print("- For failed endpoints, check if specific feature scopes (e.g., gifts) are enabled.")

if __name__ == "__main__":
    test_token_scopes()
