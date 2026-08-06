########### Python 3.2 #############
import urllib.request, json
import os
import pandas as pd

os.environ['BB_API_SUBSCRIPTION_KEY'] = '83636218748a46688b993e006c06c6fe'
os.environ['BB_BEARER_TOKEN'] = 'Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjREVjZzVkxIM0FtU1JTbUZqMk04Wm5wWHU3WSIsInR5cCI6IkpXVCJ9.eyJhcHBsaWNhdGlvbmlkIjoiYTA1NmNhNmItYTNhOC00YWM3LWIzMjUtOTk3NjY2MzA2ZTUyIiwibW9kZSI6IkZ1bGwiLCJncmFudGF1dGhvcml0eSI6IkNvbm5lY3Rpb24iLCJlbnZpcm9ubWVudG5hbWUiOiJGcmFuY2lzIFBhcmtlciBTY2hvb2wgU0lTIiwiZW52aXJvbm1lbnRpZCI6InAtdnVBZFpFaWp2MGFSQ1ZkNzM4ODZZZyIsImxlZ2FsZW50aXR5aWQiOiJwLVhsSHV6enhPTVV1Vkk0MDZUNnAwdnciLCJsZWdhbGVudGl0eW5hbWUiOiJGcmFuY2lzIFBhcmtlciBTY2hvb2wiLCJ6b25lIjoicC11c2EwMSIsIm5hbWVpZCI6IjAxYTUyNDA4LTk0M2ItNGMxYS05Mzc5LTgwMzFkZGZlOTM5OCIsImp0aSI6IjY5MGFkZDE0LWY2NGEtNDFjOS1hZGIwLWIyYjBkZjZjOTIwYyIsImV4cCI6MTc0OTE2NTA1OCwiaWF0IjoxNzQ5MTYxNDU4LCJpc3MiOiJodHRwczovL29hdXRoMi5za3kuYmxhY2tiYXVkLmNvbS8iLCJhdWQiOiJibGFja2JhdWQifQ.RNquGetSqVrLpdGmiRJhK50P51p05f-Zv1wD8RlrQ-Dhsg6DDXW74LS5DjUauXNDJV1KcM9LTSx3xzcJWoeoVV8DOoAGje70atIUlNQgzKagOj6duPP2QOeUnQIqupsEjHQJv1jkXyGs6tgSztj2uwRqyCFCZS8pv3Fzhlx031KmKedVYqX3zijiLEkyptPU8RxLxvQZOS33ymxoGtCgRaOgik7zICuI1AZRCV4kgh4XhZzXA2IJJtevkRRq0tTJ95NWgfz1UMnFxSWbeC9uJ1F4uR97lGXahf3XpbCtHCArr4Vm6nH8mcyvn6PmEpxP5EeHknOfNZsqOhrwsbN-Qw'
print(os.environ['BB_API_SUBSCRIPTION_KEY'])
print(os.environ['BB_BEARER_TOKEN'])
print("Environment variables loaded.")
########################################################################

try:
    # Load sensitive credentials from environment variables for security
    #url = "https://api.sky.blackbaud.com/school/v1/athletics/locations"
    url = "https://api.sky.blackbaud.com/school/v1/academics/departments"
    api_key = os.environ.get('BB_API_SUBSCRIPTION_KEY')
    bearer_token = os.environ.get('BB_BEARER_TOKEN')
    if not api_key or not bearer_token:
        raise Exception("API key or Bearer token not set in environment variables.")

    hdr ={
        # Request headers
        'Cache-Control': 'no-cache',
        'Bb-Api-Subscription-Key': api_key,
        'Authorization': bearer_token
    }

    req = urllib.request.Request(url, headers=hdr)
    req.get_method = lambda: 'GET'
    try:
        response = urllib.request.urlopen(req)
        print(f"HTTP Status Code: {response.getcode()}")
        try:
            # Attempt to decode JSON response
            data = json.loads(response.read().decode())
            print(json.dumps(data, indent=2))
            # Save JSON data to Excel file on Desktop
            # Adjust the key below if the data is nested (e.g., data['value'])
            df = pd.DataFrame(data if isinstance(data, list) else data.get('value', data))
            excel_path = os.path.expanduser('~/Desktop/academic_departments.xlsx')
            #excel_path = os.path.expanduser('~/Desktop/athletic_locations.xlsx')
            df.to_excel(excel_path, index=False)
            print(f"Data written to {excel_path}")
        except Exception as json_err:
            print("Failed to decode JSON response:", json_err)
    except urllib.error.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err.code} - {http_err.reason}")
    except urllib.error.URLError as url_err:
        print(f"URL error occurred: {url_err.reason}")
except Exception as e:
    print("General error:", e)
####################################