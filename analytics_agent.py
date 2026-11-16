"""Deterministic content operations analytics from the GitHub-backed index."""
import time


def build_report(index):
    total = len(index)
    counts = {}
    for item in index:
        status = item.get('status', 'unknown')
        counts[status] = counts.get(status, 0) + 1
    scores = [int(x.get('score', 0) or 0) for x in index if x.get('score') is not None]
    return {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'total_packages': total, 'by_status': counts,
            'average_quality_score': round(sum(scores) / len(scores), 1) if scores else 0,
            'top_topics': [{'title': x.get('title', ''), 'score': x.get('score', 0)} for x in index[:10]],
            'next_action': 'پس از اتصال API آمار پلتفرم‌ها، بازدید و تعامل نیز به این گزارش افزوده می‌شود.'}
