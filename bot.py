import os, json, threading, time as _t, re, urllib.request, ssl
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import telebot
from telebot import types
import yt_dlp
import requests
from challenge_engine import get_daily, answer as answer_challenge, profile as challenge_profile, report as challenge_report
from assistant_engine import answer_question
from assistant_tts import synthesize_fa

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
if not TOKEN:
    try:
        with open(os.path.join(os.path.expanduser('~'), 'token.txt')) as f:
            TOKEN = f.read().strip()
    except Exception:
        TOKEN = ''
if not TOKEN or ':' not in TOKEN:
    raise ValueError('Token not found!')

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

SITE = 'https://mbms-1356.github.io/forexin-site-/'
CHANNEL = 'https://t.me/forexin_turkaslanifree'
CHANNEL_POST = '@forexin_turkaslanifree'
FREE_CHANNEL = '@forexin_turkaslanifree'
GUIDE_AUDIO = 'guide_fa.wav'
GUIDE_AUDIO = 'guide_fa.wav'
GROUP = 'https://t.me/forexinturkaslanilitcommuniti'
MAINBOT = 'https://t.me/TurkaslaniFx_bot'
INSTA = 'https://www.instagram.com/forexin.turkaslani'
YOUTUBE = 'https://www.youtube.com/@Forexin.turkaslani'
QUIZ = SITE + 'quiz.html'
DATA_FILE = 'trades.json'
ADMIN_FILE = 'admin.json'
GROUP_FILE = 'group_id.txt'
DL_DIR = 'dl'
os.makedirs(DL_DIR, exist_ok=True)

ADMIN = None
try:
    with open(ADMIN_FILE) as f: ADMIN = json.load(f)['id']
except Exception: pass

GROUP_ID = None
try:
    with open(GROUP_FILE) as f: GROUP_ID = int(f.read().strip())
except Exception: pass

def save_group(gid):
    global GROUP_ID
    if GROUP_ID is None:
        GROUP_ID = gid
        try:
            with open(GROUP_FILE, 'w') as f: f.write(str(gid))
        except Exception: pass

USERS, WARNS = set(), {}
ASSISTANT_USERS = set()
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
    try:
        with open(DATA_FILE, 'w') as f: json.dump(TRADES, f)
    except Exception: pass

def ensure_admin(uid):
    global ADMIN
    if ADMIN is None and uid == 227491135:
        ADMIN = uid
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

MENU = ['🎟️ VIP', '❓ سوالات', '💰 طلا', '🇮🇷 تتر', '🎬 دانلود', '📊 معامله', '📈 گزارش', '💬 بازخورد', '🧠 آزمون', '🌐 سایت', '📢 کانال', '📷 اینستا', '▶️ یوتیوب', '🎁 لینک‌ها', '🚀 شروع']

WELCOME_PRIV = 'سلام! 👋\nمن دستیار فارکسین ترک اصلانی هستم.\n<i>📊 ژورنال معاملاتی | 💰 قیمت لحظه‌ای | 🎬 دانلودر</i>'

WELCOME_GROUP = '''سلام {first} عزیز! 🌟
به «LIT Community Forexin_Turkaslani» خوش آمدید.

کانال‌های ما:
1️⃣  کانال سیگنال و لایو (رایگان)
@forexin_turkaslanifree
2️⃣ 🎓 کانال آموزش آکادمی
@Forexin_Turkaslani_Base
3️⃣ 💬 همین گروه (LIT Community)
4️⃣ ▶️ یوتیوب
youtube.com/@Forexin.turkaslani

⚠️ تمام مطالب صرفاً آموزشی‌اند.
🚫 ارسال لینک و تبلیغ ممنوع (۲ اخطار = مسدودیت).
با آرزوی سودهای پایدار 📈'''

FLAGS = {'USD': '🇺🇸', 'EUR': '🇪🇺', 'GBP': '🇬🇧', 'JPY': '🇯🇵', 'CNY': '🇨🇳', 'AUD': '🇦🇺', 'CAD': '🇨🇦', 'CHF': '🇨🇭', 'NZD': '🇳🇿'}

