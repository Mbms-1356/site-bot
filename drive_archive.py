"""Optional Google Drive archive adapter for GitHub Actions.

The adapter is deliberately no-op unless both credentials and a Drive folder ID
are configured. GitHub remains the source of truth until Drive is enabled.
"""
import io
import json
import os
from typing import Any, Dict, Optional

ROOT_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_ROOT_FOLDER_ID', '').strip()
_CREDENTIALS = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_JSON', '').strip()
_service = None
_folder_cache = {}


def enabled() -> bool:
    return bool(ROOT_FOLDER_ID and _CREDENTIALS)


def status() -> Dict[str, Any]:
    return {
        'enabled': enabled(),
        'root_folder_configured': bool(ROOT_FOLDER_ID),
        'credentials_configured': bool(_CREDENTIALS),
        'mode': 'google-drive-plus-github' if enabled() else 'github-only-fallback',
    }


def _get_service():
    global _service
    if _service is not None:
        return _service
    if not enabled():
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        info = json.loads(_CREDENTIALS)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=['https://www.googleapis.com/auth/drive'])
        _service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        return _service
    except Exception as exc:
        print('drive-archive-init-failed:', str(exc)[:180])
        return None


def _parent_for(path: str) -> str:
    """Resolve a relative archive path under the configured Drive root."""
    service = _get_service()
    if not service:
        return ROOT_FOLDER_ID
    parent = ROOT_FOLDER_ID
    parts = [part for part in path.split('/')[:-1] if part]
    for name in parts:
        cache_key = (parent, name)
        if cache_key in _folder_cache:
            parent = _folder_cache[cache_key]
            continue
        query = (
            "name = '" + name.replace("'", "\\'") + "' and "
            "mimeType = 'application/vnd.google-apps.folder' and "
            "trashed = false and '" + parent + "' in parents"
        )
        found = service.files().list(q=query, pageSize=1, fields='files(id)').execute().get('files', [])
        if found:
            parent = found[0]['id']
        else:
            created = service.files().create(
                body={'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent]},
                fields='id').execute()
            parent = created['id']
        _folder_cache[cache_key] = parent
    return parent


def upload_bytes(path: str, data: bytes, mime_type: str = 'application/octet-stream') -> Optional[Dict[str, Any]]:
    service = _get_service()
    if not service:
        return None
    try:
        from googleapiclient.http import MediaIoBaseUpload
        name = path.rsplit('/', 1)[-1]
        media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime_type, resumable=False)
        result = service.files().create(
            body={'name': name, 'parents': [_parent_for(path)]},
            media_body=media, fields='id,name,mimeType,webViewLink').execute()
        return result
    except Exception as exc:
        print('drive-archive-upload-failed:', str(exc)[:180])
        return None


def upload_json(path: str, value: Any) -> Optional[Dict[str, Any]]:
    data = json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')
    return upload_bytes(path, data, 'application/json')
