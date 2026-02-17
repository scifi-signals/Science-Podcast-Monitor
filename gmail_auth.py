#!/usr/bin/env python3
"""
Gmail OAuth2 Setup Script
Run this ONCE locally to authorize the Science Trend Monitor to send emails.

Usage:
    1. Place your credentials.json (from Google Cloud Console) in this directory
    2. Run: python gmail_auth.py
    3. A browser window will open - sign in and click "Allow"
    4. token.json will be created - upload this to the server

To get credentials.json:
    1. Go to https://console.cloud.google.com
    2. Create a project (or select existing)
    3. Enable the Gmail API: APIs & Services > Enable APIs > search "Gmail API"
    4. Create credentials: APIs & Services > Credentials > Create Credentials > OAuth client ID
       - Application type: Desktop app
       - Name: Science Trend Monitor
    5. Download the JSON file and rename it to credentials.json
"""

import os
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
except ImportError:
    print("Missing dependencies. Install them with:")
    print("  pip install google-auth-oauthlib google-auth google-api-python-client")
    sys.exit(1)

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(__file__), 'token.json')


def setup():
    """Run the OAuth2 flow and save the token."""

    # Check if token already exists and is valid
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if creds and creds.valid:
            print(f"[OK] Token already exists and is valid: {TOKEN_FILE}")
            print(f"     Account: {creds.client_id[:20]}...")
            return
        if creds and creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            creds.refresh(Request())
            with open(TOKEN_FILE, 'w') as f:
                f.write(creds.to_json())
            print(f"[OK] Token refreshed: {TOKEN_FILE}")
            return

    # Need to run the full auth flow
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"[ERROR] credentials.json not found at: {CREDENTIALS_FILE}")
        print()
        print("To get this file:")
        print("  1. Go to https://console.cloud.google.com")
        print("  2. Create a project (or select existing)")
        print("  3. Enable the Gmail API:")
        print("     APIs & Services > Enable APIs > search 'Gmail API'")
        print("  4. Create credentials:")
        print("     APIs & Services > Credentials > Create Credentials > OAuth client ID")
        print("     - Application type: Desktop app")
        print("     - Name: Science Trend Monitor")
        print("  5. Download the JSON and save as 'credentials.json' in this folder")
        sys.exit(1)

    print("Starting OAuth2 authorization flow...")
    print("A browser window will open. Sign in with: nasem.sciencetrends@gmail.com")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    with open(TOKEN_FILE, 'w') as f:
        f.write(creds.to_json())

    print()
    print(f"[OK] Authorization successful! Token saved to: {TOKEN_FILE}")
    print()
    print("Next steps:")
    print("  1. Upload token.json and credentials.json to the server:")
    print("     scp token.json credentials.json science-intel:/root/science-trend-monitor/")
    print("  2. Test email delivery:")
    print("     python main.py --test-email")


if __name__ == '__main__':
    setup()