def build_menu():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton(MENU[0], callback_data='code'), types.InlineKeyboardButton(MENU[1], callback_data='faq'))
    m.add(types.InlineKeyboardButton(MENU[2], callback_data='gold'), types.InlineKeyboardButton(MENU[3], callback_data='usdt'))
    m.add(types.InlineKeyboardButton('📅 اخبار مهم امروز', callback_data='news'))
    m.add(types.InlineKeyboardButton('🕒 وضعیت سشن‌ها', callback_data='sessions'))
    m.add(types.InlineKeyboardButton('🎯 چالش روز', callback_data='challenge'))
    m.add(types.InlineKeyboardButton('📊 پیشرفت من', callback_data='challenge_progress'))
    m.add(types.InlineKeyboardButton('🤖 دستیار آموزشی', callback_data='assistant'))
    m.add(types.InlineKeyboardButton('📖 راهنمای استفاده', callback_data='guide'), types.InlineKeyboardButton('🤖 معرفی سیستم', callback_data='about'))
    m.add(types.InlineKeyboardButton('🔊 راهنمای صوتی', callback_data='guide_audio'))
    m.add(types.InlineKeyboardButton(MENU[4], callback_data='dl'), types.InlineKeyboardButton(MENU[5], callback_data='tr'))
    m.add(types.InlineKeyboardButton(MENU[6], callback_data='rp'), types.InlineKeyboardButton(MENU[7], callback_data='fb'))
    m.add(types.InlineKeyboardButton(MENU[8], url=QUIZ), types.InlineKeyboardButton(MENU[9], url=SITE))
    m.add(types.InlineKeyboardButton(MENU[10], url=CHANNEL), types.InlineKeyboardButton(MENU[11], url=INSTA))
    m.add(types.InlineKeyboardButton(MENU[12], url=YOUTUBE), types.InlineKeyboardButton(MENU[13], callback_data='inv'))
    m.add(types.InlineKeyboardButton(MENU[14], callback_data='st'))
    return m

def group_menu():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton('💰 طلا', callback_data='gold'), types.InlineKeyboardButton('🇮🇷 تتر', callback_data='usdt'))
    m.add(types.InlineKeyboardButton('📅 اخبار مهم امروز', callback_data='news'))
    m.add(types.InlineKeyboardButton('🕒 وضعیت سشن‌ها', callback_data='sessions'))
    m.add(types.InlineKeyboardButton('🎯 چالش روز', callback_data='challenge'))
    m.add(types.InlineKeyboardButton('📊 پیشرفت من', callback_data='challenge_progress'))
    m.add(types.InlineKeyboardButton('📖 راهنمای استفاده', callback_data='guide'), types.InlineKeyboardButton('🤖 معرفی سیستم', callback_data='about'))
    m.add(types.InlineKeyboardButton('📜 قوانین', callback_data='rules'), types.InlineKeyboardButton('🧠 آزمون', url=QUIZ))
    m.add(types.InlineKeyboardButton('🎁 لینک‌ها', callback_data='inv'), types.InlineKeyboardButton('🚀 شروع', callback_data='st'))
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
    return f"📖 <b>راهنمای استفاده از Forexin</b>\n\n۱. ابتدا عضو کانال فری شوید.\n۲. دکمه «بررسی عضویت» را بزنید.\n۳. از منو قیمت طلا و تتر، اخبار اقتصادی، وضعیت سشن‌ها و چالش روز را استفاده کنید.\n۴. از «پیشرفت من» امتیاز، streak و نشان‌های آموزشی خود را ببینید.\n۵. برای آموزش بیشتر از کانال آکادمی، گروه و یوتیوب استفاده کنید.\n\n🔗 کانال فری: {CHANNEL}\n🎓 آکادمی: @Forexin_Turkaslani_Base\n💬 گروه: {GROUP}\n▶️ یوتیوب: {YOUTUBE}\n\n⚠️ همه مطالب آموزشی‌اند و توصیه خرید یا فروش نیستند."

def about_text():
    return f"🤖 <b>سیستم Forexin</b>\n\nربات سیگنال برای قیمت‌ها، اخبار، سشن‌ها و اطلاع‌رسانی آموزشی طراحی شده است. ربات سایت برای آموزش، دانلود، مقاله و مسیر یادگیری استفاده می‌شود.\n\n📢 پیام‌های خودکار سشن‌ها فقط یک‌بار در کانال فری منتشر می‌شوند تا پیام تکراری ارسال نشود.\n\n{CHANNEL}\n{MAINBOT}"

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

