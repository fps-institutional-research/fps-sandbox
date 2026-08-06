import os
from google.cloud import storage
from google.oauth2 import service_account
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption

def load_credentials_from_p12(p12_path, client_email, project_id, password=b"notasecret"):
    print(f"Loading credentials from P12 file: {p12_path}")
    with open(p12_path, "rb") as f:
        p12_data = f.read()
    
    # Load private key from PKCS12 file (default Google password is "notasecret")
    private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
        p12_data, password
    )
    
    # Convert private key to PEM bytes
    pem_private_key = private_key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.PKCS8,
        encryption_algorithm=NoEncryption()
    )
    
    # Construct standard Google oauth2 credentials
    info = {
        "type": "service_account",
        "project_id": project_id,
        "private_key": pem_private_key.decode("utf-8"),
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    return service_account.Credentials.from_service_account_info(info)

def test_read_access(bucket_name, key_path, client_email, project_id):
    print("Initializing Storage Client with P12 key...")
    try:
        credentials = load_credentials_from_p12(key_path, client_email, project_id)
        storage_client = storage.Client(credentials=credentials)
        
        print(f"Connecting to bucket: {bucket_name}...")
        bucket = storage_client.bucket(bucket_name)
        
        # Attempt to list the objects in the bucket (Requires storage.objects.list)
        print("Attempting to list files (Testing Read-Only Permissions)...")
        blobs = bucket.list_blobs(max_results=5)
        
        print("\n--- Success! Files found in bucket: ---")
        file_count = 0
        for blob in blobs:
            file_count += 1
            print(f" - {blob.name} (Size: {blob.size} bytes)")
            
        if file_count == 0:
            print(" (Bucket is accessible, but currently empty!)")
            
        print("\nRead access test passed successfully!")
        
    except Exception as e:
        print(f"\n[ERROR] Access test failed: {e}")

# --- Configuration ---
BUCKET_NAME = "495616-boomi-staging" 
# Replace this with the actual path to the P12 key file you downloaded
PATH_TO_P12_KEY = "/Users/jshwisberg/Desktop/Data/institutional-research-495616-8d3bb6f98d1b.p12" 

# Note: These values must match the service account details associated with the P12 key.
# You can find the email and project ID in your GCP Console under IAM & Admin > Service Accounts.
SERVICE_ACCOUNT_EMAIL = "boomi-gcs-reader@institutional-research-495616.iam.gserviceaccount.com"
PROJECT_ID = "institutional-research-495616"

test_read_access(BUCKET_NAME, PATH_TO_P12_KEY, SERVICE_ACCOUNT_EMAIL, PROJECT_ID)