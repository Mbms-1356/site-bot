import os, json, threading, time as _t, re, urllib.request, urllib.parse, ssl, html, base64
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import telebot
from telebot import types
import yt_dlp
import requests
from challenge_engine import get_daily, answer as answer_challenge, profile as challenge_profile, report as challenge_report
from assistant_engine import answer_question, record_unanswered
from assistant_tts import synthesize_fa

TOKEN = (os.environ.get('TELEGRAM_SITE_BOT_TOKEN', '').strip()
         or os.environ.get('TOKEN_SITE', '').strip()
         or os.environ.get('TELEGRAM_BOT_TOKEN', '').strip())
if not TOKEN:
    try:
        with open(os.path.join(os.path.expanduser('~'), 'token.txt')) as f:
            TOKEN = f.read().strip()
    except Exception:
        TOKEN = ''
if not TOKEN or ':' not in TOKEN:
    raise ValueError('Token not found!')

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'

SITE = 'https://mbms-1356.github.io/forexin-site-/'
ARTICLE = SITE + 'lit-liquidity.html'
CHANNEL = 'https://t.me/forexin_turkaslanifree'
CHANNEL_POST = '@forexin_turkaslanifree'
GROUP = 'https://t.me/forexinturkaslanilitcommuniti'
MAINBOT = '@TurkaslaniSiteBot'
FREE_CHANNEL = '@forexin_turkaslanifree'
GUIDE_AUDIO = 'guide_fa.wav'
BASE_CHANNEL = '@Forexin_Turkaslani_Base'
INSTA = 'https://www.instagram.com/forexin.turkaslani'
YOUTUBE = 'https://www.youtube.com/@Forexin.turkaslani'
QUIZ = SITE + 'quiz.html'
DATA_FILE = 'trades.json'
ADMIN_FILE = 'admin.json'
GROUP_FILE = 'group_id.txt'
INVITE_FILE = 'invites.json'
CACHE_FILE = 'usdt_cache.json'
BLOCK_FILE = 'blocklist.json'
DL_DIR = 'dl'
os.makedirs(DL_DIR, exist_ok=True)

GH_TOKEN = os.environ.get('GH_TOKEN', '').strip()
GH_REPO = os.environ.get('GH_REPO', '').strip()
DATA_FILES = [DATA_FILE, ADMIN_FILE, GROUP_FILE, INVITE_FILE, CACHE_FILE, BLOCK_FILE]

def fetch_json(url):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    return json.load(urllib.request.urlopen(req, timeout=6, context=ctx))

def fetch_text(url, referer=None, timeout=10):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {'User-Agent': UA}
    if referer: headers['Referer'] = referer
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8', 'ignore')

_dirty = False
ASSISTANT_USERS = set()
def mark_dirty():
    global _dirty
    _dirty = True

def gh_load():
    if not GH_REPO:
        return
    for f in DATA_FILES:
        if os.path.exists(f):
            continue
        try:
            body = fetch_text('https://raw.githubusercontent.com/' + GH_REPO + '/main/' + f, timeout=8)
            if body:
                with open(f, 'w') as fh:
                    fh.write(body)
        except Exception:
            pass

def gh_save():
    global _dirty
    if not (GH_TOKEN and GH_REPO) or not _dirty:
        return
    for f in DATA_FILES:
        try:
            with open(f) as fh:
                content = fh.read()
        except Exception:
            continue
        try:
            url = 'https://api.github.com/repos/' + GH_REPO + '/contents/' + f
            h = {'Authorization': 'Bearer ' + GH_TOKEN, 'Accept': 'application/vnd.github+json', 'User-Agent': UA}
            r = requests.get(url, headers=h, timeout=8)
            sha = r.json().get('sha') if r.ok else None
            payload = {'message': 'data sync', 'content': base64.b64encode(content.encode()).decode()}
            if sha:
                payload['sha'] = sha
            requests.put(url, headers=h, json=payload, timeout=10)
        except Exception:
            pass
    _dirty = False

gh_load()

ADMIN = None
try:
    with open(ADMIN_FILE) as f: ADMIN = json.load(f)['id']
except Exception: pass

GROUP_ID = None
try:
    with open(GROUP_FILE) as f: GROUP_ID = int(f.read().strip())
except Exception: pass

INVITES = {}
try:
    with open(INVITE_FILE) as f: INVITES = json.load(f)
except Exception: pass

USDT_CACHE = {}
try:
    with open(CACHE_FILE) as f: USDT_CACHE = json.load(f)
except Exception: pass

BLOCKLIST = set()
try:
    with open(BLOCK_FILE) as f: BLOCKLIST = set(json.load(f))
except Exception: pass

CAPTCHA = {}

def save_invites():
    mark_dirty()
    try:
        with open(INVITE_FILE, 'w') as f: json.dump(INVITES, f)
    except Exception: pass

def save_usdt_cache(p, src):
    mark_dirty()
    global USDT_CACHE
    USDT_CACHE = {'price': int(p), 'ts': int(_t.time()), 'src': src}
    try:
        with open(CACHE_FILE, 'w') as f: json.dump(USDT_CACHE, f)
    except Exception: pass

def save_blocklist():
    mark_dirty()
    try:
        with open(BLOCK_FILE, 'w') as f: json.dump(list(BLOCKLIST), f)
    except Exception: pass

def block_user(uid):
    BLOCKLIST.add(int(uid))
    save_blocklist()

def is_blocked(uid):
    return int(uid) in BLOCKLIST

def save_group(gid):
    mark_dirty()
    global GROUP_ID
    if GROUP_ID is None:
        GROUP_ID = gid
        try:
            with open(GROUP_FILE, 'w') as f: f.write(str(gid))
        except Exception: pass

USERS, WARNS = set(), {}
WARN_TXT = {
    'fa': '⚠️ ارسال لینک/تبلیغ ممنوع است! (اخطار {n}/2)',
    'en': '⚠️ Links/ads are not allowed! (Warning {n}/2)',
    'tr': '⚠️ Link/reklam yasaktır! (Uyarı {n}/2)',
    'az': '⚠️ Link/reklam qadağandır! (Xəbərdarlıq {n}/2)',
    'ur': '⚠️ لنک/اشتہار ممنوع ہے! (انتباہ {n}/2)',
    'ku': '⚠️ Lînk/reklam qedexe ye! (Hişyarî {n}/2)',
    'ar': '⚠️ الروابط/الإعلانات ممنوعة! (تحذير {n}/2)'
}

try:
    with open(DATA_FILE) as f: TRADES = json.load(f)
except Exception: TRADES = []

def save_trades():
    mark_dirty()
    try:
        with open(DATA_FILE, 'w') as f: json.dump(TRADES, f)
    except Exception: pass

def ensure_admin(uid):
    global ADMIN
    if ADMIN is None:
        ADMIN = uid
        mark_dirty()
        try:
            with open(ADMIN_FILE, 'w') as f: json.dump({'id': uid}, f)
        except Exception: pass
        return True
    return uid == ADMIN

