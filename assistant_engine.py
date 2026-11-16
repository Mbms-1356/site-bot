import json
import base64
import os
import re
import requests
import time
import hashlib
from difflib import SequenceMatcher
from pathlib import Path

CONTENT_PATH = Path('content/challenges.json')
KNOWLEDGE_PATH = os.environ.get('KNOWLEDGE_PATH', 'content-control/knowledge/index.json')
KNOWLEDGE_REPO = os.environ.get('KNOWLEDGE_REPO', 'Mbms-1356/forexin-site-')
GH_TOKEN = os.environ.get('GH_TOKEN', os.environ.get('GH_PAT', '')).strip()
_KNOWLEDGE_CACHE = {'at': 0.0, 'rows': []}
UNANSWERED_REPO = os.environ.get('KNOWLEDGE_REPO', 'Mbms-1356/forexin-site-')
UNANSWERED_PATH = 'content-control/unanswered-questions.json'
ACTIVE_FAQ_PATH = 'content-control/active-faq.json'


def _norm(text):
    text = (text or '').lower().replace('ي', 'ی').replace('ك', 'ک')
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\u0600-\u06ff ]+', ' ', text)).strip()


def _questions():
    try:
        return json.loads(CONTENT_PATH.read_text(encoding='utf-8'))
    except Exception:
        return []


def _knowledge():
    if time.time() - _KNOWLEDGE_CACHE['at'] < 300:
        return _KNOWLEDGE_CACHE['rows']
    local = Path(KNOWLEDGE_PATH)
    if local.exists():
        try:
            rows = json.loads(local.read_text(encoding='utf-8'))
            _KNOWLEDGE_CACHE.update(at=time.time(), rows=rows)
            return rows
        except Exception:
            pass
    if not GH_TOKEN:
        return []
    try:
        url = f'https://api.github.com/repos/{KNOWLEDGE_REPO}/contents/{KNOWLEDGE_PATH}'
        response = requests.get(url, headers={'Authorization': f'Bearer {GH_TOKEN}', 'Accept': 'application/vnd.github+json'}, timeout=15)
        if not response.ok:
            return []
        rows = json.loads(base64.b64decode(response.json().get('content', '')).decode('utf-8'))
        _KNOWLEDGE_CACHE.update(at=time.time(), rows=rows)
        return rows
    except Exception:
        return []


def _active_faq():
    """Load only reviewed FAQ entries that contain an actual approved answer."""
    local = Path(ACTIVE_FAQ_PATH)
    try:
        if local.exists():
            rows = json.loads(local.read_text(encoding='utf-8'))
        elif not GH_TOKEN:
            return []
        else:
            url = f'https://api.github.com/repos/{KNOWLEDGE_REPO}/contents/{ACTIVE_FAQ_PATH}'
            response = requests.get(url, headers={'Authorization': f'Bearer {GH_TOKEN}', 'Accept': 'application/vnd.github+json'}, timeout=15)
            if not response.ok:
                return []
            rows = json.loads(base64.b64decode(response.json().get('content', '')).decode('utf-8'))
        return [x for x in rows if x.get('status') == 'active' and x.get('answer')]
    except Exception:
        return []


