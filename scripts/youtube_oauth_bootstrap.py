from __future__ import annotations
import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

load_dotenv()
client_id = os.getenv("YOUTUBE_CLIENT_ID")
client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

if not client_id or not client_secret:
    raise SystemExit(
        "Put YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in .env first."
    )

config = {
    "installed": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(
    config,
    scopes=["https://www.googleapis.com/auth/youtube.upload"],
)
creds = flow.run_local_server(
    port=0, access_type="offline", prompt="consent"
)

print("\nSAVE THIS AS YOUTUBE_REFRESH_TOKEN:\n")
print(creds.refresh_token)
