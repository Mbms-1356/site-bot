import json
import re
from difflib import SequenceMatcher
from pathlib import Path

CONTENT_PATH = Path('content/challenges.json')


def _norm(text):
    text = (text or '').lower().replace('ي', 'ی').replace('ك', 'ک')
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\u0600-\u06ff ]+', ' ', text)).strip()


def _questions():
    try:
        return json.loads(CONTENT_PATH.read_text(encoding='utf-8'))
    except Exception:
        return []


def answer_question(text):
    query = _norm(text)
    if len(query) < 3:
        return {'matched': False, 'text': 'لطفاً سؤال کامل‌تری درباره LIT، مدیریت ریسک، سشن‌ها یا آموزش بازار بنویسید.'}
    rows = _questions()
    query_words = set(query.split())
    scored = []
    for q in rows:
        hay = _norm(' '.join([q.get('question', ''), q.get('category', ''), q.get('explanation', ''), q.get('tip', '')]))
        words = set(hay.split())
        overlap = len(query_words & words) / max(1, len(query_words))
        similarity = SequenceMatcher(None, query, _norm(q.get('question', ''))).ratio()
        score = 0.70 * overlap + 0.30 * similarity
        scored.append((score, q))
    scored.sort(key=lambda item: item[0], reverse=True)
    score, q = scored[0]
    if score < 0.22 or not (query_words & set(_norm(q.get('question', '')).split())):
        return {'matched': False, 'text': 'برای این سؤال پاسخ مطمئن و مرتبطی در بانک آموزشی فعلی پیدا نکردم. لطفاً درباره LIT، نقدینگی، POI، Imbalance، مدیریت ریسک، سشن‌ها یا ژورنال سؤال کنید.'}
    return {
        'matched': True,
        'id': q.get('id'),
        'category': q.get('category', 'آموزش'),
        'difficulty': q.get('difficulty', ''),
        'question': q.get('question', ''),
        'answer': q.get('explanation', ''),
        'tip': q.get('tip', ''),
        'url': q.get('related_url', 'https://mbms-1356.github.io/forexin-site-/learn.html'),
    }
