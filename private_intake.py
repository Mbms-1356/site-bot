"""Private Telegram intake orchestration for the content factory."""
from content_package import make_package, score_package
from content_control import save_package
from file_intake import classify, extract_text, ocr_image


def process_private_upload(msg, state, file_bytes, transcribe, make_article, gh_text, put_json, tg_send, menu):
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
        tg_send(chat_id, f"✅ متن دریافت شد و پیش‌نویس ساخته شد.\n📊 امتیاز: {package['quality']['score']}", menu)
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
    data = file_bytes(file_id)
    category = classify(name, kind)
    if category == 'image':
        extracted = ocr_image(data, name)
        if not extracted:
            tg_send(chat_id, '⚠️ عکس دریافت شد، اما متن خوانایی برای OCR پیدا نشد. لطفاً عکس واضح‌تر یا فایل اصلی را ارسال کنید.', menu)
            return True
        caption = (msg.get('caption') or '').strip()
        source = (caption + '\n\n' if caption else '') + extracted
        article = make_article(source, '')
        if not article:
            tg_send(chat_id, '⚠️ متن عکس استخراج شد، اما تولید پیش‌نویس ناموفق بود.', menu)
            return True
        package = make_package(article, '', source, '')
        package.setdefault('source', {})['type'] = 'image-ocr'
        package['source']['ocr_text'] = extracted[:12000]
        score_package(package)
        save_package(package, lambda path: gh_text(path), lambda path, value, message: put_json(path, value, message))
        tg_send(chat_id, f"✅ عکس با OCR خوانده شد و پیش‌نویس ساخته شد.\n🔎 متن استخراج‌شده: {len(extracted)} کاراکتر\n📊 امتیاز: {package['quality']['score']}", menu)
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
    score_package(package)
    save_package(package, lambda path: gh_text(path), lambda path, value, message: put_json(path, value, message))
    tg_send(chat_id, f"✅ فایل دریافت و پیش‌نویس ساخته شد.\n📄 نوع: {category}\n📊 امتیاز: {package['quality']['score']}", menu)
    return True
