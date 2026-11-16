"""Visual asset job planner; generation is held until a provider is connected."""
import time


def build_asset_jobs(index, limit=50):
    jobs = []
    for item in index[:limit]:
        jobs.append({'id': item.get('id'), 'title': item.get('title', ''), 'status': 'pending_provider',
                     'formats': ['website_cover', 'instagram_portrait', 'instagram_square', 'reels_story', 'youtube_thumbnail'],
                     'provider': 'pending', 'requires_approval': True})
    return {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'mode': 'manifest-only', 'jobs': jobs,
            'note': 'برای تولید فایل واقعی باید Canva یا سرویس تصویر به‌صورت امن متصل شود.'}
