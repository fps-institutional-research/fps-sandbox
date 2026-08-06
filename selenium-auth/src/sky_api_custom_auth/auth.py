"""
Blackbaud API Authentication Flows

This module provides both interactive (webbrowser) and automated (Selenium) 
authentication flows for the Blackbaud API.
"""

import os
import time
import socketserver
import urllib.parse
import webbrowser
from dotenv import load_dotenv
import pyotp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from .client import BlackbaudOAuth, OAuthCallbackHandler

def authenticate_interactive(
    client_id: str,
    client_secret: str,
    subscription_key: str,
    redirect_uri: str = "http://localhost:8080/callback",
) -> BlackbaudOAuth:
    """
    Interactive OAuth authentication flow.
    Opens browser for user authorization and exchanges code for tokens.
    """
    oauth = BlackbaudOAuth(client_id, client_secret, redirect_uri)
    oauth.load_tokens()

    if not oauth.is_token_expired():
        return oauth

    auth_url = oauth.get_authorization_url(subscription_key)
    print("Opening browser for authentication...")
    print(f"If browser doesn't open, visit: {auth_url}")
    webbrowser.open(auth_url)

    authorization_code = None

    def handle_callback(code: str):
        nonlocal authorization_code
        authorization_code = code

    parsed_uri = urllib.parse.urlparse(redirect_uri)
    port = parsed_uri.port or 8080
    handler = lambda *args, **kwargs: OAuthCallbackHandler(
        *args, auth_code_callback=handle_callback, **kwargs
    )

    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Waiting for OAuth callback on port {port}...")
        httpd.timeout = 300
        httpd.handle_request()

    if not authorization_code:
        raise Exception("Authorization code not received. Authentication failed.")

    print("Exchanging authorization code for access token...")
    oauth.exchange_code_for_token(authorization_code, subscription_key)
    oauth.save_tokens()
    print("Authentication successful! Tokens saved.")
    return oauth

def authenticate_automation(
    client_id: str,
    client_secret: str,
    subscription_key: str,
    redirect_uri: str = "http://localhost:8080/callback",
    service_email: str = None,
    service_password: str = None,
    service_totp_secret: str = None
) -> BlackbaudOAuth:
    """
    Automated OAuth authentication flow using Selenium.
    Automatically completes the Google SSO and TOTP login.
    """
    load_dotenv()
    
    # Use provided credentials or fall back to environment variables
    email = service_email or os.environ.get('SERVICE_EMAIL')
    password = service_password or os.environ.get('SERVICE_PW')
    totp_secret = service_totp_secret or os.environ.get('SERVICE_TOTP')
    
    if not all([email, password, totp_secret]):
        raise Exception("Missing automation credentials (SERVICE_EMAIL, SERVICE_PW, SERVICE_TOTP)")
    
    oauth = BlackbaudOAuth(client_id, client_secret, redirect_uri)
    oauth.load_tokens()

    if not oauth.is_token_expired():
        return oauth

    auth_url = oauth.get_authorization_url(subscription_key)
    
    # Initialize WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--incognito")
    # chrome_options.add_argument("--headless") # For headless servers
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(auth_url)
    except Exception as e:
        raise Exception(f"Could not initialize WebDriver: {e}")
    
    authorization_code = None
    
    try:
        driver.implicitly_wait(0)
        wait = WebDriverWait(driver, 30)

        # ------------------- Selenium Steps -------------------
        
        # Step 1: SSO Toggle
        sso_continue_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-bbauto-field='email-continue-button']"))
        )
        sso_continue_button.click()
        
        # Step 2: Email entry
        email_field = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-bbauto-field='sign-in-email']"))
        )
        email_field.send_keys(email)

        # Step 3: Continue
        continue_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-bbauto-field='primary-button']"))
        )
        continue_button.click()

        # Step 4: Google Next (1)
        next_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
        )
        next_button.click()
        
        # Step 5: Password entry
        password_field = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@name='Passwd']"))
        )
        password_field.send_keys(password)
        
        # Step 6: Google Next (2)
        second_next_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
        )
        second_next_button.click()
        
        # Step 7: Handle MFA check
        try:
            time.sleep(5)
            try_another_way_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Try another way']"))
            )
            try_another_way_button.click()
        except:
            pass # Skip if already on MFA screen
        
        # Step 8: Select Google Authenticator
        time.sleep(5)
        google_auth_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//strong[text()='Google Authenticator']"))
        )
        google_auth_button.click()

        # Step 9: TOTP PIN Entry
        time.sleep(5)
        totp_field = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR,"input[name='totpPin']"))
        )
        third_next_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
        )
        
        # Timing guard for TOTP
        TOTP_PERIOD = 30
        MIN_SECONDS_REQUIRED = 5
        seconds_remaining = TOTP_PERIOD - (int(time.time()) % TOTP_PERIOD)
        if seconds_remaining < MIN_SECONDS_REQUIRED:
            time.sleep(seconds_remaining + 1)
            
        totp = pyotp.TOTP(totp_secret)
        current_otp = totp.now()
        totp_field.send_keys(current_otp)
        third_next_button.click()

        # Step 10: Authorize Application
        time.sleep(3)
        authorize_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.sky-btn-primary"))
        )
        
        def handle_callback(code):
            nonlocal authorization_code
            authorization_code = code
            
        parsed_uri = urllib.parse.urlparse(redirect_uri)
        port = parsed_uri.port or 8080
        handler = lambda *args, **kwargs: OAuthCallbackHandler(*args, auth_code_callback=handle_callback, **kwargs)
        
        with socketserver.TCPServer(("", port), handler) as httpd:
            httpd.timeout = 60
            authorize_button.click()
            httpd.handle_request()    

        time.sleep(2)
        print("Automation flow successfully completed!")
    
    except Exception as e:
        print(f"Automation error: {e}")
    finally:
        driver.quit()

    if not authorization_code:
        raise Exception("Authorization code not received during automation flow.")
    
    print("Exchanging authorization code for tokens...")
    oauth.exchange_code_for_token(authorization_code, subscription_key)
    oauth.save_tokens()
    return oauth
