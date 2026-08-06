import os
import json
import webbrowser
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Step 1: Define scope (which API and what level of access)
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']  # Example: Read Google Drive metadata

# Step 2: Load client secrets (downloaded from Google Cloud Console)
# Save your client credentials JSON file from Google and put its path here
CLIENT_SECRETS_FILE = "client_secret.json"

def main():
    # Step 3: Start OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES)

    # Opens a browser window for user to authenticate
    creds = flow.run_local_server(port=8080)

    # Step 4: Use credentials to call Google API
    service = build('drive', 'v3', credentials=creds)
    results = service.files().list(
        pageSize=10, fields="nextPageToken, files(id, name)").execute()

    files = results.get('files', [])

    # Step 5: Print results
    if not files:
        print('No files found.')
    else:
        print('Files:')
        for file in files:
            print(f"{file['name']} ({file['id']})")

if __name__ == '__main__':
    main()