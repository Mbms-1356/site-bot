"""Small, GitHub-backed content control center used by the content agent."""
import json
import time
from typing import Any, Dict, List

INDEX_PATH = 'content-control/index.json'
DRAFT_DIR = 'content-control/drafts/'
ARCHIVE_PATH = 'content-control/archive/index.json'
KNOWLEDGE_PATH = 'content-control/knowledge/index.json'


def draft_path(package_id: str) -> str:
    return DRAFT_DIR + package_id + '.json'


def load_index(fetch_json) -> List[Dict[str, Any]]:
    raw = fetch_json(INDEX_PATH)
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []


def save_package(package: Dict[str, Any], fetch_json, put_json) -> None:
    package_id = package['id']
    package['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    put_json(draft_path(package_id), package, 'Save content package draft')
    index = load_index(fetch_json)
    index = [item for item in index if item.get('id') != package_id]
    index.insert(0, {'id': package_id, 'slug': package.get('slug'), 'title': package.get('article', {}).get('title'),
                     'status': package.get('status', 'draft'), 'score': package.get('quality', {}).get('score', 0),
                     'updated_at': package['updated_at']})
    put_json(INDEX_PATH, index[:300], 'Update content control index')
    archive = _load_list(fetch_json, ARCHIVE_PATH)
    archive = [item for item in archive if item.get('id') != package_id]
    archive.insert(0, {
        'id': package_id, 'slug': package.get('slug'),
        'title': package.get('article', {}).get('title', ''),
        'status': package.get('status', 'draft'),
        'category': package.get('article', {}).get('category', 'آموزش'),
        'keywords': package.get('article', {}).get('keywords', []),
        'source': package.get('source', {}),
        'visuals': package.get('visuals', {}),
        'platforms': package.get('platforms', {}),
        'article_path': draft_path(package_id),
        'updated_at': package['updated_at'],
    })
    put_json(ARCHIVE_PATH, archive[:500], 'Update content asset archive')
    knowledge = _load_list(fetch_json, KNOWLEDGE_PATH)
    knowledge = [item for item in knowledge if item.get('id') != package_id]
    article = package.get('article', {})
    knowledge.insert(0, {
        'id': package_id, 'title': article.get('title', ''),
        'category': article.get('category', 'آموزش'),
        'keywords': article.get('keywords', []),
        'text': ('\n'.join(str(x) for x in article.get('body', [])) + '\n' + str(article.get('excerpt', '')))[:20000],
        'source_url': package.get('source', {}).get('url', ''),
        'status': package.get('status', 'draft'),
        'safe_for_assistant': package.get('status') in ('approved', 'published'),
        'updated_at': package['updated_at'],
    })
    put_json(KNOWLEDGE_PATH, knowledge[:500], 'Update assistant knowledge index')


def _load_list(fetch_json, path: str) -> List[Dict[str, Any]]:
    raw = fetch_json(path)
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except Exception:
        return []


def set_status(package: Dict[str, Any], status: str, reviewer: str = '') -> Dict[str, Any]:
    if status not in ('draft', 'approved', 'rejected', 'published'):
        raise ValueError('invalid content status')
    package['status'] = status
    package.setdefault('publishing', {})['approved_by'] = reviewer or None
    package['publishing']['approved_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()) if reviewer else None
    return package


def summary(index: List[Dict[str, Any]]) -> str:
    counts = {s: sum(1 for x in index if x.get('status') == s) for s in ('draft', 'approved', 'rejected', 'published')}
    return ('📊 مرکز کنترل محتوا\n\n'
            f"📝 پیش‌نویس: {counts['draft']}\n✅ تأییدشده: {counts['approved']}\n"
            f"🚫 ردشده: {counts['rejected']}\n🚀 منتشرشده: {counts['published']}\n\n"
            'انتشار شبکه‌های اجتماعی فعلاً فقط پس از تأیید مدیر انجام می‌شود.\n'
            '🗂 آرشیو دارایی‌ها و نمایه دانش با هر بسته به‌روزرسانی می‌شوند.')
