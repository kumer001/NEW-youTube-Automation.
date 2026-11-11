#!/usr/bin/env python3
"""One-time helper: get a YouTube refresh token.

pip install google-auth-oauthlib
python scripts/get_refresh_token.py client_secret.json

Open the printed URL in a browser on the same device, approve, and the token is printed.
"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file(
    sys.argv[1], scopes=['https://www.googleapis.com/auth/youtube.upload']
)
creds = flow.run_local_server(port=8080, open_browser=False, access_type='offline', prompt='consent')
print('\nYT_CLIENT_ID     =', creds.client_id)
print('YT_CLIENT_SECRET =', creds.client_secret)
print('YT_REFRESH_TOKEN =', creds.refresh_token)