QUOTES = [
    "بازار هرگز اشتباه نمی‌کند؛ فقط دیدگاه ما اشتباه است.",
    "صبر، نیمی از پیروزی در ترید است.",
    "تریدر حرفه‌ای ریسک را مدیریت می‌کند؛ آماتور سود را دنبال می‌کند.",
    "استاپ‌لاس هزینه نیست؛ بیمهٔ زندگی معامله‌گر است.",
    "حرکت با نخبگان، معامله برای برد."
]

GLOSS = {
    'lat': 'لات: واحد حجم معامله؛ ۱ لات = ۱۰۰ واحد ارز پایه.',
    'pip': 'پیپ: کوچک‌ترین واحد تغییر قیمت.',
    'stop': 'استاپ: سفارش محدودکنندهٔ ضرر.',
    'ahrom': 'اهرم: سرمایهٔ قرضی از بروکر.',
    'spread': 'اسپرد: فاصلهٔ بین قیمت خرید و فروش.',
    'target': 'تارگت: هدف سود معامله.',
    'session': 'سشن: بازهٔ زمانی فعالیت بازار.',
    'candle': 'کندل: نمایش قیمت در یک بازه.',
    'pattern': 'پترن: الگوی تکرارشوندهٔ قیمتی.',
    'lit': 'LIT: استراتژی فارکسین ترک اصلانی.',
    'vip': 'VIP: کانال ویژهٔ سیگنال‌ها.'
}

BASE_GUIDE = '''📌 راهنمای کامل ورود به کانال بیس

🎯 کانال بیس: @Forexin_Turkaslani_Base
آکادمی عملی: آموزش استراتژی LIT، مدیریت سرمایه.

🔑 روش ورود (تنها روش):
1️⃣ ربات: @TurkaslaniSiteBot و /start
2️⃣ دکمه «🎟️ لینک دعوت» را بزنید.
3️⃣ لینک‌تان را برای ۲ دوست بفرستید.
4️⃣ هر عضو موفق = ۱ دعوت.
5️⃣ بعد از ۲ دعوت، لینک کانال بیس ارسال می‌شود. 🎉

تیم Forexin Turkaslani'''

WELCOME_PRIV = 'سلام! 👋\nمن دستیار فارکسین ترک اصلانی هستم.\n<i>📊 ژورنال | 💰 قیمت | 🎬 دانلودر | 📚 آموزش</i>'

WELCOME_GROUP = '''سلام {first} عزیز! 🌟
به «LIT Community» خوش آمدید.

کانال‌ها:
1️⃣ سیگنال: @forexin_turkaslanifree
2️⃣ آموزش: @Forexin_Turkaslani_Base
3️⃣ گروه: همین‌جا
4️⃣ یوتیوب: youtube.com/@Forexin.turkaslani

⚠️ مطالب آموزشی | 🚫 لینک/تبلیغ ممنوع.'''

FLAGS = {'USD': '🇺🇸', 'EUR': '🇪🇺', 'GBP': '🇬🇧', 'JPY': '🇯🇵', 'CNY': '🇨🇳', 'AUD': '🇦🇺', 'CAD': '🇨🇦', 'CHF': '🇨🇭', 'NZD': '🇳🇿'}

def build_menu():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton('🎟️ VIP', callback_data='code'), types.InlineKeyboardButton('❓ سوالات', callback_data='faq'))
    m.add(types.InlineKeyboardButton('💰 طلا', callback_data='gold'), types.InlineKeyboardButton('🇮🇷 تتر', callback_data='usdt'))
    m.add(types.InlineKeyboardButton('📅 اخبار مهم امروز', callback_data='news'))
    m.add(types.InlineKeyboardButton('🕒 وضعیت سشن‌ها', callback_data='sessions'))
    m.add(types.InlineKeyboardButton('🎯 چالش روز', callback_data='challenge'))
    m.add(types.InlineKeyboardButton('📊 پیشرفت من', callback_data='challenge_progress'))
    m.add(types.InlineKeyboardButton('🤖 دستیار آموزشی', callback_data='assistant'))
    m.add(types.InlineKeyboardButton('📖 راهنمای استفاده', callback_data='guide'), types.InlineKeyboardButton('🤖 معرفی سیستم', callback_data='about'))
    m.add(types.InlineKeyboardButton('🔊 راهنمای صوتی', callback_data='guide_audio'))
    m.add(types.InlineKeyboardButton('🎬 دانلود', callback_data='dl'), types.InlineKeyboardButton('📊 معامله', callback_data='tr'))
    m.add(types.InlineKeyboardButton('📈 گزارش', callback_data='rp'), types.InlineKeyboardButton('💬 بازخورد', callback_data='fb'))
    m.add(types.InlineKeyboardButton('🧠 آزمون', url=QUIZ), types.InlineKeyboardButton('📚 مقاله', url=ARTICLE))
    m.add(types.InlineKeyboardButton('🌐 سایت', url=SITE), types.InlineKeyboardButton('📢 کانال', url=CHANNEL))
    m.add(types.InlineKeyboardButton('📷 اینستا', url=INSTA), types.InlineKeyboardButton('▶️ یوتیوب', url=YOUTUBE))
    m.add(types.InlineKeyboardButton('🎁 لینک‌ها', callback_data='inv'), types.InlineKeyboardButton('🎟️ لینک دعوت', callback_data='invite'))
    m.add(types.InlineKeyboardButton('🚀 شروع', callback_data='st'))
    return m

def group_menu():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton('💰 طلا', callback_data='gold'), types.InlineKeyboardButton('🇮🇷 تتر', callback_data='usdt'))
    m.add(types.InlineKeyboardButton('📅 اخبار مهم امروز', callback_data='news'))
    m.add(types.InlineKeyboardButton('🕒 وضعیت سشن‌ها', callback_data='sessions'))
    m.add(types.InlineKeyboardButton('🎯 چالش روز', callback_data='challenge'))
    m.add(types.InlineKeyboardButton('📊 پیشرفت من', callback_data='challenge_progress'))
    m.add(types.InlineKeyboardButton('📖 راهنمای استفاده', callback_data='guide'), types.InlineKeyboardButton('🤖 معرفی سیستم', callback_data='about'))
    m.add(types.InlineKeyboardButton('🎬 دانلود', callback_data='dl'), types.InlineKeyboardButton('📜 قوانین', callback_data='rules'))
    m.add(types.InlineKeyboardButton('🧠 آزمون', url=QUIZ), types.InlineKeyboardButton('📚 مقاله', url=ARTICLE))
    m.add(types.InlineKeyboardButton('🎁 لینک‌ها', callback_data='inv'), types.InlineKeyboardButton('🎟️ لینک دعوت', callback_data='invite'))
    m.add(types.InlineKeyboardButton('🚀 شروع', callback_data='st'))
    return m

def join_menu():
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton('📢 عضویت در کانال فری', url=CHANNEL))
    m.add(types.InlineKeyboardButton('✅ بررسی عضویت', callback_data='join_check'))
    m.add(types.InlineKeyboardButton('📖 راهنمای استفاده', callback_data='guide'))
    m.add(types.InlineKeyboardButton('🔊 راهنمای صوتی', callback_data='guide_audio'))
    return m

