"""Upload one video to YouTube using a stored OAuth refresh token."""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def upload(path, title, description, tags, lang, privacy='public'):
    creds = Credentials(
        None,
        refresh_token=os.environ['YT_REFRESH_TOKEN'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ['YT_CLIENT_ID'],
        client_secret=os.environ['YT_CLIENT_SECRET'],
        scopes=['https://www.googleapis.com/auth/youtube.upload'],
    )
    yt = build('youtube', 'v3', credentials=creds, cache_discovery=False)

    kept, total = [], 0
    for tag in tags:
        tag = str(tag).replace('<', '').replace('>', '').strip()
        if tag and total + len(tag) + 1 <= 450:
            kept.append(tag)
            total += len(tag) + 1

    body = {
        'snippet': {
            'title': title[:100],
            'description': description[:4900],
            'tags': kept,
            'categoryId': '24',
            'defaultLanguage': lang,
            'defaultAudioLanguage': lang,
        },
        'status': {'privacyStatus': privacy, 'selfDeclaredMadeForKids': False},
    }
    req = yt.videos().insert(
        part='snippet,status',
        body=body,
        media_body=MediaFileUpload(path, mimetype='video/mp4', resumable=True, chunksize=-1),
    )
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp['id']
