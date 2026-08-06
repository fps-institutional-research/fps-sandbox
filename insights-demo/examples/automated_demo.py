import os
import json
from dotenv import load_dotenv

# Importing from the successfully installed sky_api_custom_auth package
from sky_api_custom_auth import authenticate_automation

def main():
    load_dotenv()
    
    CLIENT_ID = os.environ.get('BB_CLIENT_ID')
    CLIENT_SECRET = os.environ.get('BB_CLIENT_SECRET')
    SUBSCRIPTION_KEY = os.environ.get('BB_API_SUBSCRIPTION_KEY')
    
    # Optional credentials for service account automation
    SERVICE_EMAIL = os.environ.get('SERVICE_EMAIL')
    SERVICE_PW = os.environ.get('SERVICE_PW')
    SERVICE_TOTP = os.environ.get('SERVICE_TOTP')
    
    if not all([CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_KEY]):
        print("Error: Missing base environment variables (BB_CLIENT_ID, BB_CLIENT_SECRET, BB_API_SUBSCRIPTION_KEY)")
        return
        
    if not all([SERVICE_EMAIL, SERVICE_PW, SERVICE_TOTP]):
        print("Error: Missing automation credentials (SERVICE_EMAIL, SERVICE_PW, SERVICE_TOTP)")
        print("These are required for the automated (Selenium) login flow.")
        return
        
    print("Starting AUTOMATED OAuth authentication (Selenium)...")
    try:
        # This will open a Chrome window and automatically complete the login
        oauth_client = authenticate_automation(CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_KEY)
        
        print("\nMaking test request...")
        response = oauth_client.make_authenticated_request(
            '/school/v1/athletics/locations',
            SUBSCRIPTION_KEY
        )
        print("Success! Automated login and request complete.")
        print("Response length:", len(response['value']))
    except Exception as e:
        print(f"Automated authentication failed: {e}")

if __name__ == "__main__":
    main()