def is_free_member(uid):
    try:
        member = bot.get_chat_member(FREE_CHANNEL, uid)
        return member.status in ('creator', 'administrator', 'member')
    except Exception:
        return False

def send_join_gate(chat):
    bot.send_message(chat, '🔒 برای استفاده از امکانات ربات، ابتدا عضو کانال فری شوید و سپس «بررسی عضویت» را بزنید.\n\nراهنمای متنی و صوتی برای آشنایی شما آزاد است.', reply_markup=join_menu())

def guide_text():
    return f"📖 <b>راهنمای استفاده از Forexin</b>\n\n۱. ابتدا عضو کانال فری شوید.\n۲. دکمه «بررسی عضویت» را بزنید.\n۳. از منو قیمت طلا و تتر، اخبار اقتصادی، وضعیت سشن‌ها و چالش روز را استفاده کنید.\n۴. از «پیشرفت من» امتیاز، streak و نشان‌های آموزشی خود را ببینید.\n۵. برای آموزش بیشتر از کانال آکادمی، گروه و یوتیوب استفاده کنید.\n\n🔗 کانال فری: {CHANNEL}\n🎓 آکادمی: {BASE_CHANNEL}\n💬 گروه: {GROUP}\n▶️ یوتیوب: {YOUTUBE}\n\n⚠️ همه مطالب آموزشی‌اند و توصیه خرید یا فروش نیستند."

def about_text():
    return f"🤖 <b>سیستم Forexin</b>\n\nاین ربات برای آموزش، مقاله، دانلود، قیمت‌ها، اخبار، سشن‌ها و چالش‌های آموزشی طراحی شده است. ربات سیگنال نیز برای اطلاع‌رسانی سریع بازار استفاده می‌شود.\n\n📢 پیام‌های خودکار سشن‌ها فقط یک‌بار در کانال فری منتشر می‌شوند.\n\n{CHANNEL}\n{MAINBOT}"

FAQS = {
    'faq_market': ('💰 قیمت‌ها و سیگنال', 'قیمت طلا و تتر برای اطلاع‌رسانی بازار هستند و تضمین یا توصیه خرید و فروش نیستند. قبل از هر معامله، تحلیل شخصی، حد ضرر و مقدار ریسک را مشخص کنید.'),
    'faq_sessions': ('🕒 سشن‌های بازار', 'سشن‌های فرانکفورت، لندن و نیویورک زمان فعالیت بازار را نشان می‌دهند؛ بازشدن سشن به‌تنهایی سیگنال ورود نیست. خبر و ساختار قیمت را نیز بررسی کنید.'),
    'faq_risk': ('🛡 مدیریت ریسک', 'در هر معامله مقدار ریسک را از قبل مشخص کنید، حد ضرر را حذف نکنید و پس از ضرر برای جبران عجله نکنید. حفظ سرمایه مقدم بر سود کوتاه‌مدت است.'),
    'faq_news': ('📅 اخبار اقتصادی', 'اخبار مهم می‌توانند نوسان را افزایش دهند. پیش از معامله تقویم اقتصادی را بررسی کنید و نزدیک خبرهای پرقدرت حجم معامله را کاهش دهید یا صبر کنید.'),
    'faq_challenge': ('🎯 چالش و امتیاز', 'چالش روز برای یادگیری و ساختن عادت آموزشی است. امتیاز و streak فقط معیار تمرین هستند، نه معیار تضمین سود یا مهارت قطعی در معامله.'),
    'faq_lit': ('📚 آموزش LIT', 'برای یادگیری LIT از کانال آکادمی و محتوای آموزشی استفاده کنید. هر مفهوم را ابتدا روی داده گذشته تمرین و سپس با حساب آزمایشی ارزیابی کنید.'),
    'faq_audio': ('🔊 پاسخ صوتی متداول', 'برای شنیدن پاسخ صوتی نکات مهم بازار، مدیریت ریسک، سشن‌ها، اخبار و چالش روز، دکمه زیر را بزنید.')
}

def faq_menu():
    m = types.InlineKeyboardMarkup(row_width=2)
    for key in ('faq_market', 'faq_sessions', 'faq_risk', 'faq_news', 'faq_challenge', 'faq_lit'):
        m.add(types.InlineKeyboardButton(FAQS[key][0], callback_data=key))
    m.add(types.InlineKeyboardButton('🔊 پاسخ صوتی متداول', callback_data='faq_audio'))
    return m

def tehran_now():
    return datetime.now(timezone(timedelta(hours=3, minutes=30)))

SESSION_EVENTS = [
    ('frankfurt_open', '🇩🇪 بازشدن فرانکفورت', 'Europe/Berlin', 8, 0),
    ('london_open', '🇬🇧 بازشدن لندن', 'Europe/London', 8, 0),
    ('newyork_open', '🇺🇸 بازشدن نیویورک و شروع هم‌پوشانی لندن–نیویورک', 'America/New_York', 8, 0),
    ('london_close', '🇬🇧 بسته‌شدن لندن', 'Europe/London', 17, 0),
]

def sessions_status():
    now = tehran_now()
    active = []
    for name, zone, start, end in [
        ('آسیا', 'Asia/Tokyo', 0, 9),
        ('فرانکفورت', 'Europe/Berlin', 8, 16),
        ('لندن', 'Europe/London', 8, 17),
        ('نیویورک', 'America/New_York', 8, 17),
    ]:
        local = now.astimezone(ZoneInfo(zone))
        if start <= local.hour + local.minute / 60 < end:
            active.append(name)
    upcoming = []
    for delta in range(0, 3):
        date = (now + timedelta(days=delta)).date()
        for key, label, zone, hour, minute in SESSION_EVENTS:
            local_dt = datetime(date.year, date.month, date.day, hour, minute, tzinfo=ZoneInfo(zone))
            tehran_dt = local_dt.astimezone(now.tzinfo)
            if tehran_dt >= now:
                upcoming.append((tehran_dt, label))
    upcoming.sort(key=lambda x: x[0])
    next_line = '⏳ رویداد بعدی: ' + upcoming[0][1] + '، ساعت ' + upcoming[0][0].strftime('%H:%M') if upcoming else '⏳ رویداد بعدی نامشخص است.'
    active_line = '، '.join(active) if active else 'هیچ سشن اصلی در این لحظه فعال نیست.'
    return '🕒 <b>وضعیت سشن‌های بازار</b>\n\n✅ سشن فعال: ' + active_line + '\n' + next_line + '\n\n⚠️ زمان‌ها به وقت ایران هستند؛ این بخش اطلاع‌رسانی آموزشی است و سیگنال خرید یا فروش نیست.'

def challenge_prompt(q):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, option in enumerate(q['options']):
        markup.add(types.InlineKeyboardButton(option, callback_data=f"challenge_answer:{q['id']}:{i}"))
    return f"🎯 <b>چالش روز | {q['category']}</b>\nسطح: {q['difficulty']}\n\n{q['question']}", markup