def fetch_json(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    return json.load(urllib.request.urlopen(req, timeout=10, context=ctx))

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

def get_prices():
    gold = 'نامشخص'
    try:
        d = fetch_json('https://api.gold-api.com/price/XAU')
        gold = f"{d['price']}"
    except Exception:
        try:
            d = fetch_json('https://data-asg.goldprice.org/dbXRates/USD')
            gold = f"{round(d['items'][0]['xau_price'], 2)}"
        except Exception: pass

    usdt = 'نامشخص'
    try:
        d = fetch_json('https://api.tabdeal.org/api/v1/public/ticker?symbol=USDTIRT')
        if d.get('status') == 'success':
            usdt = f"{int(float(d['data']['last'])):,}"
    except Exception:
        try:
            d = fetch_json('https://api.nobitex.ir/market/stats?srcCurrency=usdt&dstCurrency=rls')
            usdt = f"{int(d['stats']['usdt-rls']['latest']) // 10:,}"
        except Exception:
            try:
                d = fetch_json('https://api.wallex.ir/v1/markets/ticker?symbol=USDTIRT')
                usdt = f"{int(float(d['data']['latest']['lastPrice'])):,}"
            except Exception: pass

    return f"📊 <b>قیمت‌های لحظه‌ای:</b>\n\n🥇 <b>انس طلا:</b> ${gold}\n🇮🇷 <b>تتر:</b> {usdt} تومان\n\n<i>🔄 آپدیت خودکار از صرافی‌های ایرانی</i>"

def get_gold_only():
    gold = 'نامشخص'
    try:
        d = fetch_json('https://api.gold-api.com/price/XAU')
        gold = f"{d['price']}"
    except Exception:
        try:
            d = fetch_json('https://data-asg.goldprice.org/dbXRates/USD')
            gold = f"{round(d['items'][0]['xau_price'], 2)}"
        except Exception:
            pass
    return f"🥇 <b>قیمت لحظه‌ای انس جهانی طلا:</b> ${gold}"

def get_usdt_only():
    usdt = 'نامشخص'
    try:
        d = fetch_json('https://api.tabdeal.org/api/v1/public/ticker?symbol=USDTIRT')
        if d.get('status') == 'success':
            usdt = f"{int(float(d['data']['last'])):,}"
    except Exception:
        try:
            d = fetch_json('https://api.nobitex.ir/market/stats?srcCurrency=usdt&dstCurrency=rls')
            usdt = f"{int(d['stats']['usdt-rls']['latest']) // 10:,}"
        except Exception:
            try:
                d = fetch_json('https://api.wallex.ir/v1/markets/ticker?symbol=USDTIRT')
                usdt = f"{int(float(d['data']['latest']['lastPrice'])):,}"
            except Exception:
                pass
    return (
        f"🇮🇷 <b>قیمت لحظه‌ای تتر:</b> {usdt} تومان\n\n"
        "🔗 <b>مشاهده قیمت در صرافی‌های ایرانی:</b>\n"
        '🥇 <a href="https://nobitex.ir/price/usdt/">نوبیتکس</a>\n'
        '🥈 <a href="https://tabdeal.org/usdt-price">تبدیل</a>\n'
        '🥉 <a href="https://www.ompfinex.com/markets/usdt-price">اُم‌فاینکس</a>'
    )

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
            if ev.get('impact') != 'High':
                continue
            try:
                dt = datetime.fromisoformat(ev['date'].replace('Z', '+00:00'))
            except Exception:
                continue
            dt_ir = dt.astimezone(timezone(timedelta(hours=3, minutes=30)))
            if dt_ir.date() != now.date():
                continue
            flag = FLAGS.get(ev.get('country', ''), '🌐')
            lines.append(f"{flag} <b>{ev['title']}</b>\n⏰ ساعت {dt_ir.strftime('%H:%M')} به وقت ایران")
            if len(lines) >= 8:
                break
        if lines:
            return "📅 <b>تقویم اقتصادی امروز (اخبار پرقدرت):</b>\n\n" + "\n\n".join(lines) + "\n\n<i>منبع: ForexFactory | ساعت‌ها به وقت ایران</i>"
    except Exception:
        return '⚠️ منبع تقویم اقتصادی موقتاً در دسترس نیست؛ لطفاً چند دقیقه بعد دوباره امتحان کنید.'
    return '📅 امروز خبر پرقدرتی در تقویم اقتصادی وجود ندارد.'

def handle_download(m, url):
    wait = bot.send_message(m.chat.id, '⏳ <b>در حال دانلود... صبر کنید!</b>')
    def job():
        try:
            if 'tiktok.com' in url:
                r = requests.post('https://tikwm.com/api/', data={'url': url, 'hd': 1}, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
                res = r.json()
                if res.get('code') != 0:
                    raise Exception('tikwm error')
                vd = res['data']
                vurl = vd.get('hdplay') or vd.get('play')
                if vurl and not vurl.startswith('http'):
                    vurl = 'https://tikwm.com' + vurl
                data = requests.get(vurl, timeout=30).content
                title = vd.get('title', 'TikTok Video')[:50]
            else:
                opts = {
                    'outtmpl': os.path.join(DL_DIR, '%(id)s.%(ext)s'),
                    'format': 'best[height<=720]',
                    'quiet': True, 'no_warnings': True,
                    'socket_timeout': 30, 'retries': 3,
                    'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'}
                }
                with yt_dlp.YoutubeDL(opts) as y:
                    info = y.extract_info(url, download=True)
                    fn = y.prepare_filename(info)
                with open(fn, 'rb') as f:
                    data = f.read()
                title = info.get('title', 'Video')[:50]
                try: os.remove(fn)
                except Exception: pass

            if len(data) > 48*1024*1024:
                bot.send_message(m.chat.id, '⚠️ فایل سنگین‌تر از ۴۸MB است و قابل ارسال نیست.')
            else:
                fp = os.path.join(DL_DIR, 'send.mp4')
                with open(fp, 'wb') as f:
                    f.write(data)
                with open(fp, 'rb') as f:
                    bot.send_video(m.chat.id, f, caption=f"<b>{title}</b>\n<i>🤖 Forexin Downloader</i>", supports_streaming=True)
                try: os.remove(fp)
                except Exception: pass
            try: bot.delete_message(m.chat.id, wait.message_id)
            except Exception: pass
        except Exception as e:
            err = str(e)
            if 'login' in err.lower() or 'sign in' in err.lower():
                msg = '❌ اینستاگرام نیاز به لاگین دارد. فقط لینک Reels عمومی بفرستید.'
            else:
                msg = f"❌ دانلود ناموفق بود.\n💡 لینک تیک‌تاک را در <code>snaptik.app</code> و اینستا را در <code>snapinsta.app</code> امتحان کنید.\n<code>{err[:100]}</code>"
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

@bot.message_handler(content_types=['new_chat_members'])
def new_member(m):
    if m.chat.type in ('group', 'supergroup'):
        save_group(m.chat.id)
    for u in m.new_chat_members:
        if not u.is_bot:
            try:
                bot.send_message(m.chat.id, WELCOME_GROUP.format(first=u.first_name or 'دوست عزیز'), reply_markup=group_menu())
            except Exception: pass

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
    bot.send_message(uid, WELCOME_PRIV, reply_markup=build_menu())

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
        if d == 'st':
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
            bot.send_message(chat, f"🎁 <b>لینک‌های مفید:</b>\n🤖 ربات اصلی: {MAINBOT}\n💬 گروه: {GROUP}\n📢 کانال: {CHANNEL}")
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
            bot.send_message(chat, '📜 <b>قوانین گروه:</b>\n۱. احترام متقابل\n۲. عدم تبلیغ و اسپم\n۳. فقط مباحث ترید و آموزشی\n۴. ارسال لینک = حذف + اخطار (۲ اخطار = مسدودیت)')
        elif d == 'code':
            bot.send_message(chat, '🎟️ <b>کد VIP خود را وارد کنید:</b>')
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
        elif d == 'fb':
            bot.send_message(chat, '💬 <b>بازخورد خود را بنویسید تا به مدیریت برسد:</b>')
        elif d == 'tr':
            bot.send_message(chat, '📊 برای ثبت معامله (فقط ادمین):\n/trade ورود استاپ تارگت')
        elif d == 'rp':
            wins = len([x for x in TRADES if x.get('result') == 'win'])
            loss = len([x for x in TRADES if x.get('result') == 'loss'])
            bot.send_message(chat, f"📈 <b>گزارش معاملات:</b>\n✅ برنده: {wins}\n❌ بازنده: {loss}\n📊 کل: {len(TRADES)}")
        elif d.startswith('w') or d.startswith('l'):
            tid = int(d[1:])
            for x in TRADES:
                if x.get('id') == tid:
                    x['result'] = 'win' if d.startswith('w') else 'loss'
            save_trades()
            try: bot.edit_message_reply_markup(chat, c.message.message_id)
            except Exception: pass
            bot.answer_callback_query(c.id, '✅ نتیجه ثبت شد')
            return
    except Exception: pass
    bot.answer_callback_query(c.id)

@bot.message_handler(func=lambda m: True)
def txt(m):
    uid = m.from_user.id
    t = m.text.strip()
    is_grp = m.chat.type in ('group', 'supergroup')
    if is_grp:
        save_group(m.chat.id)

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
            answer_text = f"🤖 <b>پاسخ آموزشی</b>\n🏷 موضوع: {result['category']} | سطح: {result['difficulty']}\n\n{result['answer']}\n\n🛡 <b>نکته:</b> {result['tip']}\n\n⚠️ این پاسخ آموزشی است، نه توصیه معاملاتی."
            bot.send_message(m.chat.id, answer_text, reply_markup=mk)
            audio = synthesize_fa(result['answer'] + '\n' + result['tip'])
            if audio:
                bot.send_audio(m.chat.id, audio, caption='🔊 پاسخ صوتی آموزشی از آرشیو تأییدشده')
        else:
            bot.send_message(m.chat.id, '🤖 ' + result['text'])
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
            try: bot.ban_chat_member(m.chat.id, uid)
            except Exception: pass
            try: bot.send_message(m.chat.id, '⛔ کاربر به دلیل تکرار تبلیغ مسدود شد.')
            except Exception: pass
        return

    if not is_grp and any(x in t for x in ['youtube.com', 'youtu.be', 'instagram.com', 'tiktok.com']):
        handle_download(m, t.split()[0])
        return

    if t.startswith('/trade') and ensure_admin(uid):
        parts = t.split()
        if len(parts) == 4:
            try:
                e, s, tg = float(parts[1]), float(parts[2]), float(parts[3])
                rsk, rwd = abs(e-s), abs(tg-e)
                rr = round(rwd/rsk, 2) if rsk else 0
                tid = len(TRADES) + 1
                TRADES.append({'id': tid, 'user': uid, 'entry': e, 'stop': s, 'target': tg, 'rr': rr, 'date': tehran_now().strftime('%Y-%m-%d'), 'result': None})
                save_trades()
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton('✅ TP', callback_data=f'w{tid}'), types.InlineKeyboardButton('❌ SL', callback_data=f'l{tid}'))
                bot.reply_to(m, f"📊 <b>معامله #{tid}</b>\n🎯 ورود: {e}\n🛡️ استاپ: {s}\n🏆 تارگت: {tg}\n💎 R:R = {rr}", reply_markup=mk)
            except Exception:
                bot.reply_to(m, 'فرمت صحیح: /trade ورود استاپ تارگت')
        return

    if t.startswith('/report') and ensure_admin(uid):
        wins = len([x for x in TRADES if x.get('result') == 'win'])
        loss = len([x for x in TRADES if x.get('result') == 'loss'])
        bot.reply_to(m, f"📈 <b>گزارش:</b>\n✅ {wins} | ❌ {loss}")
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
                if hm == (8, 0) and now.strftime('%Y-%m-%d') != last_cal_day:
                    last_cal_day = now.strftime('%Y-%m-%d')
                    n = news_today()
                    if n:
                        post_all(n)
                    else:
                        post_all('📰 <b>یادآور اخبار اقتصادی:</b>\nتقویم امروز را چک کنید:\nwww.forexfactory.com/calendar')
                if hm == (9, 0) and now.strftime('%Y-%m-%d') != last_quote_day:
                    last_quote_day = now.strftime('%Y-%m-%d')
                    q = QUOTES[now.timetuple().tm_yday % len(QUOTES)]
                    post_all(f"🌟 <b>جملهٔ روز:</b>\n\n💡 {q}\n\n🤖 Forexin Bot")
                if hm == (9, 30):
                    post_all('🟠 <b>سشن فرانکفورت باز شد!</b>')
                if hm == (10, 30):
                    post_all('🟢 <b>سشن لندن باز شد!</b>\nحجم و نوسان واقعی بازار شروع شد.')
                if hm == (15, 0) and now.strftime('%Y-%m-%d') != last_news_day:
                    last_news_day = now.strftime('%Y-%m-%d')
                    msg = '📰 <b>قبل از سشن نیویورک:</b>\nاخبار پرقدرت را چک کنید:\nwww.forexfactory.com/calendar'
                    if now.weekday() == 4 and now.day <= 7:
                        msg += '\n\n⚠️ <b>جمعهٔ اول ماه — روز NFP!</b> نوسان شدید، مراقب باشید!'
                    post_all(msg)
                if hm == (15, 30):
                    post_all('🟢 <b>سشن نیویورک باز شد!</b>')
                if hm == (19, 30):
                    post_all('🔴 <b>سشن لندن بسته شد</b> — نیویورک ادامه دارد.')
        except Exception: pass
        _t.sleep(20)

threading.Thread(target=notifier, daemon=True).start()

if __name__ == '__main__':
    print('🚀 Bot started in polling mode')
    while True:
        try:
            bot.infinity_polling()
        except Exception:
            _t.sleep(5)
