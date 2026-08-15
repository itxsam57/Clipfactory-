from __future__ import annotations
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from ..config import env

TOKEN_URI = "https://oauth2.googleapis.com/token"

def upload(video_path: Path, plan: dict) -> dict:
    creds = Credentials(
        token=None,
        refresh_token=env("YOUTUBE_REFRESH_TOKEN", required=True),
        token_uri=TOKEN_URI,
        client_id=env("YOUTUBE_CLIENT_ID", required=True),
        client_secret=env("YOUTUBE_CLIENT_SECRET", required=True),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    description = plan["description"].strip()
    attribution = f"\n\nSource evidence: {plan['source_creator']} — {plan['source_url']}"
    if attribution not in description:
        description += attribution

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": plan["title"][:100],
                "description": description[:5000],
                "tags": [h.lstrip("#") for h in plan.get("hashtags", [])][:15],
                "categoryId": "27",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
    )
    result = request.execute()
    return {
        "platform": "youtube",
        "id": result["id"],
        "url": f"https://youtube.com/shorts/{result['id']}",
    }