def clean(x):
    s = str(x)
    s = s.translate(str.maketrans({'۰':'0','۱':'1','۲':'2','۳':'3','۴':'4','۵':'5','۶':'6','۷':'7','۸':'8','۹':'9','٠':'0','١':'1','٢':'2','٣':'3','٤':'4','٥':'5','٦':'6','٧':'7','٨':'8','٩':'9'}))
    return int(float(s.replace(',', '').replace('٬', '').replace('،', '').replace(' ', '')))

def get_gold_only():
    try:
        d = fetch_json('https://api.gold-api.com/price/XAU')
        p = round(float(d['price']), 2)
        return f"🥇 <b>قیمت لحظه‌ای انس جهانی طلا:</b> ${p}\n<i>🤖 Forexin Bot</i>"
    except Exception:
        try:
            d = fetch_json('https://data-asg.goldprice.org/dbXRates/USD')
            p = round(float(d['items'][0]['xau_price']), 2)
            return f"🥇 <b>قیمت لحظه‌ای انس جهانی طلا:</b> ${p}\n<i>🤖 Forexin Bot</i>"
        except Exception as e2:
            return f"🥇 <b>انس طلا:</b> خطا\n<code>{html.escape(str(e2)[:80])}</code>"

def get_usdt_only():
    gold_line = ''
    try:
        g = fetch_json('https://api.gold-api.com/price/XAU')
        ounce = float(g['price'])
        base = USDT_CACHE.get('price') or 189000
        gold_line = f"\n🪙 طلای ۱۸ عیار (تخمینی): {int(base * ounce / 31.1035 * 0.75):,} تومان/گرم"
    except Exception:
        pass
    return ('🇮 <b>قیمت لحظه‌ای تتر در بازار ایران:</b>\n\n'
        '🥇 <a href="https://nobitex.ir/price/usdt/">نوبیتکس (دقیق‌ترین)</a>\n'
        '🥈 <a href="https://tabdeal.org/usdt-price">تبدیل</a>\n'
        '🥉 <a href="https://www.ompfinex.com/markets/usdt-price">اُم‌فاینکس</a>\n'
        + gold_line +
        '\n\n💡 روی هر گزینه بزنید تا قیمت زنده باز شود.\n<i>🤖 Forexin Bot</i>')

def news_today():
    try:
        r = requests.get(
            'https://nfs.faireconomy.media/ff_calendar_thisweek.json',
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=15,
        )
        r.raise_for_status()
        d = r.json()
        now = tehran_now()
        lines = []
        for ev in d:
            if ev.get('impact') != 'High': continue
            try:
                dt = datetime.fromisoformat(ev['date'].replace('Z', '+00:00'))
            except Exception: continue
            dt_ir = dt.astimezone(timezone(timedelta(hours=3, minutes=30)))
            if dt_ir.date() != now.date(): continue
            flag = FLAGS.get(ev.get('country', ''), '🌐')
            lines.append(f"{flag} <b>{ev['title']}</b>\n⏰ {dt_ir.strftime('%H:%M')}")
            if len(lines) >= 8: break
        if lines:
            return "📅 <b>تقویم امروز:</b>\n\n" + "\n\n".join(lines)
    except Exception:
        return '⚠️ منبع تقویم اقتصادی موقتاً در دسترس نیست؛ لطفاً چند دقیقه بعد دوباره امتحان کنید.'
    return '📅 امروز خبر پرقدرتی در تقویم اقتصادی وجود ندارد.'

def tiktok_full(u):
    q = urllib.parse.quote(u, safe='')
    try:
        r = requests.get('https://www.tikwm.com/api/?hd=1&url=' + q, headers={'User-Agent': UA}, timeout=20)
        res = r.json()
        if res.get('code') == 0:
            vd = res['data']
            vurl = vd.get('hdplay') or vd.get('play')
            if vurl and not vurl.startswith('http'): vurl = 'https://tikwm.com' + vurl
            return requests.get(vurl, timeout=30, headers={'User-Agent': UA}).content, (vd.get('title') or 'TikTok')[:50]
    except Exception: pass
    try:
        r = requests.post('https://tikwm.com/api/', data={'url': u, 'hd': 1}, headers={'User-Agent': UA}, timeout=20)
        res = r.json()
        if res.get('code') == 0:
            vd = res['data']
            vurl = vd.get('hdplay') or vd.get('play')
            if vurl and not vurl.startswith('http'): vurl = 'https://tikwm.com' + vurl
            return requests.get(vurl, timeout=30, headers={'User-Agent': UA}).content, (vd.get('title') or 'TikTok')[:50]
    except Exception: pass
    try:
        r = requests.get('https://api.tiklydown.eu.org/api/download?url=' + q, timeout=20)
        d = r.json()
        v = d.get('video')
        if v and v.get('playback'):
            return requests.get(v['playback'], timeout=60, headers={'User-Agent': UA}).content, (d.get('title') or 'TikTok')[:50]
    except Exception: pass
    try:
        sess = requests.Session()
        sess.headers.update({'User-Agent': UA, 'Referer': 'https://ttsave.app/'})
        r = sess.post('https://ttsave.app/download', data={'id': u, 'locale': 'en'}, timeout=20)
        m = re.search(r'(https?://[^"\s]+\.mp4[^"\s]*)', r.text)
        if not m:
            m = re.search(r'href="(https?://[^"]+)"[^>]*>[^<]*[Dd]ownload', r.text)
        if m:
            data = sess.get(m.group(1), timeout=60).content
            if len(data) > 50000:
                return data, 'TikTok'
    except Exception: pass
    return yt_dl(u)

def insta_dl_multi(url):
    services = [
        ('igram.world', 'https://igram.world/api/ajaxSearch', {'q': url, 't': 'media'}),
        ('saveig.app', 'https://saveig.app/api/ajaxSearch', {'q': url, 't': 'media'}),
        ('snapinsta.app', 'https://snapinsta.app/action', {'url': url, 'lang_code': 'en'}),
    ]
    for name, endpoint, data in services:
        try:
            sess = requests.Session()
            sess.headers.update({'User-Agent': UA, 'Referer': f'https://{name}/'})
            r = sess.post(endpoint, data=data, timeout=15)
            res = r.json() if r.text.startswith('{') else {}
            html_content = res.get('html') or res.get('data') or str(res)
            vm = re.search(r'href="(https?://[^"]+)"[^>]*>Download', html_content, re.I)
            if not vm:
                vm = re.search(r'(https?://[^"\'\s]+\.mp4[^"\'\s]*)', html_content, re.I)
            if vm:
                vurl = vm.group(1)
                video_data = sess.get(vurl, timeout=60).content
                if len(video_data) > 50000:
                    return video_data, f'Instagram ({name})'
        except Exception:
            continue
    raise Exception('all insta services failed')

def yt_id(u):
    m = re.search(r'(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})', u)
    return m.group(1) if m else None

PIPED = ['https://pipedapi.kavin.rocks', 'https://pipedapi.adminforge.de', 'https://pipedapi.reallyaweso.me']

