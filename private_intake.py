"""Private Telegram intake orchestration for the content factory."""
import hashlib
import io
from pathlib import Path
from content_package import make_package, score_package
from content_control import save_package
from file_intake import classify, extract_text, ocr_image

SITE_REPO = 'Mbms-1356/forexin-site-'


def _compact_image(data):
    """Create a smaller readable archive copy; OCR still uses the original bytes."""
    try:
        from PIL import Image
        image = Image.open(io.BytesIO(data)).convert('RGB')
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        out = io.BytesIO()
        image.save(out, format='JPEG', quality=82, optimize=True, progressive=True)
        return out.getvalue()
    except Exception:
        return data


def _result_links(package, media_url=''):
    package_id = package.get('id', '')
    draft_url = f'https://github.com/{SITE_REPO}/blob/main/content-control/drafts/{package_id}.json'
    lines = [f'🔗 پیش‌نویس کامل: {draft_url}']
    if media_url:
        lines.append(f'🖼 فایل اصلی عکس: {media_url}')
    return '\n'.join(lines)


def process_private_upload(msg, state, file_bytes, transcribe, make_article, gh_text, put_json, tg_send, menu, put_binary=None, analyze_image=None, drive_upload=None, drive_json=None, make_audio=None, render_reel=None, tg_upload=None):
    chat_id = msg.get('chat', {}).get('id')
    if not chat_id:
        return False
    if msg.get('text') and not msg['text'].startswith('/'):
        text = msg['text'].strip()
        if not text:
            return False
        article = make_article(text, '')
        if not article:
            tg_send(chat_id, '⚠️ تولید پیش‌نویس انجام نشد؛ متن را کوتاه‌تر یا دوباره ارسال کنید.', menu)
            return True
        package = make_package(article, '', text, '')
        score_package(package)
        save_package(package, lambda path: gh_text(path), lambda path, value, message: put_json(path, value, message))
        if make_audio and tg_upload:
            audio_preview = make_audio(article.get('podcast_script', ''))
            if audio_preview:
                tg_upload('sendAudio', 'audio', package.get('slug', 'podcast') + '.mp3', audio_preview, chat_id,
                          '🔊 پیش‌نمایش صوتی متن — هنوز منتشر نشده است', menu)
        tg_send(chat_id, f"✅ متن دریافت شد و پیش‌نویس ساخته شد.\n📊 امتیاز: {package['quality']['score']}\n\n{_result_links(package)}", menu)
        return True
    name, file_id, kind = '', None, ''
    if msg.get('document'):
        doc = msg['document']; name = doc.get('file_name', 'upload.bin'); file_id = doc.get('file_id')
    elif msg.get('photo'):
        file_id = msg['photo'][-1].get('file_id'); name = 'upload.jpg'; kind = 'photo'
    elif msg.get('audio'):
        audio = msg['audio']; file_id = audio.get('file_id'); name = audio.get('file_name', 'upload.mp3'); kind = 'audio'
    elif msg.get('voice'):
        file_id = msg['voice'].get('file_id'); name = 'upload.ogg'; kind = 'voice'
    elif msg.get('video'):
        file_id = msg['video'].get('file_id'); name = 'upload.mp4'; kind = 'video'
    else:
        return False
    try:
        tg_send(chat_id, '⏳ فایل دریافت شد؛ در حال بررسی و ساخت بسته محتوا هستم...', menu)
        data = file_bytes(file_id)
    except Exception:
        tg_send(chat_id, '⚠️ دریافت فایل از تلگرام ناموفق بود. لطفاً همان عکس را دوباره ارسال کنید.', menu)
        return True
    category = classify(name, kind)
    media_path = ''
    archive_data = _compact_image(data) if category == 'image' else data
    if put_binary and category in ('image', 'audio', 'video'):
        digest = hashlib.sha256(data).hexdigest()[:20]
        suffix = Path(name or 'upload.bin').suffix.lower()
        if suffix not in ('.jpg', '.jpeg', '.png', '.webp', '.mp3', '.m4a', '.wav', '.ogg', '.mp4', '.mov', '.mkv', '.webm'):
            suffix = '.bin'
        media_path = f'content-control/previews/media/{digest}{suffix}'
        try:
            put_binary(media_path, archive_data, 'Store compact review preview ' + category)
        except Exception:
            media_path = ''
    drive_path = ''
    if drive_upload and category in ('image', 'audio', 'video'):
        suffix = Path(name or 'upload.bin').suffix.lower() or '.bin'
        drive_result = drive_upload('00_Previews/' + hashlib.sha256(data).hexdigest()[:20] + suffix, archive_data, category)
        if drive_result:
            drive_path = drive_result.get('webViewLink') or drive_result.get('id', '')
    if category == 'image':
        extracted = ocr_image(data, name)
        visual_analysis = analyze_image(data, name) if analyze_image else ''
        if not extracted:
            extracted = visual_analysis
            if not extracted:
                tg_send(chat_id, '⚠️ عکس دریافت شد، اما متن یا تحلیل قابل‌اعتمادی پیدا نشد. لطفاً عکس واضح‌تر یا Caption آموزشی ارسال کنید.', menu)
                return True
        caption = (msg.get('caption') or '').strip()
        source = (caption + '\n\n' if caption else '') + extracted
        if visual_analysis and visual_analysis not in source:
            source += '\n\nتحلیل بصری آموزشی:\n' + visual_analysis
        article = make_article(source, '')
        if not article:
            tg_send(chat_id, '⚠️ متن عکس استخراج شد، اما تولید پیش‌نویس ناموفق بود.', menu)
            return True
        package = make_package(article, '', source, '')
        package.setdefault('source', {})['type'] = 'image-ocr'
        package['source']['ocr_text'] = extracted[:12000]
        package['source']['image_analysis'] = visual_analysis[:8000]
        if media_path:
            package['source']['media_path'] = media_path
            package['source']['preview_path'] = media_path
            package['source']['preview_url'] = 'https://github.com/' + SITE_REPO + '/blob/main/' + media_path
        if drive_path:
            package['source']['drive_url'] = drive_path
        score_package(package)
        save_package(package, lambda path: gh_text(path), lambda path, value, message: put_json(path, value, message))
        if drive_json:
            drive_json('00_Previews/packages/' + package.get('id', 'package') + '.json', package)
        if tg_upload:
            tg_upload('sendPhoto', 'photo', package.get('slug', 'cover') + '.jpg', data, chat_id,
                      '🖼 پیش‌نمایش عکس ورودی — هنوز منتشر نشده است', menu)
            if make_audio:
                audio_preview = make_audio(article.get('podcast_script', ''))
                if audio_preview:
                    tg_upload('sendAudio', 'audio', package.get('slug', 'podcast') + '.mp3', audio_preview, chat_id,
                              '🔊 پیش‌نمایش صوتی مقاله — هنوز منتشر نشده است', menu)
                    if render_reel:
                        reel_preview = render_reel(data, audio_preview, article.get('podcast_script', ''))
                        if reel_preview:
                            tg_upload('sendVideo', 'video', package.get('slug', 'reel') + '.mp4', reel_preview, chat_id,
                                      '🎬 پیش‌نمایش ریلز ۹:۱۶ — هنوز منتشر نشده است', menu)
        tg_send(chat_id, f"✅ عکس با OCR خوانده شد و پیش‌نویس ساخته شد.\n🔎 متن استخراج‌شده: {len(extracted)} کاراکتر\n📊 امتیاز: {package['quality']['score']}\n\n{_result_links(package, package.get('source', {}).get('media_url', ''))}", menu)
        return True
    extracted = transcribe(data, name) if category in ('audio', 'video') else extract_text(data, name)
    if not extracted:
        tg_send(chat_id, '⚠️ فایل دریافت شد، اما متن قابل استخراج نبود. برای PDF اسکن‌شده و عکس، OCR در مرحله بعد فعال می‌شود.', menu)
        return True
    article = make_article(extracted, '')
    if not article:
        tg_send(chat_id, '⚠️ فایل خوانده شد اما تولید پیش‌نویس ناموفق بود.', menu)
        return True
    package = make_package(article, '', extracted, extracted)
    if media_path:
        package.setdefault('source', {})['media_path'] = media_path
        package['source']['preview_path'] = media_path
        package['source']['preview_url'] = 'https://github.com/' + SITE_REPO + '/blob/main/' + media_path
        package['source']['media_type'] = category
    if drive_path:
        package['source']['drive_url'] = drive_path
    score_package(package)
    save_package(package, lambda path: gh_text(path), lambda path, value, message: put_json(path, value, message))
    if drive_json:
        drive_json('00_Previews/packages/' + package.get('id', 'package') + '.json', package)
    if make_audio and tg_upload:
        audio_preview = make_audio(article.get('podcast_script', ''))
        if audio_preview:
            tg_upload('sendAudio', 'audio', package.get('slug', 'podcast') + '.mp3', audio_preview, chat_id,
                      '🔊 پیش‌نمایش صوتی فایل — هنوز منتشر نشده است', menu)
    tg_send(chat_id, f"✅ فایل دریافت و پیش‌نویس ساخته شد.\n📄 نوع: {category}\n📊 امتیاز: {package['quality']['score']}\n\n{_result_links(package, package.get('source', {}).get('media_url', ''))}", menu)
    return True
