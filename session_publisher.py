import base64
import json
import os
from datetime import datetime, timedelta, timezone, time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TEHRAN = ZoneInfo('Asia/Tehran')
CHANNEL = '@forexin_turkaslanifree'
REPO = os.environ.get('GH_REPO', 'Mbms-1356/site-bot')
GH_PAT = os.environ.get('GH_PAT', '').strip()
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
STATE_PATH = Path('session_state.json')
CONTENT_PATH = Path('content/session_messages.json')

EVENTS = [
    ('frankfurt_open', '🇩🇪 بازشدن فرانکفورت', 'Europe/Berlin', 8, 0),
    ('london_open', '🇬🇧 بازشدن لندن', 'Europe/London', 8, 0),
    ('newyork_open', '🇺🇸 بازشدن نیویورک و شروع هم‌پوشانی لندن–نیویورک', 'America/New_York', 8, 0),
    ('london_close', '🇬🇧 بسته‌شدن لندن', 'Europe/London', 17, 0),
]


def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def event_instances(now):
    for delta in (-1, 0, 1):
        date = (now + timedelta(days=delta)).date()
        for key, label, zone, hour, minute in EVENTS:
            local = datetime.combine(date, time(hour, minute), tzinfo=ZoneInfo(zone))
            yield key, label, local.astimezone(TEHRAN)


def send_message(text):
    response = requests.post(
        f'https://api.telegram.org/bot{TOKEN}/sendMessage',
        json={
            'chat_id': CHANNEL,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get('ok'):
        raise RuntimeError('Telegram rejected the message')


def save_state(state):
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not GH_PAT:
        raise RuntimeError('GH_PAT is required to persist session state')
    url = f'https://api.github.com/repos/{REPO}/contents/session_state.json'
    headers = {
        'Authorization': f'Bearer {GH_PAT}',
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'forexin-session-publisher',
    }
    old = requests.get(url, headers=headers, timeout=15)
    payload = {
        'message': 'Record published market session event',
        'content': base64.b64encode(STATE_PATH.read_bytes()).decode(),
    }
    if old.ok:
        payload['sha'] = old.json().get('sha')
    response = requests.put(url, headers=headers, json=payload, timeout=20)
    response.raise_for_status()


def main():
    if not TOKEN:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is missing')
    content = load_json(CONTENT_PATH, {})
    state = load_json(STATE_PATH, {})
    now = datetime.now(TEHRAN)
    published = []
    # GitHub schedules can be delayed; allow a short delivery window and deduplicate by local event date.
    for key, label, event_time in event_instances(now):
        age = (now - event_time).total_seconds()
        event_id = f'{key}:{event_time.date().isoformat()}'
        if age < 0 or age > 20 * 60 or event_id in state:
            continue
        item = content.get(key)
        if not item:
            continue
        text = item['body'] + f'\n\n🕒 زمان رویداد: {event_time.strftime("%Y-%m-%d %H:%M")} به وقت ایران'
        send_message(text)
        state[event_id] = {'published_at': now.isoformat(), 'title': item.get('title', label)}
        published.append(event_id)
    if published:
        save_state(state)
        print('published:', ', '.join(published))
    else:
        print('no session event due')


if __name__ == '__main__':
    main()