def piped_dl(u):
    vid = yt_id(u)
    if not vid: raise Exception('no id')
    for base in PIPED:
        try:
            d = requests.get(base + '/streams/' + vid, headers={'User-Agent': UA}, timeout=10).json()
            streams = d.get('videoStreams') or []
            best = None
            for s in streams:
                if '720' in (s.get('quality') or ''): best = s; break
            if not best and streams: best = streams[-1]
            if best and best.get('url'):
                data = requests.get(best['url'], timeout=90, headers={'User-Agent': UA}).content
                if len(data) > 100000:
                    return data, (d.get('title') or 'YouTube')[:50]
        except Exception: continue
    raise Exception('piped failed')

INVIDIOUS = ['https://inv.nadeko.net', 'https://invidious.f5.si', 'https://y.com.sb', 'https://iv.melmac.space', 'https://invidious.nerdvpn.de', 'https://inv.tux.pizza', 'https://invidious.flokinet.to']

def invidious_dl(u):
    vid = yt_id(u)
    if not vid: raise Exception('no id')
    for base in INVIDIOUS:
        try:
            d = requests.get(base + '/api/v1/videos/' + vid + '?local=true', headers={'User-Agent': UA}, timeout=10).json()
            fmts = (d.get('formatStreams') or []) + (d.get('adaptiveFormats') or [])
            best = None
            for f in fmts:
                if str(f.get('type', '')).startswith('video/mp4') and f.get('url'):
                    q = str(f.get('qualityLabel') or f.get('quality') or '')
                    if '720' in q or '480' in q or '360' in q:
                        best = f
                        break
                    if not best: best = f
            if best and best.get('url'):
                vurl = best['url']
                if vurl.startswith('/'): vurl = base + vurl
                data = requests.get(vurl, timeout=90, headers={'User-Agent': UA}).content
                if len(data) > 100000:
                    return data, (d.get('title') or 'YouTube')[:50]
        except Exception: continue
    raise Exception('invidious failed')

def ssyoutube_dl(url):
    try:
        ss_url = url.replace('youtube.com', 'ssyoutube.com').replace('youtu.be', 'ssyoutube.com/watch?v=')
        sess = requests.Session()
        sess.headers.update({'User-Agent': UA})
        page = sess.get(ss_url, timeout=20, allow_redirects=True).text
        links = re.findall(r'href="(https?://[^"]+)"[^>]*>.*?(?:720p|HD|Download)', page, re.I)
        if not links:
            links = re.findall(r'href="(https?://[^"]+\.mp4[^"]*)"', page, re.I)
        if links:
            data = sess.get(links[0], timeout=90).content
            if len(data) > 100000:
                return data, 'YouTube Video'
        raise Exception('no link')
    except Exception as e:
        raise Exception(f'ssyoutube: {str(e)[:40]}')

def yt_dl(url):
    opts = {
        'outtmpl': os.path.join(DL_DIR, '%(id)s.%(ext)s'),
        'format': 'best[height<=720]/best',
        'quiet': True, 'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 30, 'retries': 3,
        'extractor_args': {'youtube': {'player_client': ['tv', 'android', 'ios', 'web']}},
        'http_headers': {'User-Agent': UA}
    }
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(url, download=True)
        fn = y.prepare_filename(info)
    with open(fn, 'rb') as f: data = f.read()
    title = info.get('title', 'Video')[:50]
    try: os.remove(fn)
    except Exception: pass
    return data, title

def handle_download(m, url):
    wait = bot.send_message(m.chat.id, '⏳ <b>در حال دانلود...</b>')
    def job():
        try:
            if 'tiktok.com' in url:
                data, title = tiktok_full(url)
            elif 'instagram.com' in url:
                try:
                    data, title = insta_dl_multi(url)
                except Exception:
                    data, title = yt_dl(url)
            else:
                try:
                    data, title = piped_dl(url)
                except Exception:
                    try:
                        data, title = invidious_dl(url)
                    except Exception:
                        try:
                            data, title = ssyoutube_dl(url)
                        except Exception:
                            data, title = yt_dl(url)
            if len(data) > 48*1024*1024:
                bot.send_message(m.chat.id, '⚠️ فایل سنگین است.')
            else:
                fp = os.path.join(DL_DIR, 'send.mp4')
                with open(fp, 'wb') as f: f.write(data)
                with open(fp, 'rb') as f:
                    bot.send_video(m.chat.id, f, caption=f"<b>{title}</b>\n<i>🤖 Forexin</i>", supports_streaming=True)
                try: os.remove(fp)
                except Exception: pass
            try: bot.delete_message(m.chat.id, wait.message_id)
            except Exception: pass
        except Exception as e:
            err = str(e)
            if 'instagram.com' in url:
                msg = f'❌ اینستاگرام این ویدیو را نمی‌دهد.\n💡 از <code>igram.world</code> دستی استفاده کنید.\n<code>{html.escape(err[:80])}</code>'
            elif 'youtube.com' in url or 'youtu.be' in url:
                msg = f'❌ یوتیوب این ویدیو را نمی‌دهد.\n💡 از <code>ssyoutube.com</code> دستی استفاده کنید.\n<code>{html.escape(err[:80])}</code>'
            else:
                msg = f'❌ دانلود ناموفق.\n💡 تیک‌تاک: <code>snaptik.app</code>\n<code>{html.escape(err[:100])}</code>'
            bot.send_message(m.chat.id, msg)
            try: bot.delete_message(m.chat.id, wait.message_id)
            except Exception: pass
    threading.Thread(target=job, daemon=True).start()

def is_link(txt):
    return bool(re.search(r'https?://|t\.me/|@[\w]{5,}|\.com|\.ir', txt.lower()))

def post_all(text):
    try: bot.send_message(CHANNEL_POST, text)
    except Exception: pass
    if GROUP_ID:
        try: bot.send_message(GROUP_ID, text)
        except Exception: pass

def sync_loop():
    while True:
        _t.sleep(120)
        try: gh_save()
        except Exception: pass

def cap_watch():
    while True:
        _t.sleep(10)
        try:
            now = _t.time()
            for uid in list(CAPTCHA):
                rec = CAPTCHA[uid]
                if now > rec['exp']:
                    CAPTCHA.pop(uid, None)
                    try: bot.delete_message(rec['chat'], rec['msg'])
                    except Exception: pass
                    try: bot.ban_chat_member(rec['chat'], uid)
                    except Exception: pass
        except Exception: pass

threading.Thread(target=sync_loop, daemon=True).start()
threading.Thread(target=cap_watch, daemon=True).start()

@bot.message_handler(content_types=['new_chat_members'])
def new_member(m):
    if m.chat.type in ('group', 'supergroup'):
        save_group(m.chat.id)
    for u in m.new_chat_members:
        if not u.is_bot:
            if is_blocked(u.id):
                try:
                    bot.ban_chat_member(m.chat.id, u.id)
                    bot.send_message(m.chat.id, f'⛔ <b>{u.first_name}</b> قبلاً بن شده بود؛ دوباره حذف شد.')
                except Exception: pass
                continue
            if m.chat.type in ('group', 'supergroup'):
                try:
                    bot.restrict_chat_member(m.chat.id, u.id, can_send_messages=False, can_send_audios=False, can_send_documents=False, can_send_photos=False, can_send_videos=False, can_send_other_messages=False)
                except Exception: pass
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton('✅ من ربات نیستم', callback_data=f'cap:{u.id}'))
                msg = bot.send_message(m.chat.id, f'🛡️ <b>{u.first_name or "کاربر"}</b> عزیز، خوش آمدید!\nبرای تأیید، تا ۲ دقیقه دکمهٔ زیر را بزنید:', reply_markup=mk)
                CAPTCHA[u.id] = {'chat': m.chat.id, 'exp': _t.time() + 120, 'msg': msg.message_id, 'name': u.first_name or 'دوست'}

