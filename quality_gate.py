"""Deterministic safety and quality checks for educational finance content."""
import re

GUARANTEE_PATTERNS = [
    r'سود\s+(?:قطعی|تضمینی|حتمی)', r'درآمد\s+(?:قطعی|تضمینی)', r'بدون\s+ریسک',
    r'برد\s*۱۰۰\s*٪', r'برد\s*100\s*%', r'guaranteed\s+profit',
    r'risk[- ]?free', r'no\s+loss', r'100\s*%\s*win',
]
RISK_NOTICE_MARKERS = ('صرفاً آموزشی', 'توصیه معاملاتی', 'تضمین سود نیست', 'نتیجه معاملاتی تضمین')


def audit_package(package):
    article = package.get('article', {})
    texts = [article.get('title', ''), article.get('description', ''), article.get('excerpt', '')]
    texts.extend(str(x) for x in article.get('body', []))
    for value in package.get('platforms', {}).values():
        if isinstance(value, dict):
            texts.extend(str(x) for x in value.values() if isinstance(x, (str, int, float)))
    combined = '\n'.join(texts)
    violations = []
    for pattern in GUARANTEE_PATTERNS:
        if re.search(pattern, combined, flags=re.IGNORECASE):
            violations.append(pattern)
    has_notice = any(marker in combined for marker in RISK_NOTICE_MARKERS)
    warnings = []
    if not has_notice:
        warnings.append('هشدار ریسک مالی در خروجی‌های انتشار پیدا نشد.')
    if len(article.get('keywords', [])) < 3:
        warnings.append('حداقل سه کلمه کلیدی لازم است.')
    if len(article.get('body', [])) < 3:
        warnings.append('بدنه مقاله برای انتشار کامل کوتاه است.')
    return {'passed': not violations and has_notice,
            'blocked': bool(violations) or not has_notice,
            'violations': violations,
            'warnings': warnings}
