"""Shared content-package schema for the Forexin content factory."""
import hashlib
import re
import time
from typing import Any, Dict, List

PLATFORMS = ('website', 'podcast', 'instagram', 'telegram', 'whatsapp', 'tiktok', 'youtube', 'linkedin', 'x')


def slugify(value: str) -> str:
    value = re.sub(r'[^a-zA-Z0-9 -]', '', value or '').lower().strip().replace(' ', '-')
    return value[:70] or 'forexin-content-' + str(int(time.time()))


def source_id(source_link: str, source_text: str) -> str:
    raw = (source_link or '') + '\n' + (source_text or '')[:2000]
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]


def make_package(article: Dict[str, Any], source_link: str, source_text: str,
                 transcript: str = '', audio_url: str = '') -> Dict[str, Any]:
    title = article.get('title', 'آموزش جدید Forexin')
    slug = slugify(article.get('slug') or title)
    excerpt = article.get('excerpt') or article.get('description', '')
    keywords = article.get('keywords') or []
    body = article.get('body') or []
    script = article.get('podcast_script') or excerpt
    hooks = [
        f'چرا بیشتر معامله‌گران در موضوع «{title}» اشتباه می‌کنند؟',
        f'قبل از تصمیم‌گیری درباره «{title}»، این نکته را بررسی کنید.',
        f'اگر با «{title}» مشکل دارید، این آموزش کوتاه را ببینید.',
    ]
    cta = 'برای آموزش‌های بیشتر، مقاله کامل و دستیار آموزشی Forexin را ببینید.'
    return {
        'schema_version': '1.0',
        'id': source_id(source_link, source_text),
        'slug': slug,
        'status': 'draft',
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'source': {'url': source_link, 'text': source_text[:4000], 'transcript': transcript[:12000]},
        'article': {'title': title, 'description': article.get('description', ''), 'excerpt': excerpt,
                    'keywords': keywords, 'category': article.get('category', 'آموزش'), 'body': body},
        'podcast': {'script': script, 'audio_url': audio_url},
        'short_video': {'hooks': hooks, 'script': script[:1800], 'duration_seconds': 45,
                        'caption_overlay': title, 'cta': cta},
        'visuals': {'cover_prompt': f'کاور آموزشی حرفه‌ای فارسی درباره {title}، سبک مدرن مالی، بدون وعده سود، فضای خوانا برای تیتر',
                    'thumbnail_text': title[:48]},
        'platforms': {
            'instagram': {'caption': excerpt + '\n\n' + cta, 'hashtags': ['#فارکس', '#LIT', '#مدیریت_ریسک']},
            'telegram': {'text': title + '\n\n' + excerpt + '\n\n' + cta},
            'whatsapp': {'text': title + '\n' + excerpt[:500] + '\n' + cta},
            'tiktok': {'caption': hooks[0] + '\n' + cta, 'hashtags': ['#forex', '#trading', '#LIT']},
            'youtube': {'title': title, 'description': excerpt + '\n\n' + cta, 'tags': keywords},
            'linkedin': {'text': 'یادداشت آموزشی: ' + title + '\n\n' + excerpt},
            'x': {'text': hooks[0] + '\n' + excerpt[:240] + '\n' + cta},
        },
        'quality': {'score': 0, 'checks': {'source_present': bool(source_text or transcript),
                    'has_title': bool(title), 'has_description': bool(article.get('description')),
                    'has_keywords': len(keywords) >= 3, 'has_body': len(body) >= 3,
                    'risk_notice_required': True}, 'needs_review': True},
        'publishing': {'website': 'auto', 'social': 'draft_only', 'approved_by': None, 'approved_at': None},
    }


def score_package(package: Dict[str, Any]) -> int:
    checks = package.get('quality', {}).get('checks', {})
    passed = sum(bool(v) for v in checks.values())
    total = max(len(checks), 1)
    score = round(100 * passed / total)
    package.setdefault('quality', {})['score'] = score
    package['quality']['needs_review'] = score < 90
    return score
