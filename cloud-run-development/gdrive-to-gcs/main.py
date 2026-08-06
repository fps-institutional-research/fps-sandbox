# Not yet configured in Cloud Run
# Need to setup secret manager for service account JSON credentials

import os
import io
import json
import tempfile
from google.cloud import storage
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import google.auth
# pyrefly: ignore [missing-import]
import functions_framework

# --- Configurations ---
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT", "amazing-hub-484421-v9")
DEFAULT_BUCKET_NAME = os.environ.get("GCS_BUCKET", "amazing-hub-484421-v9-bq-staging")
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    credentials, project = google.auth.default(scopes=SCOPES)
    return build('drive', 'v3', credentials=credentials)

def download_and_upload(gdrive_folder_id, gcs_bucket_name, gcs_folder_path):
    service = get_drive_service()
    storage_client = storage.Client()
    bucket = storage_client.bucket(gcs_bucket_name)

    export_mapping = {
        'application/vnd.google-apps.spreadsheet': ('text/csv', '.csv'),
        'application/vnd.google-apps.document': ('application/pdf', '.pdf'),
        'application/vnd.google-apps.presentation': ('application/pdf', '.pdf'),
    }

    query = f"'{gdrive_folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        includeItemsFromAllDrives=True,
        supportsAllDrives=True,
        fields="files(id, name, mimeType)"
    ).execute()
    
    items = results.get('files', [])
    processed_count = 0

    for item in items:
        file_id = item['id']
        file_name = item['name']
        mime_type = item['mimeType']
        
        if mime_type == 'application/vnd.google-apps.folder':
            continue

        # Setup export/download
        if mime_type in export_mapping:
            export_mime, extension = export_mapping[mime_type]
            if not file_name.lower().endswith(extension):
                file_name += extension
            request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        else:
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)

        # Upload directly to GCS using a streaming approach (if small enough for memory)
        # For simplicity and robustness in functions, we'll use a temp file
        with tempfile.NamedTemporaryFile() as tmp:
            downloader = MediaIoBaseDownload(tmp, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            blob_name = f"{gcs_folder_path.strip('/')}/{file_name}" if gcs_folder_path else file_name
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(tmp.name)
            processed_count += 1
            print(f"Uploaded: {blob_name}")

    return processed_count

@functions_framework.http
def gdrive_to_gcs_http(request):
    """
    HTTP Cloud Function entry point.
    Expected JSON body:
    {
        "gdrive_folder_id": "...",
        "gcs_folder_path": "raw/data",
        "bucket": "optional-bucket-name"
    }
    """
    request_json = request.get_json(silent=True)
    
    if not request_json or 'gdrive_folder_id' not in request_json:
        return "Error: Missing gdrive_folder_id", 400

    gdrive_id = request_json['gdrive_folder_id']
    gcs_folder = request_json.get('gcs_folder_path', '')
    bucket_name = request_json.get('bucket', DEFAULT_BUCKET_NAME)

    try:
        count = download_and_upload(gdrive_id, bucket_name, gcs_folder)
        return {
            "status": "success",
            "files_processed": count,
            "destination": f"gs://{bucket_name}/{gcs_folder}"
        }, 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error processing transfer: {str(e)}", 500
