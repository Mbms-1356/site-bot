"""Shared content-package schema for the Forexin content factory."""
import hashlib
import re
import time
from typing import Any, Dict, List
from quality_gate import audit_package
from brand_config import BRAND, branded_cta

PLATFORMS = ('website', 'podcast', 'instagram', 'telegram', 'whatsapp', 'tiktok', 'youtube', 'linkedin', 'x')


def slugify(value: str) -> str:
    value = re.sub(r'[^a-zA-Z0-9 -]', '', value or '').lower().strip().replace(' ', '-')
    return value[:70] or 'forexin-content-' + str(int(time.time()))


def source_id(source_link: str, source_text: str) -> str:
    raw = (source_link or '') + '\n' + (source_text or '')[:2000]
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]


def _hashtag(value: str) -> str:
    value = re.sub(r'[^\wآ-ی]+', '', str(value or ''), flags=re.UNICODE)
    return '#' + value[:32] if value else ''


def _hashtags(title: str, keywords: List[Any]) -> List[str]:
    base = ['#فارکس', '#LIT', '#مدیریت_ریسک', '#روانشناسی_ترید', '#آموزش_معامله_گری']
    generated = [_hashtag(x) for x in [title] + list(keywords[:4])]
    result = []
    for tag in base + generated:
        if tag and tag not in result:
            result.append(tag)
    return result[:10]


def make_package(article: Dict[str, Any], source_link: str, source_text: str,
                 transcript: str = '', audio_url: str = '') -> Dict[str, Any]:
    title = article.get('title', 'آموزش جدید Forexin')
    slug = slugify(article.get('slug') or title)
    excerpt = article.get('excerpt') or article.get('description', '')
    keywords = article.get('keywords') or []
    body = article.get('body') or []
    script = article.get('podcast_script') or excerpt
    description = article.get('description') or excerpt[:155]
    seo_title = (article.get('seo_title') or title)[:60]
    seo_description = description[:155]
    tags = _hashtags(title, keywords)
    hashtag_text = ' '.join(tags)
    risk_notice = '⚠️ این محتوا صرفاً آموزشی است و توصیه معاملاتی یا تضمین سود نیست.'
    cta = branded_cta()
    visual_prompt = (f'کاور آموزشی حرفه‌ای درباره «{title}» برای برند Forexin؛ فضای مالی مدرن، '
                     'رنگ‌های سبز تیره و طلایی، نمودار انتزاعی بدون عدد جعلی، نورپردازی تمیز، '
                     'بدون وعده سود، بدون سیگنال خرید یا فروش، بدون لوگوی ساختگی، فضای خالی امن برای تیتر فارسی؛ '
                     'در صورت وجود لوگوی رسمی، همان لوگو را در گوشه امن کاور استفاده کن.')
    hooks = [
        f'چرا بیشتر معامله‌گران در موضوع «{title}» اشتباه می‌کنند؟',
        f'قبل از تصمیم‌گیری درباره «{title}»، این نکته را بررسی کنید.',
        f'اگر با «{title}» مشکل دارید، این آموزش کوتاه را ببینید.',
    ]
    return {
        'schema_version': '1.1',
        'id': source_id(source_link, source_text),
        'slug': slug,
        'status': 'draft',
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'brand': {'name': BRAND['name'], 'links': BRAND.copy(),
                  'logo_url': BRAND['logo_url'],
                  'logo_instruction': 'فقط از لوگوی رسمی تأییدشده استفاده شود؛ لوگوی ساختگی تولید نشود.'},
        'source': {'url': source_link, 'text': source_text[:4000], 'transcript': transcript[:12000]},
        'article': {'title': title, 'description': description, 'excerpt': excerpt,
                    'keywords': keywords, 'category': article.get('category', 'آموزش'), 'body': body},
        'seo': {'title': seo_title, 'description': seo_description, 'slug': slug,
                'keywords': keywords, 'canonical_path': 'articles/' + slug + '.html',
                'image_alt': 'تصویر آموزشی درباره ' + title,
                'hashtags': tags},
        'podcast': {'script': script, 'audio_url': audio_url},
        'short_video': {'hooks': hooks, 'script': script[:1800], 'duration_seconds': 45,
                        'caption_overlay': title, 'cta': cta},
        'visuals': {
            'status': 'draft_only',
            'cover_prompt': visual_prompt,
            'thumbnail_text': title[:48],
            'alt_text': 'کاور آموزشی درباره ' + title,
            'assets': {
                'website_cover': {'width': 1200, 'height': 630, 'ratio': '1.91:1', 'prompt': visual_prompt},
                'instagram_portrait': {'width': 1080, 'height': 1350, 'ratio': '4:5', 'prompt': visual_prompt},
                'instagram_square': {'width': 1080, 'height': 1080, 'ratio': '1:1', 'prompt': visual_prompt},
                'reels_story': {'width': 1080, 'height': 1920, 'ratio': '9:16', 'prompt': visual_prompt},
                'youtube_thumbnail': {'width': 1280, 'height': 720, 'ratio': '16:9', 'prompt': visual_prompt},
            },
            'generation': {'provider': 'pending', 'approved_by': None, 'approved_at': None},
        },
        'platforms': {
            'instagram': {'caption': excerpt + '\n\n' + cta + '\n\n' + risk_notice, 'hashtags': tags},
            'telegram': {'text': title + '\n\n' + excerpt + '\n\n' + cta + '\n\n' + risk_notice, 'hashtags': tags},
            'whatsapp': {'text': title + '\n' + excerpt[:500] + '\n' + cta + '\n' + risk_notice, 'hashtags': tags[:6]},
            'tiktok': {'caption': hooks[0] + '\n' + cta + '\n' + risk_notice, 'hashtags': tags[:8]},
            'youtube': {'title': seo_title, 'description': excerpt + '\n\n' + cta + '\n\n' + risk_notice, 'tags': keywords, 'hashtags': tags},
            'linkedin': {'text': 'یادداشت آموزشی: ' + title + '\n\n' + excerpt + '\n\n' + cta + '\n\n' + risk_notice, 'hashtags': tags[:6]},
            'x': {'text': hooks[0] + '\n' + excerpt[:240] + '\n' + cta + '\n' + risk_notice, 'hashtags': tags[:5]},
        },
        'quality': {'score': 0, 'checks': {'source_present': bool(source_text or transcript),
                    'has_title': bool(title), 'has_description': bool(article.get('description')),
                    'has_keywords': len(keywords) >= 3, 'has_body': len(body) >= 3,
                    'risk_notice_required': True}, 'needs_review': True},
        'publishing': {'website': 'draft_only', 'social': 'draft_only', 'approved_by': None, 'approved_at': None},
    }


def score_package(package: Dict[str, Any]) -> int:
    checks = package.get('quality', {}).get('checks', {})
    audit = audit_package(package)
    checks['risk_language'] = audit['passed']
    passed = sum(bool(v) for v in checks.values())
    total = max(len(checks), 1)
    score = round(100 * passed / total)
    package.setdefault('quality', {})['score'] = score
    package['quality']['audit'] = audit
    package['quality']['needs_review'] = score < 90 or audit['blocked']
    package['quality']['blocked'] = audit['blocked']
    return score
