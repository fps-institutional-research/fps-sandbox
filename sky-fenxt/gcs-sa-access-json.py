import os
from google.cloud import storage

def test_read_access(bucket_name, key_path):
    print("Initializing Storage Client with JSON key...")
    try:
        # Explicitly load the service account credentials from your JSON key file
        storage_client = storage.Client.from_service_account_json(key_path)
        
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
# Updated to match the active bucket visible in your console
BUCKET_NAME = "495616-boomi-staging" 
# Replace this with the actual path to the JSON file you just downloaded
PATH_TO_JSON_KEY = "/Users/jshwisberg/Desktop/institutional-research-495616-5f8f36176090.json"

test_read_access(BUCKET_NAME, PATH_TO_JSON_KEY)