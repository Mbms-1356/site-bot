"""Safe publishing queue. It prepares approved items; external posting stays disabled until APIs are configured."""
import time

PLATFORMS = ('website', 'telegram', 'instagram', 'youtube', 'tiktok', 'linkedin', 'x', 'whatsapp')


def build_publish_queue(index, limit=50):
    queue = []
    for item in index:
        if item.get('status') != 'approved':
            continue
        queue.append({'id': item.get('id'), 'slug': item.get('slug'), 'title': item.get('title', ''),
                      'platforms': {p: {'status': 'ready_for_manual_or_api_publish'} for p in PLATFORMS},
                      'scheduled_for': None, 'mode': 'dry-run', 'requires_api_credentials': True})
        if len(queue) >= limit:
            break
    return {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'mode': 'safe-preview', 'external_posting_enabled': False, 'items': queue,
            'note': 'هیچ انتشار شبکه اجتماعی بدون اتصال API و تأیید مدیر انجام نمی‌شود.'}
