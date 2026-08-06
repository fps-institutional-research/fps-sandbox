import os
from dotenv import load_dotenv

# Path resolution is no longer needed after editable install
from sky_api_custom_auth import authenticate_interactive

def main():
    load_dotenv()
    
    CLIENT_ID = os.environ.get('BB_CLIENT_ID')
    CLIENT_SECRET = os.environ.get('BB_CLIENT_SECRET')
    SUBSCRIPTION_KEY = os.environ.get('BB_API_SUBSCRIPTION_KEY')
    
    if not all([CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_KEY]):
        print("Error: Missing environment variables (BB_CLIENT_ID, BB_CLIENT_SECRET, BB_API_SUBSCRIPTION_KEY)")
        return
        
    print("Authenticating with Blackbaud API...")
    try:
        oauth_client = authenticate_interactive(CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_KEY)
        
        print("\nMaking test request...")
        response = oauth_client.make_authenticated_request(
            '/school/v1/athletics/departments',
            SUBSCRIPTION_KEY
        )
        print("Success! Response from Blackbaud received.")
        print("Response length:", len(response['value']))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()