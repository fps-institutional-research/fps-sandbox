import requests
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

#print(f"Sky API Subscription Key: {sky_api_subscription_key}")
#print(f"OneRoster Access Token: {oneroster_access_token}")
#exit()

# --- 2. The Probe Configuration ---
# We ask for a massive number to force the API to reveal its ceiling
TEST_LIMIT = 50000 
URL = f"https://api.sky.blackbaud.com/afe-rostr/ims/oneroster/v1p1/enrollments?limit={TEST_LIMIT}&offset=0"

headers = {
    "Authorization": f"Bearer {oneroster_access_token}",
    "Bb-Api-Subscription-Key": sky_api_subscription_key
}

print(f"🚀 Probing Blackbaud OneRoster API with limit={TEST_LIMIT}...")
response = requests.get(URL, headers=headers)

# --- 3. Evaluate the Results ---
if response.status_code == 200:
    data = response.json()
    # OneRoster wraps the array in the endpoint name
    records = data.get("enrollments", []) 
    
    print("\n✅ SUCCESS (200 OK)")
    print(f"Requested Limit: {TEST_LIMIT}")
    print(f"Actually Received: {len(records)} records")
    
    if len(records) == TEST_LIMIT:
        print("\n🏆 Conclusion: The API actually allowed the massive limit! You can safely update your pipeline to use limit=1000 or higher.")
    else:
        print(f"\n🕵️ Conclusion: The API silently truncated your request. The true maximum limit enforced by Blackbaud is: {len(records)}")

elif response.status_code == 400:
    print("\n🛑 REJECTED (400 Bad Request)")
    print(f"Error Message: {response.text}")
    print("\n🕵️ Conclusion: The API explicitly rejects oversized limits. Read the error message above to find the exact maximum allowed value.")

else:
    print(f"\n⚠️ Unexpected Status {response.status_code}: {response.text}")