@bot.message_handler(commands=['challenge_report'])
def challenge_report_cmd(m):
    if not is_admin(m.from_user.id):
        return
    r = challenge_report()
    weak = '، '.join(f'{name} ({data["accuracy"]}٪)' for name, data in r['weakest']) or 'هنوز داده کافی نیست'
    top = '\n'.join(f"{i+1}. کاربر ...{row['uid'][-4:]} — {row['points']} امتیاز" for i, row in enumerate(r['leaderboard'])) or 'هنوز داده‌ای ثبت نشده'
    bot.send_message(m.chat.id, f"📈 <b>گزارش چالش‌ها</b>\n\n👥 کاربران فعال: {r['users']}\n📝 پاسخ‌ها: {r['answers']}\n✅ دقت کلی: {r['accuracy']}٪\n📚 موضوعات نیازمند تقویت: {weak}\n\n🏆 <b>رتبه‌بندی آموزشی:</b>\n{top}")

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    if m.chat.type in ('group', 'supergroup'):
        save_group(m.chat.id)
        bot.send_message(m.chat.id, WELCOME_PRIV, reply_markup=group_menu())
        return
    if ADMIN is None:
        ensure_admin(uid)
        bot.send_message(uid, '🛠️ <b>شما ادمین شدید!</b>')
        return
    if not is_free_member(uid):
        send_join_gate(uid)
        return
    USERS.add(uid)
    extra = ''
    rec = INVITES.get(str(uid))
    if rec:
        extra = f"\n🎟️ دعوت‌های شما: {rec.get('count', 0)}/2"
    bot.send_message(uid, WELCOME_PRIV + extra, reply_markup=build_menu())

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    chat = c.message.chat.id
    uid = c.from_user.id
    d = c.data
    try:
        if c.message.chat.type == 'private' and not ensure_admin(uid) and d not in ('join_check', 'guide', 'guide_audio', 'about') and not is_free_member(uid):
            send_join_gate(chat)
            bot.answer_callback_query(c.id, 'ابتدا عضو کانال فری شوید.')
            return
        if d.startswith('cap:'):
            target = int(d[4:])
            if uid == target and target in CAPTCHA:
                rec = CAPTCHA.pop(target, None)
                try: bot.delete_message(rec['chat'], rec['msg'])
                except Exception: pass
                try:
                    bot.restrict_chat_member(rec['chat'], target, can_send_messages=True, can_send_audios=True, can_send_documents=True, can_send_photos=True, can_send_videos=True, can_send_other_messages=True)
                except Exception: pass
                bot.send_message(rec['chat'], WELCOME_GROUP.format(first=rec.get('name', 'دوست')), reply_markup=group_menu())
                bot.answer_callback_query(c.id, '✅ تأیید شد؛ خوش آمدید!')
                return
            bot.answer_callback_query(c.id)
            return
        if d == 'st':
            if c.message.chat.type in ('group', 'supergroup'):
                bot.send_message(chat, WELCOME_PRIV, reply_markup=group_menu())
            else:
                bot.send_message(chat, WELCOME_PRIV, reply_markup=build_menu())
        elif d == 'join_check':
            if is_free_member(uid):
                bot.send_message(chat, '✅ عضویت شما تأیید شد. اکنون همه امکانات فعال است.', reply_markup=build_menu())
            else:
                send_join_gate(chat)
        elif d == 'guide':
            bot.send_message(chat, guide_text(), reply_markup=join_menu() if not is_free_member(uid) else build_menu())
        elif d == 'guide_audio':
            if os.path.exists(GUIDE_AUDIO):
                with open(GUIDE_AUDIO, 'rb') as audio:
                    bot.send_audio(chat, audio, caption='🔊 راهنمای صوتی استفاده از Forexin')
            else:
                bot.send_message(chat, '🔊 راهنمای صوتی در حال آماده‌سازی است.')
        elif d == 'about':
            bot.send_message(chat, about_text())
        elif d == 'assistant':
            ASSISTANT_USERS.add(uid)
            bot.send_message(chat, '🤖 <b>دستیار آموزشی Forexin</b>\n\nسؤال خود را درباره LIT، نقدینگی، POI، Imbalance، مدیریت ریسک، سشن‌ها یا ژورنال بنویسید.\n\nپاسخ‌ها آموزشی‌اند و سیگنال قطعی خرید یا فروش نیستند. برای خروج از حالت سؤال، /cancel را بفرستید.')
        elif d == 'inv':
            bot.send_message(chat, f"🎁 <b>لینک‌های مفید:</b>\n🤖 {MAINBOT}\n📢 @forexin_turkaslanifree\n🎓 @Forexin_Turkaslani_Base\n💬 @forexinturkaslanilitcommuniti")
        elif d == 'gold':
            bot.send_message(chat, get_gold_only())
        elif d == 'usdt':
            bot.send_message(chat, get_usdt_only())
        elif d == 'news':
            bot.send_message(chat, news_today() or '📅 امروز خبر پرقدرتی در تقویم اقتصادی پیدا نشد.')
        elif d == 'sessions':
            bot.send_message(chat, sessions_status())
        elif d == 'challenge':
            q = get_daily(uid)
            if q:
                text, markup = challenge_prompt(q)
                bot.send_message(chat, text, reply_markup=markup)
            else:
                bot.send_message(chat, '🎯 فعلاً چالش جدیدی آماده نیست.')
        elif d.startswith('challenge_answer:'):
            _, qid, option = d.split(':', 2)
            result = answer_challenge(uid, qid, option)
            if not result:
                bot.send_message(chat, '⚠️ این چالش دیگر در دسترس نیست.')
            else:
                q = result['question']
                prefix = 'ℹ️ شما چالش امروز را قبلاً پاسخ داده‌اید.' if result['already'] else ('✅ پاسخ درست بود!' if result['correct'] else '❌ پاسخ درست نبود؛ نکته آموزشی را ببینید.')
                user = result['user']
                badges = '، '.join(user.get('badges', [])) or 'هنوز نشان جدیدی ندارید'
                bot.send_message(chat, f"{prefix}\n\n<b>پاسخ صحیح:</b> {q['options'][q['correct']]}\n{q['explanation']}\n\n🛡 <b>نکته:</b> {q['tip']}\n\n🏆 امتیاز: {user.get('points', 0)}\n🔥 روزهای متوالی: {user.get('streak', 0)}\n🏅 نشان‌ها: {badges}")
        elif d == 'challenge_progress':
            user = challenge_profile(uid)
            answered = sum(1 for item in user.get('history', {}).values() if item.get('answered'))
            correct = sum(1 for item in user.get('history', {}).values() if item.get('correct'))
            badges = '، '.join(user.get('badges', [])) or 'هنوز نشان جدیدی ندارید'
            bot.send_message(chat, f"📊 <b>پیشرفت آموزشی شما</b>\n\n🏆 امتیاز: {user.get('points', 0)}\n📝 چالش‌های پاسخ‌داده‌شده: {answered}\n✅ پاسخ‌های صحیح: {correct}\n🔥 روزهای متوالی: {user.get('streak', 0)}\n🏅 نشان‌ها: {badges}")
        elif d == 'dl':
            bot.send_message(chat, '🎬 <b>لینک ویدیو را بفرستید:</b>\n(یوتیوب، اینستاگرام، تیک‌تاک)')
        elif d == 'rules':
            bot.send_message(chat, '📜 <b>قوانین:</b>\n۱. احترام\n۲. بدون تبلیغ\n۳. فقط مباحث ترید\n۴. لینک = ۲ اخطار = بن دائمی')
        elif d == 'code':
            bot.send_message(chat, '🎟️ <b>کد VIP را وارد کنید:</b>')
        elif d == 'faq':
            bot.send_message(chat, '❓ <b>مرکز سوالات متداول Forexin</b>\nموضوع موردنظر را انتخاب کنید. پاسخ‌ها آموزشی هستند و پاسخ صوتی هم در دسترس است.', reply_markup=faq_menu())
        elif d in FAQS and d != 'faq_audio':
            bot.send_message(chat, f"❓ <b>{FAQS[d][0]}</b>\n\n{FAQS[d][1]}", reply_markup=faq_menu())
        elif d == 'faq_audio':
            if os.path.exists('faq_fa.wav'):
                with open('faq_fa.wav', 'rb') as audio:
                    bot.send_audio(chat, audio, caption='🔊 پاسخ صوتی سوالات متداول Forexin')
            else:
                bot.send_message(chat, FAQS['faq_audio'][1], reply_markup=faq_menu())
        elif d.startswith('gloss_'):
            bot.send_message(chat, GLOSS.get(d[6:], '❓'))
        elif d == 'fb':
            bot.send_message(chat, '💬 <b>بازخورد خود را بنویسید.</b>')
        elif d == 'base':
            bot.send_message(chat, BASE_GUIDE)
        elif d == 'invite':
            rec = INVITES.setdefault(str(uid), {'count': 0, 'ok': False})
            if rec.get('ok'):
                bot.send_message(chat, '✅ دسترسی فعال!\n🎓 @Forexin_Turkaslani_Base')
            else:
                if not rec.get('link'):
                    try:
                        rec['link'] = bot.create_chat_invite_link(FREE_CHANNEL, name=str(uid)).invite_link
                        save_invites()
                    except Exception as e:
                        bot.send_message(chat, f"❌ خطا: <code>{html.escape(str(e)[:80])}</code>")
                        bot.answer_callback_query(c.id); return
                bot.send_message(chat, f"🎁 <b>لینک دعوت شما:</b>\n<code>{rec['link']}</code>\n📊 {rec.get('count', 0)} از ۲")
        elif d == 'tr':
            bot.send_message(chat, '📊 (ادمین) /trade ورود استاپ تارگت')
        elif d == 'rp':
            wins = len([x for x in TRADES if x.get('result') == 'win'])
            loss = len([x for x in TRADES if x.get('result') == 'loss'])
            bot.send_message(chat, f"📈 برنده: {wins} | بازنده: {loss}")
        elif d.startswith('w') or d.startswith('l'):
            tid = int(d[1:])
            for x in TRADES:
                if x.get('id') == tid:
                    x['result'] = 'win' if d.startswith('w') else 'loss'
            save_trades()
            bot.answer_callback_query(c.id, '✅ ثبت شد'); return
    except Exception: pass
    bot.answer_callback_query(c.id)

