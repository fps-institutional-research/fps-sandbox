import requests
from requests.auth import HTTPBasicAuth

# Your OneRoster OAuth 2.0 credentials
client_id = "058b9994-ef61-42fd-a4d7-d349c930fffa"
client_secret = "CQpf/kL5ShrBo9fE+Uxc+di76fkew1NPKTN9YcYB3eg="
token_url = "https://oauth2.sky.blackbaud.com/token"  # Corrected token endpoint

def get_access_token():
    data = {
        'grant_type': 'client_credentials',  # Grant type for OAuth2 client credentials flow
        'scope': 'https://purl.imsglobal.org/spec/or/v1p1/scope/roster.readonly'  # Use 'openid' for Blackbaud SKY API
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    try:
        response = requests.post(
            token_url,
            data=data,
            headers=headers,
            auth=HTTPBasicAuth(client_id, client_secret)
        )
        response.raise_for_status()
        return response.json().get('access_token')
    except requests.exceptions.HTTPError as http_err:
        print("HTTP error occurred:", http_err)
        print("Response content:", response.text)
        return None

if __name__ == "__main__":
    token = get_access_token()
    print("Access Token:", token)