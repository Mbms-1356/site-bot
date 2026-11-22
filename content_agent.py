import base64, html, io, json, os, re, subprocess, tempfile, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from content_package import make_package, score_package
from content_control import draft_path, load_index, save_package, set_status, summary
from file_intake import classify, extract_text, ocr_image
import drive_archive
from private_intake import process_private_upload
from publishing_orchestrator import build_publish_queue
from visual_asset_agent import build_asset_jobs
from analytics_agent import build_report as build_analytics_report
from github_app_auth import readiness as github_app_readiness, github_token
from reel_renderer import render_image_reel
from brand_config import brand_links

TOKEN = os.environ.get('TOKEN_CONTENT_AGENT', '').strip()
PAT = github_token()
GROQ = os.environ.get('GROQ_KEY', '').strip()
OPENROUTER = os.environ.get('OPENROUTER_KEY', '').strip()
CONTENT_ADMIN_CHAT_ID = os.environ.get('CONTENT_ADMIN_CHAT_ID', '').strip()
if not CONTENT_ADMIN_CHAT_ID:
    try:
        CONTENT_ADMIN_CHAT_ID = str(json.loads(Path('admin.json').read_text()).get('id', '')).strip()
    except Exception:
        CONTENT_ADMIN_CHAT_ID = ''
SITE_REPO = 'Mbms-1356/forexin-site-'
SELF_REPO = os.environ.get('GITHUB_REPOSITORY', 'Mbms-1356/site-bot')
BASE_NAMES = {'forexin_turkaslani_base', 'forexinturkaslanibase'}
STATE_PATH = 'content-agent-state.json'
API = 'https://api.telegram.org/bot' + TOKEN


def http(url, data=None, headers=None, timeout=60, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    return urllib.request.urlopen(req, timeout=timeout).read()


def tg(method, params=None):
    q = '' if not params else '?' + urllib.parse.urlencode(params)
    last = None
    for attempt in range(3):
        try:
            return json.loads(http(API + '/' + method + q, headers={'User-Agent': 'ForexinContentAgent'}, timeout=30))
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise last


def tg_send(chat_id, text, keyboard=None):
    params = {'chat_id': chat_id, 'text': text}
    if keyboard:
        params['reply_markup'] = json.dumps(keyboard, ensure_ascii=False)
    try:
        result = tg('sendMessage', params)
        if not result.get('ok'):
            print('telegram-send-result: failed', result.get('description', 'unknown'))
        return result
    except Exception as exc:
        print('telegram-send-failed:', str(exc)[:200])
        return None


def tg_upload(method, field, filename, data, chat_id, caption='', keyboard=None):
    """Upload a preview binary to Telegram using multipart/form-data."""
    if not data or not CONTENT_ADMIN_CHAT_ID:
        return None
    boundary = '----ForexinPreview' + str(int(time.time() * 1000))
    parts = []
    def text_part(name, value):
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n').encode())
    text_part('chat_id', str(chat_id))
    if caption:
        text_part('caption', caption[:1000])
    if keyboard:
        text_part('reply_markup', json.dumps(keyboard, ensure_ascii=False))
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode())
    parts.append(data)
    parts.append(f'\r\n--{boundary}--\r\n'.encode())
    try:
        return json.loads(http(API + '/' + method, b''.join(parts), {
            'Content-Type': 'multipart/form-data; boundary=' + boundary,
            'User-Agent': 'ForexinContentAgent'}, timeout=180))
    except Exception as exc:
        print('telegram-upload-failed:', method, str(exc)[:180])
        return None


def compact_image(data, max_side=1600, quality=82):
    """Keep a readable JPEG archive copy while avoiding large Git/Drive blobs."""
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(data)).convert('RGB')
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        image.save(out, format='JPEG', quality=quality, optimize=True, progressive=True)
        return out.getvalue()
    except Exception:
        return data


def preview_package(chat_id, package, article, audio=None, reel=None, image=None, send_assets=True):
    """Send every generated asset to the admin before any public publication."""
    if not CONTENT_ADMIN_CHAT_ID or str(chat_id) != str(CONTENT_ADMIN_CHAT_ID):
        return
    package_id = package.get('id', '')
    keyboard = draft_keyboard(package, True)
    title = article.get('title', 'بدون عنوان')
    caption = ('🔍 پیش‌نمایش برای بررسی انسانی\n\n' + title + '\n\n' +
               str(article.get('description', '')) +
               '\n\n⚠️ هنوز منتشر نشده است. پس از بررسی، دکمه «تأیید» را بزنید.')
    if image and send_assets:
        tg_upload('sendPhoto', 'photo', package.get('slug', 'cover') + '.jpg', image, chat_id, caption, keyboard)

    # Everything needed for review/copying is delivered in Telegram; GitHub is
    # only the behind-the-scenes archive and recovery store.
    def send_long(text, first_keyboard=None):
        text = str(text or '')
        if not text:
            return
        chunks = [text[i:i + 3500] for i in range(0, len(text), 3500)]
        for i, chunk in enumerate(chunks):
            tg_send(chat_id, chunk, first_keyboard if i == 0 else None)

    body = article.get('body') or []
    body_text = '\n\n'.join(
        ('• ' + str(x.get('heading', '')) + '\n' + str(x.get('content', '')))
        if isinstance(x, dict) else str(x) for x in body
    )
    short_video = package.get('short_video', {})
    platforms = package.get('platforms', {})
    lines = [
        '📰 بسته کامل آماده بررسی در تلگرام',
        '', '🆔 پیش‌نویس: ' + package_id,
        '📌 عنوان: ' + title,
        '', '📝 توضیح کوتاه:', str(article.get('description', '')),
        '', '📚 متن مقاله:', body_text or str(article.get('excerpt', '')),
        '', '🎯 قلاب‌های پیشنهادی:',
    ]
    lines.extend('• ' + str(x) for x in short_video.get('hooks', []))
    lines.extend(['', '🎬 متن ریلز:', str(short_video.get('script', '')),
                  '', '📣 کپشن‌ها و خروجی پلتفرمی:'])
    labels = {'instagram': 'اینستاگرام', 'telegram': 'تلگرام', 'whatsapp': 'واتساپ',
              'tiktok': 'تیک‌تاک', 'youtube': 'یوتیوب', 'linkedin': 'لینکدین', 'x': 'ایکس'}
    for key, label in labels.items():
        item = platforms.get(key, {})
        text = item.get('caption') or item.get('text') or item.get('description') or ''
        tags = item.get('hashtags') or item.get('tags') or []
        lines.extend(['', '🔹 ' + label + ':', str(text), 'هشتگ‌ها: ' + ' '.join(map(str, tags))])
    lines.extend(['', '🔗 لینک‌های رسمی:', brand_links(),
                  '', '⚠️ این بسته هنوز منتشر نشده است و پس از تأیید انسانی قابل انتشار است.',
                  '✅ تأیید | 🚫 رد | ✏️ اصلاح دستی'])
    send_long('\n'.join(lines), keyboard)
    if audio and send_assets:
        tg_upload('sendAudio', 'audio', package.get('slug', 'podcast') + '.mp3', audio, chat_id,
                  '🔊 پیش‌نمایش صوت فارسی — هنوز منتشر نشده است', keyboard)
    if reel and send_assets:
        tg_upload('sendVideo', 'video', package.get('slug', 'reel') + '.mp4', reel, chat_id,
                  '🎬 پیش‌نمایش ریلز ۹:۱۶ — هنوز منتشر نشده است', keyboard)


def gh_binary(path, repo=SITE_REPO):
    item = gh_json(path, repo)
    if not item or not item.get('content'):
        return None
    try:
        return base64.b64decode(item['content'])
    except Exception:
        return None