@bot.chat_member_handler(func=lambda cm: True)
def on_member(cm):
    try:
        if is_blocked(cm.new_chat_member.user.id):
            try:
                bot.ban_chat_member(cm.chat.id, cm.new_chat_member.user.id)
            except Exception: pass
            return
        if cm.invite_link is None or cm.new_chat_member.status != 'member':
            return
        link = cm.invite_link.invite_link
        for uid, rec in list(INVITES.items()):
            if rec.get('link') == link and int(uid) != cm.new_chat_member.user.id:
                rec['count'] = rec.get('count', 0) + 1
                save_invites()
                if rec['count'] >= 2 and not rec.get('ok'):
                    rec['ok'] = True
                    save_invites()
                    try:
                        bl = bot.create_chat_invite_link(BASE_CHANNEL, member_limit=1).invite_link
                    except Exception:
                        bl = 'https://t.me/Forexin_Turkaslani_Base'
                    bot.send_message(int(uid), f"🎉 دسترسی باز شد!\n🎓 {bl}")
                else:
                    bot.send_message(int(uid), f"✅ یک دعوت! ({rec['count']} از ۲)")
    except Exception: pass

@bot.message_handler(func=lambda m: True)
def txt(m):
    uid = m.from_user.id
    t = m.text.strip()
    is_grp = m.chat.type in ('group', 'supergroup')
    if is_grp: save_group(m.chat.id)

    if not is_grp and uid in ASSISTANT_USERS:
        if t == '/cancel':
            ASSISTANT_USERS.discard(uid)
            bot.send_message(m.chat.id, '✅ از حالت دستیار خارج شدید.', reply_markup=build_menu())
            return
        if not is_free_member(uid) and not ensure_admin(uid):
            send_join_gate(m.chat.id)
            return
        result = answer_question(t)
        if result.get('matched'):
            mk = types.InlineKeyboardMarkup(row_width=1)
            if result.get('url'):
                mk.add(types.InlineKeyboardButton('📚 مطالعه مقاله مرتبط', url=result['url']))
            for related in result.get('related', [])[:2]:
                if related.get('url'):
                    mk.add(types.InlineKeyboardButton('📖 ' + related.get('title', 'مطالب مرتبط')[:35], url=related['url']))
            answer_text = f"🤖 <b>پاسخ آموزشی</b>\n🏷 موضوع: {result['category']} | سطح: {result['difficulty']}\n\n{result['answer']}\n\n🛡 <b>نکته:</b> {result['tip']}\n\n⚠️ این پاسخ آموزشی است، نه توصیه معاملاتی."
            bot.send_message(m.chat.id, answer_text, reply_markup=mk)
            audio = synthesize_fa(result['answer'] + '\n' + result['tip'])
            if audio:
                bot.send_audio(m.chat.id, audio, caption='🔊 پاسخ صوتی آموزشی از آرشیو تأییدشده')
        else:
            record_unanswered(t)
            bot.send_message(m.chat.id, '🤖 ' + result['text'] + '\n\n📝 سؤال شما برای تکمیل FAQ و آموزش‌های بعدی قابل بررسی است.')
        return

    if is_grp and is_link(t) and not ensure_admin(uid):
        try: bot.delete_message(m.chat.id, m.message_id)
        except Exception: pass
        WARNS[uid] = WARNS.get(uid, 0) + 1
        if WARNS[uid] <= 2:
            langc = (m.from_user.language_code or 'fa').split('-')[0]
            if langc not in WARN_TXT: langc = 'fa'
            bot.send_message(m.chat.id, WARN_TXT[langc].format(n=WARNS[uid]))
        else:
            try:
                bot.ban_chat_member(m.chat.id, uid)
                block_user(uid)
                bot.send_message(m.chat.id, '⛔ کاربر بن شد و در بلاک‌لیست دائمی قرار گرفت.')
            except Exception: pass
        return

    if t.startswith('/rr'):
        parts = t.split()
        if len(parts) == 4:
            try:
                e, s, tg = float(parts[1]), float(parts[2]), float(parts[3])
                risk, reward = abs(e - s), abs(tg - e)
                rr = reward / risk if risk else 0
                bot.reply_to(m, f"🧮 <b>ماشین‌حساب R:R</b>\n🎯 ورود: {e}\n🛡️ استاپ: {s} (ریسک: {risk:g})\n🏆 تارگت: {tg} (پاداش: {reward:g})\n💎 R:R = 1:{rr:.2f}\n" + ('✅ عالی (۲ به بالا)' if rr >= 2 else '⚠️ زیر ۲ — محتاط باشید'))
            except Exception:
                bot.reply_to(m, 'فرمت: /rr ورود استاپ تارگت')
        else:
            bot.reply_to(m, 'فرمت: /rr ورود استاپ تارگت')
        return

    if t.startswith('/lot'):
        parts = t.split()
        if len(parts) == 4:
            try:
                bal, risk, pips = float(parts[1]), float(parts[2]), float(parts[3])
                risk_amt = bal * risk / 100
                lots = risk_amt / (pips * 10) if pips else 0
                bot.reply_to(m, f"🧮 <b>ماشین‌حساب حجم</b>\n💵 بالانس: ${bal:g}\n⚠️ ریسک: {risk:g}% = ${risk_amt:.2f}\n🛡️ استاپ: {pips:g} پیپ\n💎 حجم پیشنهادی: {lots:.2f} لات استاندارد")
            except Exception:
                bot.reply_to(m, 'فرمت: /lot بالانس ریسک% پیپ')
        else:
            bot.reply_to(m, 'فرمت: /lot بالانس ریسک% پیپ')
        return

    if t.startswith('/usdt') and ensure_admin(uid):
        try:
            p = int(float(t.split()[1]))
            save_usdt_cache(p, 'مدیریت')
            bot.reply_to(m, f"✅ قیمت تتر: {p:,}")
        except Exception:
            bot.reply_to(m, '/usdt 105000')
        return

    if t.startswith('/block') and ensure_admin(uid):
        try:
            bid = int(t.split()[1])
            block_user(bid)
            bot.reply_to(m, f'✅ کاربر {bid} به بلاک‌لیست اضافه شد.')
        except Exception:
            bot.reply_to(m, '/block 123456789')
        return

    if t.startswith('/unblock') and ensure_admin(uid):
        try:
            bid = int(t.split()[1])
            BLOCKLIST.discard(bid)
            save_blocklist()
            bot.reply_to(m, f'✅ کاربر {bid} از بلاک‌لیست حذف شد.')
        except Exception:
            bot.reply_to(m, '/unblock 123456789')
        return

    if t.startswith('/blocklist') and ensure_admin(uid):
        if not BLOCKLIST:
            bot.reply_to(m, '📭 بلاک‌لیست خالی است.')
        else:
            bot.reply_to(m, f'⛔ بلاک‌لیست ({len(BLOCKLIST)} نفر):\n' + '\n'.join(str(x) for x in list(BLOCKLIST)[:20]))
        return

    if not is_grp and any(x in t for x in ['youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com']):
        handle_download(m, t.split()[0])
        return

    if t.startswith('/trade') and ensure_admin(uid):
        parts = t.split()
        if len(parts) == 4:
            try:
                e, s, tg = float(parts[1]), float(parts[2]), float(parts[3])
                rr = round(abs(tg-e)/abs(e-s), 2) if abs(e-s) else 0
                tid = len(TRADES) + 1
                TRADES.append({'id': tid, 'user': uid, 'entry': e, 'stop': s, 'target': tg, 'rr': rr, 'date': tehran_now().strftime('%Y-%m-%d'), 'result': None})
                save_trades()
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton('✅ TP', callback_data=f'w{tid}'), types.InlineKeyboardButton('❌ SL', callback_data=f'l{tid}'))
                bot.reply_to(m, f"📊 <b>#{tid}</b> | R:R={rr}", reply_markup=mk)
            except Exception:
                bot.reply_to(m, '/trade ورود استاپ تارگت')
        return