def answer_question(text):
    query = _norm(text)
    if len(query) < 3:
        return {'matched': False, 'text': 'لطفاً سؤال کامل‌تری درباره LIT، مدیریت ریسک، سشن‌ها یا آموزش بازار بنویسید.'}
    rows = _questions()
    for item in _active_faq():
        rows.append({'id': item.get('id'), '_archive': True, 'category': 'FAQ تأییدشده',
                     'question': item.get('question', ''), 'explanation': item.get('answer', ''),
                     'tip': 'پاسخ از FAQ تأییدشده استخراج شده است.', 'related_url': item.get('url', '')})
    for item in _knowledge():
        if not item.get('safe_for_assistant'):
            continue
        rows.append({'id': item.get('id'), '_archive': True, 'category': item.get('category', 'آموزش آرشیو'),
                     'question': item.get('title', ''), 'explanation': item.get('text', ''),
                     'keywords': ' '.join(map(str, item.get('keywords', []))),
                     'tip': 'این پاسخ از محتوای آموزشی تأییدشده آرشیو استخراج شده است.',
                     'related_url': item.get('source_url', '') or 'https://mbms-1356.github.io/forexin-site-/learn.html'})
    query_words = set(query.split())
    scored = []
    for q in rows:
        hay = _norm(' '.join([q.get('question', ''), q.get('category', ''), q.get('keywords', ''), q.get('explanation', ''), q.get('tip', '')]))
        words = set(hay.split())
        overlap = len(query_words & words) / max(1, len(query_words))
        similarity = SequenceMatcher(None, query, _norm(q.get('question', ''))).ratio()
        score = 0.70 * overlap + 0.30 * similarity
        scored.append((score, q))
    scored.sort(key=lambda item: item[0], reverse=True)
    score, q = scored[0]
    related = []
    for related_score, related_q in scored[:4]:
        if related_q is q or related_score < 0.16:
            continue
        related.append({'title': related_q.get('question', ''), 'url': related_q.get('related_url', '')})
    if score < 0.22 or not (query_words & set(_norm(' '.join([q.get('question', ''), q.get('keywords', ''), q.get('explanation', '')])).split())):
        return {'matched': False, 'text': 'برای این سؤال پاسخ مطمئن و مرتبطی در بانک آموزشی فعلی پیدا نکردم. لطفاً درباره LIT، نقدینگی، POI، Imbalance، مدیریت ریسک، سشن‌ها یا ژورنال سؤال کنید.', 'related': related}
    return {
        'matched': True,
        'id': q.get('id'),
        'category': q.get('category', 'آموزش'),
        'difficulty': q.get('difficulty', ''),
        'question': q.get('question', ''),
        'answer': q.get('explanation', ''),
        'tip': q.get('tip', ''),
        'url': q.get('related_url', 'https://mbms-1356.github.io/forexin-site-/learn.html'),
        'source': 'آرشیو آموزشی تأییدشده' if q.get('_archive') else 'بانک آموزشی',
        'related': related,
    }


def record_unanswered(text):
    """Store a bounded, deduplicated queue for future FAQ/challenge curation."""
    question = ' '.join((text or '').split())[:500]
    if len(question) < 3 or not GH_TOKEN:
        return False
    try:
        url = f'https://api.github.com/repos/{UNANSWERED_REPO}/contents/{UNANSWERED_PATH}'
        headers = {'Authorization': f'Bearer {GH_TOKEN}', 'Accept': 'application/vnd.github+json', 'User-Agent': 'forexin-assistant'}
        response = requests.get(url, headers=headers, timeout=15)
        rows, sha = [], None
        if response.ok:
            body = response.json(); sha = body.get('sha')
            rows = json.loads(base64.b64decode(body.get('content', '')).decode('utf-8'))
        digest = hashlib.sha256(_norm(question).encode()).hexdigest()[:16]
        for item in rows:
            if item.get('id') == digest:
                item['count'] = int(item.get('count', 1)) + 1
                item['last_seen'] = int(time.time())
                payload = {'message': 'Update unanswered assistant question', 'content': base64.b64encode(json.dumps(rows[:300], ensure_ascii=False, indent=2).encode()).decode()}
                if sha: payload['sha'] = sha
                return requests.put(url, headers={**headers, 'Content-Type': 'application/json'}, json=payload, timeout=20).ok
        rows.insert(0, {'id': digest, 'question': question, 'count': 1, 'last_seen': int(time.time()), 'status': 'needs_review'})
        payload = {'message': 'Log unanswered assistant question', 'content': base64.b64encode(json.dumps(rows[:300], ensure_ascii=False, indent=2).encode()).decode()}
        if sha: payload['sha'] = sha
        return requests.put(url, headers={**headers, 'Content-Type': 'application/json'}, json=payload, timeout=20).ok
    except Exception:
        return False
