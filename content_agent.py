import base64, html, io, json, os, re, subprocess, tempfile, time, urllib.parse, urllib.request
from pathlib import Path

TOKEN = os.environ.get('TOKEN_AGENT', '').strip()
PAT = os.environ.get('GH_PAT', '').strip()
GROQ = os.environ.get('GROQ_KEY', '').strip()
OPENROUTER = os.environ.get('OPENROUTER_KEY', '').strip()
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
    return json.loads(http(API + '/' + method + q, headers={'User-Agent': 'ForexinContentAgent'}))


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


def state_load():
    x = gh_json(STATE_PATH, SELF_REPO)
    if not x: return {'offset': 0, 'seen': []}
    try: return json.loads(base64.b64decode(x['content']).decode())
    except Exception: return {'offset': 0, 'seen': []}


def state_save(st):
    st['seen'] = st.get('seen', [])[-300:]
    gh_put(STATE_PATH, json.dumps(st, ensure_ascii=False, indent=2), 'Update content agent state', SELF_REPO)


def file_bytes(file_id):
    f = tg('getFile', {'file_id': file_id})['result']['file_path']
    return http('https://api.telegram.org/file/bot' + TOKEN + '/' + f, timeout=180)


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


def make_article(source, transcript):
    prompt = '''از محتوای آموزشی زیر فقط JSON معتبر تولید کن. موضوع فارکس و LIT است. ادعای سود قطعی، سیگنال خرید/فروش و وعده درآمد ممنوع است. پاسخ فارسی باشد.
فیلدها: slug انگلیسی کوتاه، title فارسی، description حداکثر 155 کاراکتر، keywords آرایه 5 تا 8تایی، body آرایه‌ای از 5 تا 8 پاراگراف آموزشی، excerpt یک پاراگراف، podcast_script متن روان 2 تا 4 دقیقه‌ای، category.
منبع را تحریف نکن و اگر نکته‌ای نامطمئن است آن را قطعی ننویس.
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
    media = None; name = 'media.bin'
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
    transcript = transcribe(media, name) if media else ''
    source_link = 'https://t.me/' + (chat.get('username') or '') + '/' + str(post.get('message_id'))
    source = caption or 'آموزش منتشرشده در کانال Base Forexin'
    if not transcript and not caption: return 'no-text'
    article = make_article(source, transcript)
    if not article: return 'generation-failed'
    slug = slugify(article.get('slug'))
    audio = make_audio(article.get('podcast_script', ''))
    audio_url = ''
    if audio:
        audio_path = 'podcasts/' + slug + '.mp3'
        gh_put(audio_path, audio, 'Add podcast audio: ' + slug, SITE_REPO, binary=True)
        audio_url = 'https://mbms-1356.github.io/forexin-site-/' + audio_path
    page = render_article(article, source_link, audio_url)
    gh_put('articles/' + slug + '.html', page, 'Publish SEO article: ' + slug)
    index = gh_json('articles/index.json')
    items = []
    if index:
        try: items = json.loads(base64.b64decode(index['content']).decode())
        except Exception: pass
    items = [x for x in items if x.get('slug') != slug]
    items.insert(0, {'slug': slug, 'title': article.get('title',''), 'description': article.get('description',''), 'url': 'articles/' + slug + '.html', 'audio': audio_url, 'source': source_link, 'published_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
    gh_put('articles/index.json', json.dumps(items[:200], ensure_ascii=False, indent=2), 'Update article index')
    return 'published:' + slug + (':audio' if audio else ':text-only')


def main():
    st = state_load(); offset = int(st.get('offset', 0))
    updates = tg('getUpdates', {'offset': offset + 1, 'timeout': 5}).get('result', [])
    results = []
    for u in updates:
        st['offset'] = max(int(st.get('offset', 0)), int(u.get('update_id', 0)))
        post = u.get('channel_post')
        if post:
            key = str(u['update_id'])
            if key not in st.get('seen', []):
                results.append(handle_post(post)); st.setdefault('seen', []).append(key)
    if updates:
        state_save(st)
    print('content-agent', len(updates), results)

if __name__ == '__main__': main()
