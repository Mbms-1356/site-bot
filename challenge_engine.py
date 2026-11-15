import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

REPO = os.environ.get('GH_REPO', 'Mbms-1356/site-bot')
GH_TOKEN = os.environ.get('GH_TOKEN', '').strip()
NAMESPACE = os.environ.get('CHALLENGE_NAMESPACE', 'default')
STATE_PATH = Path(os.environ.get('CHALLENGE_STATE_FILE', f'challenge_state_{NAMESPACE}.json'))
CONTENT_PATH = Path('content/challenges.json')
TEHRAN = timezone(timedelta(hours=3, minutes=30))


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def _save_to_github():
    if not GH_TOKEN:
        return
    url = f'https://api.github.com/repos/{REPO}/contents/{STATE_PATH.as_posix()}'
    headers = {'Authorization': f'Bearer {GH_TOKEN}', 'Accept': 'application/vnd.github+json', 'User-Agent': 'forexin-challenge-engine'}
    old = requests.get(url, headers=headers, timeout=12)
    payload = {'message': f'Update {STATE_PATH.name}', 'content': base64.b64encode(STATE_PATH.read_bytes()).decode()}
    if old.ok:
        payload['sha'] = old.json().get('sha')
    requests.put(url, headers=headers, json=payload, timeout=15).raise_for_status()


def _state():
    return _load(STATE_PATH, {'users': {}})


def _persist(state):
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    try:
        _save_to_github()
    except Exception:
        pass


def _today():
    return datetime.now(TEHRAN).date().isoformat()


def _user(state, uid):
    return state.setdefault('users', {}).setdefault(str(uid), {'points': 0, 'streak': 0, 'last_date': '', 'history': {}, 'badges': []})


def _pick(uid, state, questions):
    today = _today()
    user = _user(state, uid)
    if today in user['history']:
        qid = user['history'][today]['id']
        return next((q for q in questions if q['id'] == qid), questions[0])
    used = {item['id'] for item in user['history'].values()}
    available = [q for q in questions if q['id'] not in used] or questions
    seed = hashlib.sha256(f'{uid}:{today}'.encode()).hexdigest()
    return available[int(seed[:8], 16) % len(available)]


def get_daily(uid):
    state = _state()
    questions = _load(CONTENT_PATH, [])
    if not questions:
        return None
    q = _pick(uid, state, questions)
    _persist(state)
    return q


def answer(uid, qid, option):
    state = _state()
    questions = _load(CONTENT_PATH, [])
    q = next((x for x in questions if x['id'] == qid), None)
    if not q:
        return None
    today = _today()
    user = _user(state, uid)
    existing = user['history'].get(today)
    if existing and existing.get('answered'):
        return {'already': True, 'question': q, 'correct': existing.get('correct', False), 'user': user}
    correct = int(option) == int(q['correct'])
    yesterday = (datetime.now(TEHRAN).date() - timedelta(days=1)).isoformat()
    user['streak'] = user.get('streak', 0) + 1 if user.get('last_date') == yesterday else 1
    if correct:
        user['points'] = user.get('points', 0) + 10
    user['last_date'] = today
    user['history'][today] = {'id': qid, 'answer': int(option), 'correct': correct, 'answered': True}
    badges = set(user.get('badges', []))
    if user['streak'] >= 3: badges.add('📚 یادگیرنده فعال')
    if user['streak'] >= 7: badges.add('🧠 تحلیل‌گر منظم')
    if user['points'] >= 50: badges.add('🛡 متخصص مدیریت ریسک')
    user['badges'] = sorted(badges)
    _persist(state)
    return {'already': False, 'question': q, 'correct': correct, 'user': user}


def profile(uid):
    state = _state()
    return _user(state, uid)


def report(limit=10):
    state = _state()
    questions = {q['id']: q for q in _load(CONTENT_PATH, [])}
    users = state.get('users', {})
    rows = []
    category = {}
    total_answers = 0
    total_correct = 0
    for uid, user in users.items():
        correct = sum(1 for item in user.get('history', {}).values() if item.get('answered') and item.get('correct'))
        answered = sum(1 for item in user.get('history', {}).values() if item.get('answered'))
        rows.append({'uid': uid, 'points': user.get('points', 0), 'streak': user.get('streak', 0), 'answered': answered, 'correct': correct})
        total_answers += answered
        total_correct += correct
        for item in user.get('history', {}).values():
            q = questions.get(item.get('id'))
            if not q or not item.get('answered'):
                continue
            bucket = category.setdefault(q['category'], {'answers': 0, 'correct': 0})
            bucket['answers'] += 1
            bucket['correct'] += int(bool(item.get('correct')))
    rows.sort(key=lambda x: (x['points'], x['streak'], x['correct']), reverse=True)
    for name, data in category.items():
        data['accuracy'] = round(data['correct'] / data['answers'] * 100) if data['answers'] else 0
    weakest = sorted(category.items(), key=lambda pair: (pair[1]['accuracy'], -pair[1]['answers']))
    return {'users': len(users), 'answers': total_answers, 'correct': total_correct, 'accuracy': round(total_correct / total_answers * 100) if total_answers else 0, 'leaderboard': rows[:limit], 'categories': category, 'weakest': weakest[:3]}
