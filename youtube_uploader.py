import os
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET_FILE = Path("credentials/client_secret.json")
TOKEN_FILE = Path("credentials/token.json")

# Sleep viewers search in the evening/night — publish then.
SLOT_TIMES_UTC = {
    "night": "01:00",      # 8pm EST = 1am UTC (next day)
    "evening": "23:00",    # 6pm EST = 11pm UTC
    "afternoon": "19:00",  # 2pm EST = 7pm UTC
}


def authenticate() -> object:
    """Authenticate with YouTube API using OAuth2. Returns youtube service."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRET_FILE.exists():
                raise FileNotFoundError(
                    f"Missing {CLIENT_SECRET_FILE}. "
                    "Download OAuth credentials from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def _get_publish_time(slot: str) -> str:
    """Return RFC 3339 publish timestamp for the given slot (today or tomorrow for evening)."""
    now = datetime.now(timezone.utc)
    time_str = SLOT_TIMES_UTC.get(slot, "12:00")
    hour, minute = map(int, time_str.split(":"))

    publish_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If past time today, schedule for tomorrow
    if publish_dt <= now:
        from datetime import timedelta
        publish_dt += timedelta(days=1)

    return publish_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def upload_video(youtube, video_path: str, seo: dict, privacy: str = "public",
                 slot: str = "morning") -> str:
    """Upload video to YouTube. Returns the video ID."""
    publish_at = _get_publish_time(slot) if privacy == "public" else None

    snippet = {
        "title": seo["title"],
        "description": seo["description"],
        "tags": seo["tags"],
        "categoryId": seo.get("category_id", "10"),
        "defaultLanguage": "en",
        "defaultAudioLanguage": "en",
    }

    status = {
        "privacyStatus": "private" if publish_at else privacy,
        "selfDeclaredMadeForKids": False,
    }

    if publish_at:
        status["publishAt"] = publish_at

    body = {"snippet": snippet, "status": status}

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 5,  # 5MB chunks
    )

    print(f"  Uploading: {seo['title'][:60]}...")
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status_obj, response = request.next_chunk()
        if status_obj:
            pct = int(status_obj.progress() * 100)
            print(f"  Upload progress: {pct}%")

    video_id = response.get("id", "unknown")
    scheduled = publish_at or "immediately"
    print(f"  Uploaded! Video ID: {video_id} | Scheduled: {scheduled}")
    return video_id


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth", action="store_true", help="Run OAuth authentication flow")
    args = parser.parse_args()

    if args.auth:
        print("Running YouTube OAuth authentication...")
        youtube = authenticate()
        print(f"Authentication successful! Token saved to {TOKEN_FILE}")
