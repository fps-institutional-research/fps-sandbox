import os
import io
import json
import tempfile
from google.cloud import storage
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import google.auth

# --- Configurations ---
# Google Cloud Project
GCP_PROJECT_ID = "amazing-hub-484421-v9"

# Hardcoded Transfer Details
GDRIVE_FOLDER_ID = "1pDGAQGAgZoULVJEaBQRoeLxJxqkpSYyM"
GCS_BUCKET_NAME = "amazing-hub-484421-v9-bq-staging"
GCS_FOLDER_PATH = "raw/incoming_data"

# Path to your Service Account JSON file (Leave empty to use Application Default Credentials)
SERVICE_ACCOUNT_JSON = "/Users/jshwisberg/Desktop/Data/amazing-hub-484421-v9-ca9d8bfeab6e.json"

# Scopes for Google APIs
SCOPES = ['https://www.googleapis.com/auth/drive.readonly', 'https://www.googleapis.com/auth/cloud-platform']

# --- Functions ---
def get_credentials():
    """
    Returns credentials from service account file or default environment.
    """
    if SERVICE_ACCOUNT_JSON and os.path.exists(SERVICE_ACCOUNT_JSON):
        return google.oauth2.service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_JSON, scopes=SCOPES
        )
    
    credentials, project = google.auth.default(scopes=SCOPES)
    return credentials

def get_drive_service():
    """
    Initializes and returns the Google Drive API service.
    """
    credentials = get_credentials()
    return build('drive', 'v3', credentials=credentials)

def download_files_from_gdrive(folder_id: str, local_temp_dir: str) -> list:
    """
    Downloads all files from a specific GDrive folder (including Shared Drives).
    Automatically exports Google Docs/Sheets to binary formats (PDF/CSV).
    Returns a list of local file paths.
    """
    service = get_drive_service()
    downloaded_files = []

    # Mapping of Google App types to export formats and extensions
    export_mapping = {
        'application/vnd.google-apps.spreadsheet': ('text/csv', '.csv'),
        'application/vnd.google-apps.document': ('application/pdf', '.pdf'),
        'application/vnd.google-apps.presentation': ('application/pdf', '.pdf'),
    }

    print(f"Listing files in GDrive folder: {folder_id}...")
    
    # Query for files in the folder. Supports Shared Drives.
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='nextPageToken, files(id, name, mimeType)',
        includeItemsFromAllDrives=True,
        supportsAllDrives=True
    ).execute()
    
    items = results.get('files', [])

    if not items:
        print("No files found in the specified GDrive folder.")
        return []

    for item in items:
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        
        # Skip folders
        if mime_type == 'application/vnd.google-apps.folder':
            continue
            
        # Determine if we need to export or download
        if mime_type in export_mapping:
            export_mime, extension = export_mapping[mime_type]
            # Ensure file name has the correct extension
            if not file_name.lower().endswith(extension):
                file_name += extension
            
            print(f"Exporting {item['name']} as {extension}...")
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        else:
            print(f"Downloading {file_name}...")
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)

        local_file_path = os.path.join(local_temp_dir, file_name)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        with open(local_file_path, 'wb') as f:
            f.write(fh.getvalue())
            
        downloaded_files.append(local_file_path)
        
    return downloaded_files

def upload_to_gcs(file_path: str, bucket_name: str, gcs_folder: str = "") -> None:
    """
    Uploads a file to Google Cloud Storage under a specific folder.
    """
    file_name = os.path.basename(file_path)
    
    # Construct blob name with folder path if provided
    if gcs_folder:
        # Ensure gcs_folder ends with / but doesn't start with it
        gcs_folder = gcs_folder.strip("/") + "/"
        blob_name = f"{gcs_folder}{file_name}"
    else:
        blob_name = file_name

    print(f"Uploading {file_name} to gs://{bucket_name}/{blob_name}...")
    
    # Initialize storage client with specific credentials if account file is provided
    if SERVICE_ACCOUNT_JSON and os.path.exists(SERVICE_ACCOUNT_JSON):
        storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_JSON)
    else:
        storage_client = storage.Client()
        
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)
    print(f"Successfully uploaded: {blob_name}")

def main():
    """Main function to process files using hardcoded settings."""
    processed_count = 0
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # 1. Download files from GDrive
            local_files = download_files_from_gdrive(GDRIVE_FOLDER_ID, temp_dir)
            
            if not local_files:
                return

            # 2. Upload all files to GCS
            for file_path in local_files:
                try:
                    upload_to_gcs(file_path, GCS_BUCKET_NAME, GCS_FOLDER_PATH)
                    processed_count += 1
                except Exception as e:
                    print(f"Error uploading {file_path}: {e}")
                    
        except Exception as e:
            print(f"Error in pipeline: {e}")

    print(f"Finished. Successfully transferred {processed_count} files to GCS.")

if __name__ == "__main__":
    main()