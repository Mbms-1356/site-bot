"""GitHub App authentication with safe PAT fallback for the content agent."""
import base64
import json
import os
import time
import urllib.request

_TOKEN_CACHE = {'value': '', 'expires_at': 0}


def _settings():
    app_id = os.environ.get('GITHUB_APP_ID', '').strip()
    installation_id = os.environ.get('GITHUB_APP_INSTALLATION_ID', '').strip()
    key = os.environ.get('GITHUB_APP_PRIVATE_KEY', '').strip()
    key_b64 = os.environ.get('GITHUB_APP_PRIVATE_KEY_B64', '').strip()
    if not key and key_b64:
        try:
            key = base64.b64decode(key_b64).decode('utf-8')
        except Exception:
            key = ''
    return app_id, installation_id, key


def readiness():
    app_id, installation_id, key = _settings()
    checks = {'GITHUB_APP_ID': bool(app_id),
              'GITHUB_APP_PRIVATE_KEY': bool(key),
              'GITHUB_APP_INSTALLATION_ID': bool(installation_id)}
    ready = all(checks.values())
    return {'ready': ready, 'checks': checks,
            'mode': 'github-app-ready' if ready else 'pat-current',
            'note': 'تا زمان تکمیل هر سه Secret، توکن فعلی GH_PAT دست‌نخورده باقی می‌ماند.'}


def _b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')


def _app_token():
    """Return a one-hour installation token, or an empty string on any failure."""
    app_id, installation_id, private_key = _settings()
    if not (app_id and installation_id and private_key):
        return ''
    try:
        import jwt
        now = int(time.time())
        assertion = jwt.encode({'iat': now - 30, 'exp': now + 540, 'iss': app_id}, private_key, algorithm='RS256')
        if isinstance(assertion, bytes):
            assertion = assertion.decode('ascii')
        request = urllib.request.Request(
            f'https://api.github.com/app/installations/{installation_id}/access_tokens',
            data=b'{}', method='POST', headers={
                'Authorization': 'Bearer ' + assertion,
                'Accept': 'application/vnd.github+json',
                'X-GitHub-Api-Version': '2026-03-10',
                'Content-Type': 'application/json',
                'User-Agent': 'ForexinContentAgent'})
        payload = json.loads(urllib.request.urlopen(request, timeout=20).read())
        token = str(payload.get('token', '')).strip()
        if token:
            _TOKEN_CACHE.update(value=token, expires_at=now + 3000)
        return token
    except Exception:
        return ''


def github_token():
    """Prefer GitHub App; preserve current PAT behavior until App is configured."""
    now = int(time.time())
    if _TOKEN_CACHE['value'] and _TOKEN_CACHE['expires_at'] > now + 60:
        return _TOKEN_CACHE['value']
    return _app_token() or os.environ.get('GH_PAT', '').strip()