def notifier():
    last = ''
    last_quote_day = ''
    last_news_day = ''
    last_cal_day = ''
    while True:
        try:
            now = tehran_now()
            key = now.strftime('%Y-%m-%d %H:%M')
            if key != last:
                last = key
                hm = (now.hour, now.minute)
                wd = now.weekday()
                weekend = wd >= 5
                if not weekend:
                    if hm == (8, 0) and now.strftime('%Y-%m-%d') != last_cal_day:
                        last_cal_day = now.strftime('%Y-%m-%d')
                        n = news_today()
                        if n: post_all(n)
                    if hm == (9, 0) and now.strftime('%Y-%m-%d') != last_quote_day:
                        last_quote_day = now.strftime('%Y-%m-%d')
                        q = QUOTES[now.timetuple().tm_yday % len(QUOTES)]
                        post_all(f"🌟 <b>جملهٔ روز:</b>\n💡 {q}")
                    if hm == (9, 30): post_all('🟠 سشن فرانکفورت باز شد؛ اولین موج نقدینگی اروپا در راه است.')
                    if hm == (10, 30): post_all('🟢 سشن لندن باز شد؛ بیشترین حجم معاملات روز اینجاست.')
                    if hm == (15, 0) and now.strftime('%Y-%m-%d') != last_news_day:
                        last_news_day = now.strftime('%Y-%m-%d')
                        msg = '📰 قبل از نیویورک: اخبار را چک کنید.'
                        if wd == 4 and now.day <= 7:
                            msg += '\n⚠️ <b>NFP!</b>'
                        post_all(msg)
                    if hm == (15, 30): post_all('🔵 سشن نیویورک باز شد؛ هم‌پوشانی لندن+نیویورک = بیشترین نوسان روز.')
                    if hm == (19, 30): post_all('🔴 سشن لندن بسته شد؛ معامله‌گران اروپا از بازار خارج شدند.')
        except Exception: pass
        _t.sleep(20)

threading.Thread(target=notifier, daemon=True).start()

if __name__ == '__main__':
    print('🚀 Bot started')
    while True:
        try:
            bot.infinity_polling(allowed_updates=['message', 'callback_query', 'chat_member'])
        except Exception:
            _t.sleep(5)
