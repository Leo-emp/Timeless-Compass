import os
import json
import time
import config

# ============================================================
# TIMELESS COMPASS — YOUTUBE UPLOADER
# ============================================================
# Uploads videos to YouTube using the Data API v3 with OAuth 2.0.
#
# Setup required:
#   1. Create Google Cloud project
#   2. Enable YouTube Data API v3
#   3. Create OAuth 2.0 credentials (Desktop app)
#   4. Download client_secret.json to project root
#   5. Run auth flow via dashboard settings page
#
# Environment variables:
#   YOUTUBE_CLIENT_ID     — OAuth client ID
#   YOUTUBE_CLIENT_SECRET — OAuth client secret
# ============================================================

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "youtube_token.json")


def get_auth_url():
    """
    # Generates the YouTube OAuth authorization URL
    # User visits this URL to grant upload permissions
    """
    client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
    if not client_id:
        return None

    # --- OAuth scopes needed for video upload ---
    scopes = "https://www.googleapis.com/auth/youtube.upload"
    redirect_uri = "http://localhost:8000/api/youtube/callback"

    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scopes}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return url


def exchange_code(code):
    """
    # Exchanges the OAuth authorization code for access + refresh tokens
    """
    import requests

    client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
    client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
    redirect_uri = "http://localhost:8000/api/youtube/callback"

    response = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })

    if response.status_code != 200:
        print(f"[YOUTUBE] Token exchange failed: {response.text}")
        return False

    token_data = response.json()
    token_data["obtained_at"] = time.time()

    # --- Save tokens to file ---
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print("[YOUTUBE] OAuth tokens saved successfully")
    return True


def _get_access_token():
    """
    # Returns a valid access token, refreshing if expired
    """
    import requests

    if not os.path.exists(TOKEN_FILE):
        return None

    with open(TOKEN_FILE, "r") as f:
        token_data = json.load(f)

    # --- Check if token is expired (1 hour lifetime) ---
    obtained_at = token_data.get("obtained_at", 0)
    expires_in = token_data.get("expires_in", 3600)

    if time.time() - obtained_at > expires_in - 300:
        # --- Refresh the token ---
        client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
        refresh_token = token_data.get("refresh_token")

        if not refresh_token:
            print("[YOUTUBE] No refresh token — re-authorize")
            return None

        response = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })

        if response.status_code != 200:
            print(f"[YOUTUBE] Token refresh failed: {response.text}")
            return None

        new_data = response.json()
        token_data["access_token"] = new_data["access_token"]
        token_data["expires_in"] = new_data.get("expires_in", 3600)
        token_data["obtained_at"] = time.time()

        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f, indent=2)

    return token_data.get("access_token")


def is_authenticated():
    """
    # Checks if YouTube OAuth is set up and tokens exist
    """
    return os.path.exists(TOKEN_FILE)


def upload_video(video_path, title, description, tags, category_id="27"):
    """
    # Uploads a video to YouTube
    #
    # Args:
    #   video_path: path to the MP4 file
    #   title: video title
    #   description: video description
    #   tags: list of tag strings
    #   category_id: YouTube category (27 = Education)
    #
    # Returns:
    #   YouTube video URL on success, None on failure
    """
    import requests

    access_token = _get_access_token()
    if not access_token:
        print("[YOUTUBE] Not authenticated — run OAuth flow first")
        return None

    if not os.path.exists(video_path):
        print(f"[YOUTUBE] Video file not found: {video_path}")
        return None

    file_size = os.path.getsize(video_path)
    print(f"[YOUTUBE] Uploading: {title} ({file_size / 1024 / 1024:.1f} MB)")

    # --- Step 1: Initialize resumable upload ---
    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags[:30],
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
        },
    }

    init_response = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(file_size),
        },
        json=metadata,
    )

    if init_response.status_code != 200:
        print(f"[YOUTUBE] Upload init failed: {init_response.status_code}")
        print(f"[YOUTUBE] {init_response.text[:300]}")
        return None

    # --- Get the resumable upload URL ---
    upload_url = init_response.headers.get("Location")
    if not upload_url:
        print("[YOUTUBE] No upload URL in response")
        return None

    # --- Step 2: Upload the video file ---
    with open(video_path, "rb") as f:
        upload_response = requests.put(
            upload_url,
            headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(file_size),
            },
            data=f,
        )

    if upload_response.status_code not in (200, 201):
        print(f"[YOUTUBE] Upload failed: {upload_response.status_code}")
        print(f"[YOUTUBE] {upload_response.text[:300]}")
        return None

    # --- Extract video ID ---
    result = upload_response.json()
    video_id = result.get("id", "")
    youtube_url = f"https://youtube.com/watch?v={video_id}"

    print(f"[YOUTUBE] Upload complete: {youtube_url}")
    print(f"[YOUTUBE] Status: private (change to public when ready)")

    return youtube_url