def publish_approved_package(package):
    """Publish the website/audio/reel only after a human approval callback."""
    article = dict(package.get('article', {}))
    slug = package.get('slug') or 'forexin-content'
    source_link = package.get('source', {}).get('url', '')
    preview_path = package.get('source', {}).get('preview_path', '')
    preview_media = gh_binary(preview_path) if preview_path else None
    if preview_media:
        suffix = Path(preview_path).suffix.lower() or '.bin'
        digest = __import__('hashlib').sha256(preview_media).hexdigest()[:20]
        approved_path = 'media/approved/' + digest + suffix
        gh_put(approved_path, preview_media, 'Archive approved media: ' + slug, SITE_REPO, binary=True)
        package.setdefault('source', {})['media_path'] = approved_path
        package['source']['media_url'] = 'https://mbms-1356.github.io/forexin-site-/' + approved_path
        package['source'].pop('preview_path', None)
        package['source'].pop('preview_url', None)
        try:
            drive_archive.upload_bytes('03_Approved_Knowledge/media/' + digest + suffix, preview_media, 'image/jpeg' if suffix in ('.jpg', '.jpeg') else 'application/octet-stream')
        except Exception:
            pass
    audio_url = ''
    audio_path = package.get('review', {}).get('preview_audio_path', '')
    audio = gh_binary(audio_path) if audio_path else None
    if audio:
        final_audio_path = 'podcasts/' + slug + '.mp3'
        gh_put(final_audio_path, audio, 'Publish approved podcast: ' + slug, SITE_REPO, binary=True)
        audio_url = 'https://mbms-1356.github.io/forexin-site-/' + final_audio_path
        package.setdefault('podcast', {})['audio_url'] = audio_url
    page = render_article(article, source_link, audio_url)
    gh_put('articles/' + slug + '.html', page, 'Publish approved SEO article: ' + slug)
    index = gh_json('articles/index.json')
    items = []
    if index:
        try: items = json.loads(base64.b64decode(index['content']).decode())
        except Exception: pass
    items = [x for x in items if x.get('slug') != slug]
    items.insert(0, {'slug': slug, 'title': article.get('title', ''),
                     'description': article.get('description', ''),
                     'url': 'articles/' + slug + '.html', 'audio': audio_url,
                     'source': source_link,
                     'published_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
    gh_put('articles/index.json', json.dumps(items[:200], ensure_ascii=False, indent=2), 'Update approved article index')
    reel_path = package.get('short_video', {}).get('preview_path', '')
    reel = gh_binary(reel_path) if reel_path else None
    if reel:
        final_reel_path = 'reels/' + slug + '.mp4'
        gh_put(final_reel_path, reel, 'Publish approved educational reel: ' + slug, SITE_REPO, binary=True)
        package['short_video']['url'] = 'https://mbms-1356.github.io/forexin-site-/' + final_reel_path
        package['short_video']['status'] = 'published'
    package.setdefault('review', {})['state'] = 'approved_and_published'
    package.setdefault('publishing', {})['website'] = 'published'
    return package


MAIN_MENU = {'inline_keyboard': [
    [{'text': '🧭 مرکز عملیات', 'callback_data': 'hub'}],
    [{'text': '📋 دستورات سریع', 'callback_data': 'commands'}],
    [{'text': '📊 وضعیت کارخانه', 'callback_data': 'control'}, {'text': '📝 پیش‌نویس‌ها', 'callback_data': 'drafts'}],
    [{'text': '📚 راهنمای کار', 'callback_data': 'help'}, {'text': '🔄 بررسی کانال Base', 'callback_data': 'status'}],
    [{'text': '📝 ارسال متن', 'callback_data': 'intake-text'}, {'text': '🖼 ارسال عکس', 'callback_data': 'intake-image'}],
    [{'text': '🎬 ارسال فیلم', 'callback_data': 'intake-video'}, {'text': '🎙 ارسال صوت', 'callback_data': 'intake-audio'}],
    [{'text': '📄 ارسال PDF / Word', 'callback_data': 'intake-document'}],
]}

QUALITY_MENU = {'inline_keyboard': [
    [{'text': '🧪 گزارش کیفیت', 'callback_data': 'quality-panel'}, {'text': '📝 پیش‌نویس‌ها', 'callback_data': 'drafts'}],
    [{'text': '🚫 موارد مسدودشده', 'callback_data': 'quality-blocked'}, {'text': '🩺 سلامت سیستم', 'callback_data': 'health'}],
    [{'text': '🔁 خطاهای اخیر', 'callback_data': 'errors'}, {'text': '🔙 پنل عملیات', 'callback_data': 'ops-panel'}],
]}

OPERATIONS_MENU = {'inline_keyboard': [
    [{'text': '🔎 تحقیق و ایده', 'callback_data': 'research'}, {'text': '👥 تحلیل رقبا', 'callback_data': 'competitors'}],
    [{'text': '📅 تقویم محتوا', 'callback_data': 'calendar'}, {'text': '📣 رشد قانونی', 'callback_data': 'growth'}],
    [{'text': '🚀 صف انتشار', 'callback_data': 'publishing'}, {'text': '📊 تحلیل عملکرد', 'callback_data': 'analytics'}],
    [{'text': '🗂 آرشیو تأییدشده', 'callback_data': 'archive'}, {'text': '🧠 دانش چت‌بات', 'callback_data': 'knowledge'}],
    [{'text': '🧪 کنترل کیفیت', 'callback_data': 'quality-panel'}, {'text': '☁️ وضعیت Drive', 'callback_data': 'drive-status'}],
    [{'text': '🔙 منوی اصلی', 'callback_data': 'main'}],
]}

CONTROL_MENU = {'inline_keyboard': [
    [{'text': '🧪 پنل کنترل کیفیت', 'callback_data': 'quality-panel'}, {'text': '🧭 پنل عملیاتی', 'callback_data': 'ops-panel'}],
    [{'text': '📋 دستورات سریع', 'callback_data': 'commands'}],
    [{'text': '📥 دریافت محتوا', 'callback_data': 'intake'}, {'text': '📝 پیش‌نویس‌ها', 'callback_data': 'drafts'}],
    [{'text': '📈 تحلیل سؤال‌ها', 'callback_data': 'question-insights'}, {'text': '🎨 دارایی بصری', 'callback_data': 'visual-assets'}],
    [{'text': '🔐 آمادگی GitHub App', 'callback_data': 'github-app'}, {'text': '☁️ وضعیت Drive', 'callback_data': 'drive-status'}],
    [{'text': '🚀 شروع /start', 'callback_data': 'main'}, {'text': '🔄 وضعیت /status', 'callback_data': 'status'}],
    [{'text': 'ℹ️ راهنمای کامل', 'callback_data': 'help'}, {'text': '🔙 منوی اصلی', 'callback_data': 'main'}],
]}

COMMANDS_MENU = {'inline_keyboard': [
    [{'text': '🚀 شروع', 'callback_data': 'main'}, {'text': '🔄 وضعیت', 'callback_data': 'status'}],
    [{'text': '📊 کنترل', 'callback_data': 'control'}, {'text': '📝 پیش‌نویس‌ها', 'callback_data': 'drafts'}],
    [{'text': '📝 ارسال متن', 'callback_data': 'intake-text'}, {'text': '🖼 ارسال عکس', 'callback_data': 'intake-image'}],
    [{'text': '🎬 ارسال فیلم', 'callback_data': 'intake-video'}, {'text': '🎙 ارسال صوت', 'callback_data': 'intake-audio'}],
    [{'text': '📄 ارسال PDF / Word', 'callback_data': 'intake-document'}],
    [{'text': '🧭 مرکز عملیات', 'callback_data': 'hub'}, {'text': 'ℹ️ راهنما', 'callback_data': 'help'}],
]}


def gh_json(path, repo=SITE_REPO):
    try:
        raw = http('https://api.github.com/repos/' + repo + '/contents/' + path,
                   headers={'Authorization': 'Bearer ' + PAT, 'Accept': 'application/vnd.github+json'})
        return json.loads(raw)
    except Exception:
        return None


def gh_put(path, content, message, repo=SITE_REPO, binary=False):
    old = gh_json(path, repo)
    body = {'message': message, 'content': base64.b64encode(content if binary else content.encode('utf-8')).decode()}
    if old and old.get('sha'):
        body['sha'] = old['sha']
    http('https://api.github.com/repos/' + repo + '/contents/' + path,
         data=json.dumps(body).encode(), method='PUT', headers={
             'Authorization': 'Bearer ' + PAT, 'Accept': 'application/vnd.github+json',
             'Content-Type': 'application/json', 'User-Agent': 'ForexinContentAgent'})


def gh_text(path, repo=SITE_REPO):
    item = gh_json(path, repo)
    if not item or 'content' not in item:
        return ''
    try:
        return base64.b64decode(item['content']).decode('utf-8')
    except Exception:
        return ''


def is_content_admin(chat_id):
    configured = CONTENT_ADMIN_CHAT_ID
    if not configured:
        try:
            configured = str(json.loads(Path('admin.json').read_text()).get('id', '')).strip()
        except Exception:
            configured = ''
    return bool(configured) and str(chat_id) == configured


def draft_keyboard(item, admin=False):
    package_id = str(item.get('id', ''))
    if not package_id:
        return None
    buttons = [[{'text': '👁 مشاهده', 'callback_data': 'view:' + package_id}]]
    buttons.append([{'text': '🔗 بازکردن پیش‌نویس',
                     'url': f'https://github.com/{SITE_REPO}/blob/main/content-control/drafts/{package_id}.json'}])
    if admin:
        buttons.append([
            {'text': '✅ تأیید', 'callback_data': 'approve:' + package_id},
            {'text': '🚫 رد', 'callback_data': 'reject:' + package_id},
        ])
        buttons.append([{'text': '✏️ اصلاح دستی',
                         'url': f'https://github.com/{SITE_REPO}/edit/main/content-control/drafts/{package_id}.json'}])
    return {'inline_keyboard': buttons}


def put_json(path, value, message, repo=SITE_REPO):
    gh_put(path, json.dumps(value, ensure_ascii=False, indent=2), message, repo)


def state_load():
    x = gh_json(STATE_PATH, SELF_REPO)
    if not x: return {'offset': 0, 'seen': []}
    try: return json.loads(base64.b64decode(x['content']).decode())
    except Exception: return {'offset': 0, 'seen': []}


def state_save(st):
    st['seen'] = st.get('seen', [])[-300:]
    gh_put(STATE_PATH, json.dumps(st, ensure_ascii=False, indent=2), 'Update content agent state', SELF_REPO)


def update_priority(update):
    """Handle commands and approvals before expensive media/LLM work."""
    msg = update.get('message') or {}
    text = (msg.get('text') or '').strip().lower()
    if text in ('/start', '/help', '/status', '/control', '/drafts'):
        return 0
    if update.get('callback_query'):
        return 1
    if msg.get('chat', {}).get('type') == 'private' and msg.get('text'):
        return 2
    return 3


def record_failure(st, update_id, error):
    failures = st.setdefault('failures', [])
    failures.insert(0, {'update_id': str(update_id), 'error': str(error)[:300], 'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'status': 'retry_pending'})
    st['failures'] = failures[:50]


def health_report(st):
    drive = drive_archive.status()
    return ('🩺 سلامت کارخانه محتوا\n\n'
            f"Telegram token: {'✅' if TOKEN else '❌'}\n"
            f"GitHub token: {'✅' if PAT else '❌'}\n"
            f"LLM key: {'✅' if OPENROUTER else '⚠️ ندارد'}\n"
            f"Transcription key: {'✅' if GROQ else '⚠️ ندارد'}\n"
            f"آخرین offset: {st.get('offset', 0)}\n"
            f"خطاهای در صف بازبینی: {len(st.get('failures', []))}\n\n"
            f"Google Drive: {'✅ فعال' if drive['enabled'] else '⚪ آماده‌سازی نشده (fallback GitHub)'}\n\n"
            'پردازش‌های شکست‌خورده در اجرای بعدی قابل بررسی هستند.')


def quality_report(index):
    total = len(index)
    drafts = sum(1 for x in index if x.get('status') == 'draft')
    approved = sum(1 for x in index if x.get('status') in ('approved', 'published'))
    rejected = sum(1 for x in index if x.get('status') == 'rejected')
    low = [x for x in index if int(x.get('score') or 0) < 90]
    return ('🧪 پنل کنترل کیفیت\n\n'
            f'کل بسته‌ها: {total}\n'
            f'نیازمند بررسی: {drafts}\n'
            f'تأییدشده/منتشرشده: {approved}\n'
            f'ردشده: {rejected}\n'
            f'امتیاز زیر ۹۰: {len(low)}\n\n'
            'قواعد اجباری: هشدار ریسک، نبود تضمین سود، نبود سیگنال قطعی، منبع مشخص و بررسی انسانی.\n'
            'هیچ بسته‌ای بدون عبور از Quality Gate و تأیید مدیر منتشر نمی‌شود.')


def build_research(index):
    topics = []
    for item in index[:20]:
        title = (item.get('title') or '').strip()
        if title and title not in topics:
            topics.append(title)
    seeds = topics[:5] or ['مدیریت ریسک در LIT', 'روانشناسی معامله‌گری', 'تحلیل ساختار بازار']
    ideas = []
    templates = [
        ('اشتباهات رایج', 'اشتباهات رایج در موضوع «{topic}» و روش جلوگیری آموزشی از آن‌ها'),
        ('چک‌لیست', 'چک‌لیست عملی و غیرسیگنالی برای بررسی «{topic}» قبل از تصمیم‌گیری'),
        ('پرسش مخاطب', 'پاسخ آموزشی به پرسش‌های پرتکرار درباره «{topic}»'),
        ('مقایسه مفهومی', 'تفاوت «{topic}» با برداشت‌های نادرست رایج در میان معامله‌گران'),
        ('مطالعه موردی', 'مطالعه موردی آموزشی درباره «{topic}» بدون تضمین نتیجه معاملاتی'),
    ]
    for i, topic in enumerate(seeds):
        kind, title = templates[i % len(templates)]
        ideas.append({'title': title.format(topic=topic), 'format': kind,
                      'source_topic': topic, 'status': 'idea',
                      'risk_note': 'صرفاً آموزشی؛ بدون سیگنال و تضمین سود'})
    return {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'ideas': ideas}


def build_calendar(index):
    ideas = build_research(index)['ideas']
    formats = ['مقاله سایت', 'پست تلگرام', 'ریلز آموزشی', 'پادکست کوتاه', 'پست لینکدین', 'استوری پرسش‌وپاسخ', 'مرور هفتگی']
    days = ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه']
    entries = []
    for i, day in enumerate(days):
        idea = ideas[i % len(ideas)]
        entries.append({'day': day, 'format': formats[i], 'title': idea['title'], 'status': 'planned'})
    return {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'entries': entries}


def live_research(index):
    """Read public Google News RSS results; never auto-publishes or copies articles."""
    local = build_research(index)
    topics = [x.get('source_topic', '') for x in local['ideas'][:3]]
    queries = ['فارکس مدیریت ریسک آموزش'] + [x for x in topics if x]
    items = []
    seen = set()
    for query in queries[:4]:
        url = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(query) + '&hl=fa&gl=IR&ceid=IR:fa'
        try:
            root = ET.fromstring(http(url, timeout=20))
        except Exception:
            continue
        for item in root.findall('./channel/item')[:5]:
            link = (item.findtext('link') or '').strip()
            title = (item.findtext('title') or '').strip()
            if not link or not title or link in seen:
                continue
            seen.add(link)
            items.append({'query': query, 'title': title, 'source_url': link,
                          'published_at': (item.findtext('pubDate') or '').strip(),
                          'use': 'تحقیق و ایده‌پردازی؛ قبل از انتشار راستی‌آزمایی شود'})
    return {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'queries': queries, 'items': items[:15], 'internal_ideas': local['ideas']}


def competitor_report(config):
    competitors = config.get('competitors', []) if isinstance(config, dict) else []
    report = {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'competitors': [], 'note': 'منابع عمومی برای تحقیق؛ قبل از انتشار راستی‌آزمایی شود.'}
    for competitor in competitors[:10]:
        name = str(competitor.get('name') or '').strip()
        query = str(competitor.get('query') or name).strip()
        if not name or not query:
            continue
        articles = []
        url = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(query) + '&hl=fa&gl=IR&ceid=IR:fa'
        try:
            root = ET.fromstring(http(url, timeout=20))
            for item in root.findall('./channel/item')[:5]:
                title = (item.findtext('title') or '').strip()
                link = (item.findtext('link') or '').strip()
                if title and link:
                    articles.append({'title': title, 'source_url': link, 'published_at': (item.findtext('pubDate') or '').strip()})
        except Exception:
            pass
        report['competitors'].append({'name': name, 'platform': competitor.get('platform', 'public-web'), 'query': query, 'items': articles,
                                      'content_gap_prompt': f'چه زاویه آموزشی متفاوتی برای موضوعات «{name}» می‌توان تولید کرد؟'})
    return report


def discover_competitors():
    """Discover public publishers from RSS only; never collect follower identities."""
    queries = ['فارکس آموزش', 'مدیریت سرمایه فارکس', 'استراتژی LIT', 'روانشناسی ترید']
    candidates = {}
    for query in queries:
        url = 'https://news.google.com/rss/search?q=' + urllib.parse.quote(query) + '&hl=fa&gl=IR&ceid=IR:fa'
        try:
            root = ET.fromstring(http(url, timeout=20))
        except Exception:
            continue
        for item in root.findall('./channel/item')[:10]:
            source = item.find('source')
            name = (source.text or '').strip() if source is not None else ''
            link = (item.findtext('link') or '').strip()
            title = (item.findtext('title') or '').strip()
            if not name:
                name = urllib.parse.urlparse(link).netloc
            if not name:
                continue
            row = candidates.setdefault(name, {'name': name, 'platform': 'public-web', 'queries': [], 'examples': []})
            if query not in row['queries']:
                row['queries'].append(query)
            if title and link and len(row['examples']) < 3:
                row['examples'].append({'title': title, 'source_url': link})
    return {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'candidates': sorted(candidates.values(), key=lambda x: len(x['queries']), reverse=True)[:20],
            'note': 'این فهرست فقط از منابع عمومی ساخته شده و قبل از فعال‌سازی نیاز به بررسی انسانی دارد.'}


def growth_plan():
    return {
        'principles': ['رضایت کاربر', 'عدم پیام انبوه', 'عدم استخراج فهرست اعضا', 'ارزش آموزشی قبل از دعوت'],
        'actions': [
            {'channel': 'SEO', 'action': 'ساخت مقاله‌های متمایز بر اساس شکاف محتوایی و دعوت اختیاری به کانال رایگان'},
            {'channel': 'Social', 'action': 'انتشار ریلز و پاسخ‌های آموزشی در صفحات عمومی، بدون تبلیغ مزاحم یا کپی محتوا'},
            {'channel': 'Lead magnet', 'action': 'ارائه چک‌لیست مدیریت ریسک یا درس رایگان با عضویت اختیاری و قابل لغو'},
            {'channel': 'Measurement', 'action': 'استفاده از لینک‌های UTM و گزارش تعداد کلیک، عضویت و تبدیل بدون ذخیره اطلاعات حساس'},
        ],
        'disclaimer': 'هیچ کاربر رقیب به‌صورت خودکار شناسایی، پیام‌دهی یا دعوت نمی‌شود.'
    }


def build_question_insights(rows):
    """Turn unanswered questions into review-only FAQ and challenge candidates."""
    clean = [x for x in rows if x.get('question')]
    clean.sort(key=lambda x: (int(x.get('count', 1)), x.get('last_seen', 0)), reverse=True)
    faq = []
    challenges = []
    for row in clean[:30]:
        question = str(row['question']).strip()
        faq.append({'id': row.get('id'), 'question': question, 'priority': int(row.get('count', 1)), 'status': 'needs_review',
                    'answer_instruction': 'از آرشیو آموزشی تأییدشده پاسخ کوتاه فارسی بساز؛ ادعای سود و سیگنال ممنوع.'})
        challenges.append({'id': 'question-' + str(row.get('id')), 'category': 'پرسش کاربران',
                           'question': question, 'status': 'needs_review',
                           'note': 'قبل از فعال‌سازی، پاسخ صحیح و گزینه‌های انحرافی باید توسط مدیر بررسی شوند.'})
    return {'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'total_questions': len(clean), 'faq_candidates': faq[:20], 'challenge_candidates': challenges[:20],
            'policy': 'این خروجی فقط پیشنهاد است و خودکار منتشر یا فعال نمی‌شود.'}


def candidate_keyboard(kind, candidate_id, admin):
    if not admin:
        return {'inline_keyboard': [[{'text': '👁 مشاهده', 'callback_data': f'candidate-view:{kind}:{candidate_id}'}]]}
    return {'inline_keyboard': [[
        {'text': '👁 مشاهده', 'callback_data': f'candidate-view:{kind}:{candidate_id}'},
        {'text': '✅ تأیید', 'callback_data': f'candidate-approve:{kind}:{candidate_id}'},
        {'text': '🚫 رد', 'callback_data': f'candidate-reject:{kind}:{candidate_id}'},
        {'text': '🚀 فعال‌سازی', 'callback_data': f'candidate-activate:{kind}:{candidate_id}'},
    ]]}


def file_bytes(file_id):
    f = tg('getFile', {'file_id': file_id})['result']['file_path']
    return http('https://api.telegram.org/file/bot' + TOKEN + '/' + f, timeout=180)


def intake_state(st, chat_id, mode=None):
    states = st.setdefault('intake', {})
    key = str(chat_id)
    if mode is not None:
        states[key] = mode
    return states.get(key, '')


def transcribe(data, name='media.mp3'):
    if not GROQ or len(data) > 24 * 1024 * 1024: return ''
    boundary = '----ForexinBoundary' + str(int(time.time()))
    parts = []
    def field(k, v):
        parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="' + k + '"\r\n\r\n' + v + '\r\n').encode())
    field('model', 'whisper-large-v3-turbo')
    field('language', 'fa')
    parts.append(('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' + name + '"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + data + b'\r\n')
    body = b''.join(parts) + ('--' + boundary + '--\r\n').encode()
    try:
        out = http('https://api.groq.com/openai/v1/audio/transcriptions', body, {
            'Authorization': 'Bearer ' + GROQ, 'Content-Type': 'multipart/form-data; boundary=' + boundary}, 180)
        return json.loads(out).get('text', '').strip()
    except Exception:
        return ''


def vision_analyze(data, name='image.jpg'):
    if not OPENROUTER or not data or len(data) > 12 * 1024 * 1024:
        return ''
    try:
        mime = 'image/png' if name.lower().endswith('.png') else 'image/jpeg'
        payload = {'model': 'openai/gpt-4o-mini', 'messages': [{
            'role': 'user', 'content': [
                {'type': 'text', 'text': 'این تصویر را با دقت و فقط بر اساس چیزهایی که واقعاً دیده می‌شود بررسی کن. پاسخ فارسی را دقیقاً با این بخش‌ها بده: «متن قابل‌خواندن تصویر»، «مشاهدات قطعی درباره چیدمان یا نمودار»، «بخش‌های ناخوانا یا نامطمئن». متن را حدس نزن و اگر خوانا نیست بنویس ناخوانا. درباره بروکر، سرمایه، سود، نهادها یا پیام آموزشی چیزی اضافه نکن مگر اینکه در خود تصویر به‌وضوح دیده شود. هیچ سیگنال خرید/فروش یا پیش‌بینی قطعی نده.'},
                {'type': 'image_url', 'image_url': {'url': 'data:' + mime + ';base64,' + base64.b64encode(data).decode()}}
            ]}], 'temperature': 0.2, 'max_tokens': 900}
        raw = http('https://openrouter.ai/api/v1/chat/completions', json.dumps(payload).encode(), {
            'Authorization': 'Bearer ' + OPENROUTER, 'Content-Type': 'application/json'})
        return json.loads(raw)['choices'][0]['message']['content'].strip()
    except Exception:
        return ''


def make_article(source, transcript):
    prompt = '''از محتوای آموزشی زیر فقط JSON معتبر تولید کن. موضوع فارکس و LIT است. ادعای سود قطعی، سیگنال خرید/فروش و وعده درآمد ممنوع است. پاسخ فارسی باشد.
فیلدها: slug انگلیسی کوتاه، title فارسی، seo_title حداکثر 60 کاراکتر، description حداکثر 155 کاراکتر، keywords آرایه 5 تا 8تایی، body آرایه‌ای از 5 تا 8 پاراگراف آموزشی، excerpt یک پاراگراف، podcast_script متن روان 2 تا 4 دقیقه‌ای، reel_script متن مستقل و کامل 90 تا 110 کلمه‌ای برای ریلز دقیقاً 45 ثانیه‌ای، category.
منبع را تحریف نکن و اگر نکته‌ای نامطمئن است آن را قطعی ننویس. podcast_script باید برای خواندن انسانی باشد: جمله‌های کوتاه، لحن گفتاری محترمانه، مکث طبیعی با ویرگول و نقطه، بدون تیتر، بولت، ایموجی، Markdown یا توضیح داخل پرانتز. متن صوتی نباید چیزی بیشتر از منبع ادعا کند.
reel_script باید روایتی مستقل و کامل از همان موضوع باشد؛ با شروع قلاب‌دار، توضیح روشن، جمع‌بندی و دعوت غیرتحمیلی به مطالعه ادامه مطلب. ادعای سود قطعی یا سیگنال نداشته باشد.
CONTENT:
''' + source[:12000] + '\nTRANSCRIPT:\n' + transcript[:30000]
    if not OPENROUTER: return None
    try:
        payload = {'model': 'openai/gpt-4o-mini', 'messages': [
            {'role': 'system', 'content': 'You produce safe, factual Persian educational content. Return JSON only.'},
            {'role': 'user', 'content': prompt}], 'temperature': 0.3, 'response_format': {'type': 'json_object'}}
        raw = http('https://openrouter.ai/api/v1/chat/completions', json.dumps(payload).encode(), {
            'Authorization': 'Bearer ' + OPENROUTER, 'Content-Type': 'application/json'})
        text = json.loads(raw)['choices'][0]['message']['content']
        return json.loads(text)
    except Exception:
        return None


def slugify(s):
    s = re.sub(r'[^a-zA-Z0-9 -]', '', s or '').lower().strip().replace(' ', '-')
    return (s[:70] or 'forexin-lesson-' + str(int(time.time())))


def render_article(a, source_link, audio_url=''):
    title = html.escape(a.get('title', 'آموزش جدید Forexin'))
    desc = html.escape(a.get('description', a.get('excerpt', '')[:155]))
    slug = slugify(a.get('slug'))
    body = ''.join('<p>' + html.escape(str(p)).replace('\n', '<br>') + '</p>' for p in a.get('body', []))
    keys = ', '.join(html.escape(str(x)) for x in a.get('keywords', []))
    audio = ('<p><audio controls preload="none" src="' + html.escape(audio_url) + '"></audio></p>' if audio_url else '')
    return f'''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} | Forexin</title><meta name="description" content="{desc}"><meta name="keywords" content="{keys}"><link rel="canonical" href="https://mbms-1356.github.io/forexin-site-/articles/{slug}.html"><meta property="og:type" content="article"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><script type="application/ld+json">{json.dumps({'@context':'https://schema.org','@type':'Article','headline':a.get('title',''),'description':a.get('description',''),'inLanguage':'fa','mainEntityOfPage':source_link}, ensure_ascii=False)}</script><style>body{{max-width:850px;margin:40px auto;padding:0 20px;font-family:Tahoma,Arial;line-height:2;color:#18232b;background:#f8fbfa}}article{{background:white;padding:28px;border-radius:18px;box-shadow:0 8px 30px #1231}}h1{{color:#0d6658}}.meta{{color:#607d78;font-size:.9em}}audio{{width:100%}}a{{color:#0d6658}}</style></head><body><article><h1>{title}</h1><div class="meta">دسته: {html.escape(str(a.get('category','آموزش')))} · منبع آموزشی: کانال Base</div>{audio}{body}<hr><p>⚠️ این مطلب صرفاً آموزشی است و توصیه معاملاتی یا تضمین سود نیست.</p><p><a href="{html.escape(source_link)}">مشاهده منبع اصلی</a></p></article></body></html>'''


def make_audio(script):
    if not script: return None
    try:
        import asyncio, edge_tts
        script = re.sub(r'[*_#`]+', '', str(script))
        script = re.sub(r'\[[^\]]*\]', '', script)
        script = re.sub(r'\([^)]*\)', '', script)
        script = re.sub(r'\s+', ' ', script).strip()
        path = tempfile.mktemp(suffix='.mp3')
        async def go():
            await edge_tts.Communicate(script[:12000], 'fa-IR-DilaraNeural').save(path)
        asyncio.run(go())
        return Path(path).read_bytes() if Path(path).exists() else None
    except Exception:
        return None


def handle_post(post):
    chat = post.get('chat', {})
    username = (chat.get('username') or '').lower()
    if username not in BASE_NAMES: return 'ignored-channel'
    caption = post.get('caption', '') or post.get('text', '')
    media = None; name = 'media.bin'; image_text = ''; image_analysis = ''
    if post.get('video'):
        media = file_bytes(post['video']['file_id']); name = 'video.mp4'
    elif post.get('audio'):
        media = file_bytes(post['audio']['file_id']); name = post['audio'].get('file_name', 'audio.mp3')
    elif post.get('voice'):
        media = file_bytes(post['voice']['file_id']); name = 'voice.ogg'
    elif post.get('document'):
        doc = post['document']; n = (doc.get('file_name') or '').lower()
        if any(n.endswith(x) for x in ('.mp3','.m4a','.wav','.ogg','.mp4','.mov','.mkv')):
            media = file_bytes(doc['file_id']); name = doc.get('file_name', name)
    elif post.get('photo'):
        media = file_bytes(post['photo'][-1]['file_id'])
        name = 'channel-image.jpg'
        image_text = ocr_image(media, name)
        image_analysis = vision_analyze(media, name)
    transcript = transcribe(media, name) if media else ''
    source_link = 'https://t.me/' + (chat.get('username') or '') + '/' + str(post.get('message_id'))
    source = caption or image_text or image_analysis or 'آموزش منتشرشده در کانال Base Forexin'
    if image_analysis and image_analysis not in source:
        source += '\n\nتحلیل بصری آموزشی:\n' + image_analysis
    if not transcript and not caption and not image_text: return 'no-text'
    article = make_article(source, transcript)
    if not article: return 'generation-failed'
    slug = slugify(article.get('slug'))
    audio = make_audio(article.get('podcast_script', ''))
    reel_audio = make_audio(article.get('reel_script') or article.get('podcast_script', ''))
    # Generated assets stay in a private review area until the admin approves.
    audio_url = ''
    preview_audio_path = ''
    if audio:
        preview_audio_path = 'content-control/previews/' + slug + '.mp3'
        gh_put(preview_audio_path, audio, 'Store podcast preview: ' + slug, SITE_REPO, binary=True)
    package = make_package(article, source_link, source, transcript or image_text, audio_url)
    package.setdefault('review', {})['required'] = True
    package['review']['state'] = 'waiting_for_telegram_review'
    package['review']['preview_audio_path'] = preview_audio_path
    reel_url = ''
    reel = None
    if media and name == 'channel-image.jpg' and reel_audio:
        reel = render_image_reel(media, reel_audio, article.get('reel_script') or article.get('podcast_script', ''))
        if reel:
            reel_path = 'content-control/previews/' + slug + '.mp4'
            gh_put(reel_path, reel, 'Render educational reel: ' + slug, SITE_REPO, binary=True)
            package.setdefault('short_video', {})['status'] = 'rendered'
            package['short_video']['preview_path'] = reel_path
            package['short_video']['format'] = 'mp4'
            package['short_video']['aspect_ratio'] = '9:16'
    if media and name == 'channel-image.jpg':
        media_path = 'content-control/previews/media/' + __import__('hashlib').sha256(media).hexdigest()[:20] + '.jpg'
        compact = compact_image(media)
        gh_put(media_path, compact, 'Store compact Base image preview: ' + slug, SITE_REPO, binary=True)
        package.setdefault('source', {})['type'] = 'channel-image-ocr'
        package['source']['preview_path'] = media_path
        package['source']['preview_url'] = 'https://github.com/' + SITE_REPO + '/blob/main/' + media_path
        package['source']['ocr_text'] = image_text[:12000]
        package['source']['image_analysis'] = image_analysis[:8000]
    score_package(package)
    save_package(package, lambda path: gh_text(path, SITE_REPO),
                 lambda path, value, message: put_json(path, value, message, SITE_REPO))
    preview_package(CONTENT_ADMIN_CHAT_ID, package, article, audio, reel, media if name == 'channel-image.jpg' else None)
    return 'preview-ready:' + slug + (':audio' if audio else ':text-only') + ':awaiting-approval'


def main():
    st = state_load(); offset = int(st.get('offset', 0))
    try:
        identity = tg('getMe').get('result', {})
        print('telegram-identity:', identity.get('username', ''), identity.get('id', ''))
    except Exception as exc:
        print('telegram-identity-failed:', str(exc)[:180])
    try:
        # GitHub Actions is already invoked on a schedule; do not add a long
        # Telegram long-poll delay to each short-lived runner.
        updates = tg('getUpdates', {'offset': offset + 1, 'timeout': 0, 'allowed_updates': json.dumps(['message', 'callback_query', 'channel_post'])}).get('result', [])
    except Exception as exc:
        print('telegram-poll-failed:', str(exc)[:200])
        return
    results = []
    for u in sorted(updates, key=update_priority):
        st['offset'] = max(int(st.get('offset', 0)), int(u.get('update_id', 0)))
        msg = u.get('message') or {}
        if msg and msg.get('chat', {}).get('type') == 'private':
            text = (msg.get('text') or '').strip().lower()
            if text in ('/start', '/help'):
                tg_send(msg['chat']['id'], '🦁 کارخانه محتوای Forexin فعال است.\n\n✅ پست‌های جدید کانال Base را دریافت می‌کنم.\n🎬 ویدئو و صوت را به متن تبدیل می‌کنم.\n📰 مقاله آموزشی و سئوشده می‌سازم.\n🔊 نسخه صوتی پادکست را آماده می‌کنم.\n\n⚠️ این ربات برای پردازش خودکار محتوای کانال Base است؛ محتوای جدید را در همان کانال منتشر کنید.')
                tg_send(msg['chat']['id'], 'یکی از گزینه‌های زیر را انتخاب کنید:', MAIN_MENU)
                results.append('private-start')
                continue
            if text == '/status':
                tg_send(msg['chat']['id'], '✅ کارخانه محتوا فعال است و حداکثر هر ۵ دقیقه کانال Base را بررسی می‌کند.')
                results.append('private-status')
                continue
            if text in ('/control', '/drafts'):
                index = load_index(lambda path: gh_text(path, SITE_REPO))
                if text == '/control':
                    tg_send(msg['chat']['id'], summary(index))
                else:
                    rows = index[:8]
                    if rows:
                        lines = ['📝 آخرین پیش‌نویس‌ها:'] + [
                            f"• {x.get('title','بدون عنوان')} | {x.get('status','draft')} | امتیاز {x.get('score',0)}\n"
                            f"🔗 https://github.com/{SITE_REPO}/blob/main/content-control/drafts/{x.get('id','')}.json"
                            for x in rows]
                        tg_send(msg['chat']['id'], '\n'.join(lines))
                    else:
                        tg_send(msg['chat']['id'], '📝 هنوز بسته محتوایی ثبت نشده است.')
                results.append('private-control')
                continue
            try:
                handled_private = process_private_upload(msg, st, file_bytes, transcribe, make_article, lambda path: gh_text(path, SITE_REPO),
                                      lambda path, value, message: put_json(path, value, message, SITE_REPO),
                                      tg_send, MAIN_MENU,
                                      lambda path, data, message: gh_put(path, data, message, SITE_REPO, binary=True),
                                      vision_analyze,
                                      lambda path, data, category: drive_archive.upload_bytes(path, data, {
                                          'image': 'image/jpeg', 'audio': 'audio/mpeg', 'video': 'video/mp4'
                                      }.get(category, 'application/octet-stream')),
                                      drive_archive.upload_json, make_audio, render_image_reel, tg_upload, preview_package)
            except Exception as exc:
                record_failure(st, u.get('update_id'), exc)
                tg_send(msg['chat']['id'], '⚠️ پردازش این فایل ناموفق شد و خطا برای بررسی ثبت شد. لطفاً دوباره ارسال کنید.', MAIN_MENU)
                handled_private = True
            if handled_private:
                results.append('private-intake')
                continue
        callback = u.get('callback_query')
        if callback:
            # Stop Telegram's loading spinner immediately, before any GitHub
            # API or LLM work is performed for the selected action.
            try:
                tg('answerCallbackQuery', {'callback_query_id': callback.get('id', '')})
            except Exception:
                pass
            chat_id = callback.get('message', {}).get('chat', {}).get('id')
            data = callback.get('data', '')
            if data == 'quality-panel':
                tg_send(chat_id, quality_report(load_index(lambda path: gh_text(path, SITE_REPO))), QUALITY_MENU)
            elif data == 'quality-blocked':
                rows = load_index(lambda path: gh_text(path, SITE_REPO))
                low = [x for x in rows if int(x.get('score') or 0) < 90][:10]
                if not low:
                    tg_send(chat_id, '✅ فعلاً مورد کم‌امتیاز یا مسدودشده‌ای در فهرست خلاصه وجود ندارد.', QUALITY_MENU)
                else:
                    lines = ['🚫 موارد نیازمند کنترل بیشتر:']
                    lines.extend(f"• {x.get('title', 'بدون عنوان')} | امتیاز {x.get('score', 0)} | {x.get('status', 'draft')}" for x in low)
                    tg_send(chat_id, '\n'.join(lines), QUALITY_MENU)
            elif data == 'ops-panel':
                tg_send(chat_id, '🧭 پنل عملیاتی\n\nتحقیق عمومی، تحلیل رقبا، تقویم محتوا، رشد قانونی، صف انتشار، آرشیو و تحلیل عملکرد از این بخش مدیریت می‌شوند.\n\n⚠️ مشتری‌یابی با پیام خصوصی یا استخراج اعضای رقبا فعال نیست؛ فقط جذب اختیاری و مبتنی بر محتوای عمومی مجاز است.', OPERATIONS_MENU)
            elif data == 'control':
                tg_send(chat_id, summary(load_index(lambda path: gh_text(path, SITE_REPO))), MAIN_MENU)
            elif data == 'hub':
                tg_send(chat_id, '🧭 مرکز عملیات Forexin\n\nهمه فرمان‌های تولید، دریافت، کنترل و برنامه‌ریزی محتوا از این بخش قابل دسترسی است.', CONTROL_MENU)
            elif data == 'commands':
                tg_send(chat_id, '📋 دستورات سریع کارخانه محتوا\n\nاز این بخش می‌توانید نوع ورودی و گزارش موردنظر را سریع انتخاب کنید.\n\nفرمان‌های متنی: /start  /status  /control  /drafts', COMMANDS_MENU)
            elif data == 'main':
                tg_send(chat_id, 'منوی اصلی:', MAIN_MENU)
            elif data == 'drafts':
                rows = load_index(lambda path: gh_text(path, SITE_REPO))[:8]
                if not rows:
                    tg_send(chat_id, '📝 هنوز پیش‌نویسی ثبت نشده است.', MAIN_MENU)
                else:
                    tg_send(chat_id, '📝 آخرین پیش‌نویس‌ها:', MAIN_MENU)
                    for row in rows:
                        text_out = (f"• {row.get('title','بدون عنوان')}\nوضعیت: {row.get('status','draft')} | امتیاز: {row.get('score',0)}\n"
                                    f"🔗 https://github.com/{SITE_REPO}/blob/main/content-control/drafts/{row.get('id','')}.json")
                        tg_send(chat_id, text_out, draft_keyboard(row, is_content_admin(chat_id)))
            elif data.startswith(('view:', 'approve:', 'reject:')):
                action, package_id = data.split(':', 1)
                raw = gh_text(draft_path(package_id), SITE_REPO)
                try:
                    package = json.loads(raw)
                except Exception:
                    package = None
                if not package:
                    tg_send(chat_id, '⚠️ پیش‌نویس پیدا نشد یا قابل خواندن نیست.', MAIN_MENU)
                elif action == 'view':
                    article = package.get('article', {})
                    text_out = ('👁 پیش‌نمایش پیش‌نویس\n\n' + str(article.get('title', 'بدون عنوان')) + '\n\n' +
                                str(article.get('description', '')) + '\n\n' +
                                'کلمات کلیدی: ' + ', '.join(map(str, article.get('keywords', []))) + '\n\n' +
                                'وضعیت: ' + str(package.get('status', 'draft')) + '\n' +
                                'کاورها: ' + str(len(package.get('visuals', {}).get('assets', {}))) + ' قالب آماده تولید\n' +
                                'وضعیت کاور: ' + str(package.get('visuals', {}).get('status', 'pending')) + '\n\n' +
                                f"🔗 فایل کامل: https://github.com/{SITE_REPO}/blob/main/content-control/drafts/{package_id}.json")
                    tg_send(chat_id, text_out[:3900], draft_keyboard({'id': package_id, 'status': package.get('status')}, is_content_admin(chat_id)))
                elif not is_content_admin(chat_id):
                    tg_send(chat_id, '⛔ این عملیات فقط برای مدیر مرکز محتوا فعال است.', MAIN_MENU)
                else:
                    new_status = 'approved' if action == 'approve' else 'rejected'
                    try:
                        if new_status == 'approved':
                            package = publish_approved_package(package)
                        set_status(package, new_status, str(chat_id))
                    except ValueError as exc:
                        tg_send(chat_id, '⛔ تأیید مسدود شد. ابتدا Quality Gate را اصلاح کنید.\n' + str(package.get('quality', {}).get('audit', {}).get('warnings', [])), MAIN_MENU)
                        continue
                    except Exception as exc:
                        tg_send(chat_id, '⚠️ انتشار پس از تأیید ناموفق شد و وضعیت پیش‌نویس تغییر نکرد.\n' + str(exc)[:500], MAIN_MENU)
                        continue
                    save_package(package, lambda path: gh_text(path, SITE_REPO), lambda path, value, message: put_json(path, value, message, SITE_REPO))
                    label = 'تأیید شد' if new_status == 'approved' else 'رد شد'
                    tg_send(chat_id, f'✅ پیش‌نویس {label}.\nوضعیت جدید: {new_status}', MAIN_MENU)
            elif data == 'status':
                tg_send(chat_id, '✅ کارخانه محتوا فعال است و کانال Base را در اجرای بعدی بررسی می‌کند.', MAIN_MENU)
            elif data == 'drive-status':
                drive = drive_archive.status()
                tg_send(chat_id, ('☁️ وضعیت Google Drive\n\n'
                                  f"حالت: {drive['mode']}\n"
                                  f"پوشه اصلی: {'✅ تنظیم شده' if drive['root_folder_configured'] else '❌ تنظیم نشده'}\n"
                                  f"Credential: {'✅ تنظیم شده' if drive['credentials_configured'] else '❌ تنظیم نشده'}\n\n"
                                  'تا زمان تکمیل Credential، ذخیره‌سازی GitHub بدون وقفه ادامه دارد.'), CONTROL_MENU)
            elif data == 'health':
                tg_send(chat_id, health_report(st), CONTROL_MENU)
            elif data == 'errors':
                failures = st.get('failures', [])
                if not failures:
                    tg_send(chat_id, '🔁 صف خطا خالی است.', CONTROL_MENU)
                else:
                    lines = ['🔁 آخرین خطاهای قابل بررسی:']
                    lines.extend(f"• {x.get('at','')} | update {x.get('update_id','')}\n  {x.get('error','')}" for x in failures[:8])
                    tg_send(chat_id, '\n'.join(lines), CONTROL_MENU)
            elif data in ('publishing', 'visual-assets', 'analytics', 'github-app'):
                index = load_index(lambda path: gh_text(path, SITE_REPO))
                if data == 'publishing':
                    report = build_publish_queue(index)
                    put_json('content-control/publishing-queue.json', report, 'Update safe publishing queue', SITE_REPO)
                    tg_send(chat_id, f"🚀 صف انتشار امن\n\nموارد آماده بررسی: {len(report['items'])}\nحالت فعلی: پیش‌نمایش امن\nانتشار خودکار شبکه‌های اجتماعی: خاموش\n\nبرای فعال‌سازی باید API پلتفرم و تأیید مدیر اضافه شود.", CONTROL_MENU)
                elif data == 'visual-assets':
                    report = build_asset_jobs(index)
                    put_json('content-control/visual-asset-jobs.json', report, 'Update visual asset jobs', SITE_REPO)
                    tg_send(chat_id, f"🎨 صف دارایی بصری\n\nتعداد بسته‌های آماده: {len(report['jobs'])}\nوضعیت: مانیفست و پرامپت آماده\nتولید واقعی فایل: در انتظار اتصال Canva یا سرویس تصویر\n\nهیچ تصویر بدون تأیید مدیر منتشر نمی‌شود.", CONTROL_MENU)
                elif data == 'analytics':
                    report = build_analytics_report(index)
                    put_json('content-control/analytics.json', report, 'Update content analytics report', SITE_REPO)
                    tg_send(chat_id, f"📊 تحلیل عملکرد محتوا\n\nکل بسته‌ها: {report['total_packages']}\nمیانگین امتیاز کیفیت: {report['average_quality_score']}\nوضعیت‌ها: {report['by_status']}\n\n{report['next_action']}", CONTROL_MENU)
                else:
                    report = github_app_readiness()
                    put_json('content-control/github-app-readiness.json', report, 'Update GitHub App readiness', SITE_REPO)
                    tg_send(chat_id, f"🔐 آمادگی GitHub App\n\nوضعیت: {'آماده' if report['ready'] else 'نیازمند تنظیم'}\nAPP ID: {'✅' if report['checks']['GITHUB_APP_ID'] else '❌'}\nPrivate Key: {'✅' if report['checks']['GITHUB_APP_PRIVATE_KEY'] else '❌'}\nInstallation ID: {'✅' if report['checks']['GITHUB_APP_INSTALLATION_ID'] else '❌'}\n\n{report['note']}", CONTROL_MENU)
            elif data in ('intake', 'document', 'media', 'image', 'intake-text', 'intake-image', 'intake-video', 'intake-audio', 'intake-document'):
                prompts = {
                    'intake-text': '📝 متن آموزشی را همین‌جا به‌صورت پیام ارسال کنید.',
                    'intake-image': '🖼 عکس آموزشی را همین‌جا ارسال کنید؛ نوشته داخل عکس هم خوانده و تحلیل می‌شود.',
                    'intake-video': '🎬 فیلم آموزشی را همین‌جا ارسال کنید؛ گفتار آن به متن تبدیل می‌شود.',
                    'intake-audio': '🎙 فایل صوتی یا Voice را همین‌جا ارسال کنید؛ متن، مقاله، پادکست و کپشن ساخته می‌شود.',
                    'intake-document': '📄 فایل PDF یا Word را همین‌جا ارسال کنید تا متن آن استخراج و به بسته محتوا تبدیل شود.',
                }
                prompt = prompts.get(data, '📥 عکس، فیلم، صوت، PDF، Word یا متن آموزشی را همین‌جا ارسال کنید.')
                tg_send(chat_id, prompt + '\n\n⏳ پس از دریافت، مقاله، قلاب، کپشن پلتفرم‌ها، هشتگ، صوت و در صورت امکان ریلز در همین ربات برای بررسی ارسال می‌شود.', MAIN_MENU)
            elif data in ('research', 'calendar'):
                index = load_index(lambda path: gh_text(path, SITE_REPO))
                if data == 'research':
                    report = live_research(index)
                    put_json('content-control/research.json', report, 'Update live content research', SITE_REPO)
                    lines = ['🔎 تحقیق زنده و ایده‌های تولید محتوا:']
                    lines.extend(f"{i + 1}. {x['title']}\n   منبع: {x['source_url']}" for i, x in enumerate(report['items'][:5]))
                    if not report['items']:
                        lines.append('فعلاً منبع عمومی جدیدی دریافت نشد؛ ایده‌های داخلی همچنان در فایل تحقیق ذخیره شده‌اند.')
                    lines.append('\n⚠️ منابع فقط برای تحقیق هستند؛ قبل از انتشار باید بررسی و بازنویسی شوند و سیگنال یا تضمین سود نیستند.')
                    tg_send(chat_id, '\n'.join(lines), CONTROL_MENU)
                else:
                    calendar = build_calendar(index)
                    put_json('content-control/calendar.json', calendar, 'Update weekly content calendar', SITE_REPO)
                    lines = ['📅 تقویم محتوایی هفتگی:']
                    lines.extend(f"• {x['day']}: {x['format']}\n  {x['title']}" for x in calendar['entries'])
                    tg_send(chat_id, '\n'.join(lines), CONTROL_MENU)
            elif data == 'competitors':
                config = {}
                raw = gh_text('competitors.json', SELF_REPO)
                try:
                    config = json.loads(raw) if raw else {}
                except Exception:
                    config = {}
                report = competitor_report(config)
                put_json('content-control/competitors-report.json', report, 'Update competitor research report', SITE_REPO)
                if not report['competitors']:
                    discovered = discover_competitors()
                    put_json('content-control/discovered-competitors.json', discovered, 'Update discovered public competitors', SITE_REPO)
                    if discovered['candidates']:
                        names = '\n'.join('• ' + x['name'] + ' (' + str(len(x['queries'])) + ' موضوع)' for x in discovered['candidates'][:8])
                        tg_send(chat_id, '👥 فهرست اولیه منابع عمومی پیدا شد:\n\n' + names + '\n\nاین‌ها هنوز رقیب تأییدشده نیستند؛ برای جلوگیری از خطا، ابتدا بررسی انسانی لازم است.', CONTROL_MENU)
                    else:
                        tg_send(chat_id, '👥 فهرست رقبا هنوز تنظیم نشده و منبع عمومی قابل‌اعتمادی پیدا نشد. نام ۳ تا ۵ رقیب یا عبارت جست‌وجوی آن‌ها را در competitors.json وارد کنید.', CONTROL_MENU)
                else:
                    lines = ['👥 گزارش تحلیل رقبا:']
                    lines.extend(f"• {x['name']} ({x['platform']}): {len(x['items'])} مورد عمومی\n  فرصت: {x['content_gap_prompt']}" for x in report['competitors'])
                    lines.append('\n⚠️ این گزارش برای تحقیق است و هیچ محتوایی را کپی یا خودکار منتشر نمی‌کند.')
                    tg_send(chat_id, '\n'.join(lines), CONTROL_MENU)
            elif data == 'growth':
                plan = growth_plan()
                put_json('content-control/audience-growth-plan.json', plan, 'Update compliant audience growth plan', SITE_REPO)
                lines = ['📣 برنامه رشد قانونی مخاطب:', '']
                lines.extend('• ' + x['channel'] + ': ' + x['action'] for x in plan['actions'])
                lines.append('\n⚠️ ' + plan['disclaimer'])
                tg_send(chat_id, '\n'.join(lines), CONTROL_MENU)
            elif data in ('archive', 'knowledge'):
                path = 'content-control/archive/index.json' if data == 'archive' else 'content-control/knowledge/index.json'
                try:
                    records = json.loads(gh_text(path, SITE_REPO) or '[]')
                except Exception:
                    records = []
                if data == 'archive':
                    usable = sum(1 for x in records if x.get('status') in ('approved', 'published'))
                    tg_send(chat_id, f'🗂 آرشیو مرکزی\n\nتعداد بسته‌ها: {len(records)}\nدارایی‌های تأییدشده: {usable}\n\nآرشیو شامل مقاله، کپشن، هشتگ، پادکست، پرامپت کاور و قالب‌های تصویری است.', CONTROL_MENU)
                else:
                    safe = sum(1 for x in records if x.get('safe_for_assistant'))
                    tg_send(chat_id, f'🧠 نمایه دانش چت‌بات\n\nکل مدخل‌ها: {len(records)}\nمجاز برای پاسخ‌گویی: {safe}\n\nچت‌بات فقط از محتوای تأییدشده یا منتشرشده استفاده می‌کند و منابع نامعتبر را قطعی بیان نمی‌کند.', CONTROL_MENU)
            elif data == 'question-insights':
                try:
                    unanswered = json.loads(gh_text('content-control/unanswered-questions.json', SITE_REPO) or '[]')
                except Exception:
                    unanswered = []
                try:
                    previous = json.loads(gh_text('content-control/question-insights.json', SITE_REPO) or '{}')
                except Exception:
                    previous = {}
                insights = build_question_insights(unanswered)
                previous_status = {x.get('id'): x.get('status') for x in previous.get('faq_candidates', []) + previous.get('challenge_candidates', [])}
                for group in ('faq_candidates', 'challenge_candidates'):
                    for candidate in insights[group]:
                        if candidate.get('id') in previous_status:
                            candidate['status'] = previous_status[candidate['id']]
                put_json('content-control/question-insights.json', insights, 'Update unanswered question insights', SITE_REPO)
                top = insights['faq_candidates'][:5]
                if top:
                    lines = ['📈 تحلیل سؤال‌های کاربران:', f"کل سؤال‌های ثبت‌شده: {insights['total_questions']}", '']
                    lines.extend(f"{i + 1}. {x['question']} | اولویت: {x['priority']} | {x['status']}" for i, x in enumerate(top))
                    lines.append('\n✅ از همین فهرست، کاندیدای FAQ و چالش ساخته شد؛ فعال‌سازی هنوز نیازمند بررسی مدیر است.')
                else:
                    lines = ['📈 هنوز سؤال بی‌پاسخ ثبت نشده است.']
                tg_send(chat_id, '\n'.join(lines), CONTROL_MENU)
                for candidate in top:
                    tg_send(chat_id, '❓ کاندیدای FAQ: ' + candidate['question'], candidate_keyboard('faq', candidate['id'], is_content_admin(chat_id)))
                for candidate in insights['challenge_candidates'][:5]:
                    tg_send(chat_id, '🎯 کاندیدای چالش: ' + candidate['question'] + '\nوضعیت: ' + candidate['status'], candidate_keyboard('challenge', candidate['id'], is_content_admin(chat_id)))
            elif data.startswith('candidate-'):
                parts = data.split(':', 2)
                action, kind, candidate_id = parts[0], parts[1], parts[2] if len(parts) > 2 else ''
                try:
                    insights = json.loads(gh_text('content-control/question-insights.json', SITE_REPO) or '{}')
                except Exception:
                    insights = {}
                group = 'faq_candidates' if kind == 'faq' else 'challenge_candidates'
                candidate = next((x for x in insights.get(group, []) if str(x.get('id')) == candidate_id), None)
                if not candidate:
                    tg_send(chat_id, '⚠️ کاندیدا پیدا نشد؛ دوباره گزارش را بسازید.', CONTROL_MENU)
                elif action == 'candidate-view':
                    tg_send(chat_id, ('❓ ' if kind == 'faq' else '🎯 ') + candidate.get('question', '') + '\nوضعیت: ' + candidate.get('status', 'needs_review'), candidate_keyboard(kind, candidate_id, is_content_admin(chat_id)))
                elif not is_content_admin(chat_id):
                    tg_send(chat_id, '⛔ تغییر وضعیت فقط برای مدیر مجاز است.', CONTROL_MENU)
                elif action == 'candidate-activate' and candidate.get('status') != 'approved':
                    tg_send(chat_id, '⚠️ ابتدا باید کاندیدا تأیید شود؛ سپس فعال‌سازی انجام می‌شود.', CONTROL_MENU)
                else:
                    candidate['status'] = 'approved' if action == 'candidate-approve' else 'rejected'
                    if action == 'candidate-activate':
                        candidate['status'] = 'active'
                        if kind == 'challenge':
                            candidate.update({
                                'category': candidate.get('category', 'پرسش کاربران'),
                                'difficulty': 'متوسط',
                                'options': ['بررسی آموزشی موضوع بر اساس آرشیو تأییدشده', 'تضمین سود بدون برنامه', 'نادیده‌گرفتن مدیریت ریسک', 'تصمیم‌گیری بدون تحلیل'],
                                'correct': 0,
                                'explanation': 'پاسخ باید با محتوای آموزشی تأییدشده آرشیو و اصول مدیریت ریسک بررسی شود.',
                                'tip': 'این چالش آموزشی است و نتیجه معاملاتی را تضمین نمی‌کند.',
                            })
                    candidate['reviewed_by'] = str(chat_id)
                    candidate['reviewed_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                    put_json('content-control/question-insights.json', insights, 'Review FAQ or challenge candidate')
                    if action == 'candidate-activate':
                        active_path = 'content-control/active-faq.json' if kind == 'faq' else 'content-control/active-challenges.json'
                        active = [x for x in (insights.get(group, [])) if x.get('status') == 'active']
                        put_json(active_path, active, 'Update active reviewed candidates')
                    tg_send(chat_id, '✅ وضعیت کاندیدا ثبت شد: ' + candidate['status'], CONTROL_MENU)
            elif data == 'research-help':
                tg_send(chat_id, '📚 راهنمای تحقیق:\n\n۱) ایده و تحقیق: موضوعات روز و لینک منابع عمومی.\n۲) تحلیل رقبا: مقایسه منابع عمومی رقبای تنظیم‌شده.\n۳) تقویم محتوا: برنامه هفتگی از ایده‌های ثبت‌شده.\n\nهمه خروجی‌ها قبل از انتشار باید بررسی و بازنویسی شوند.', CONTROL_MENU)
            else:
                tg_send(chat_id, '📚 برای پردازش محتوای جدید، آن را در کانال Base منتشر کنید.', MAIN_MENU)
            results.append('callback-' + data)
            continue
        post = u.get('channel_post')
        if post:
            key = str(u['update_id'])
            if key not in st.get('seen', []):
                try:
                    results.append(handle_post(post))
                    st.setdefault('seen', []).append(key)
                except Exception as exc:
                    record_failure(st, u.get('update_id'), exc)
                    results.append('failed:' + str(exc)[:80])
    if updates:
        state_save(st)
    print('content-agent', len(updates), results)

if __name__ == '__main__': main()
