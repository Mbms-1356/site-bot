import os, json, threading, time as _t, re, urllib.request, urllib.parse, ssl
from datetime import datetime, timedelta, timezone
import telebot
from telebot import types
import yt_dlp
import requests

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
ARTICLE = SITE + 'lit-liquidity.html'
CHANNEL = 'https://t.me/forexin_turkaslanifree'
CHANNEL_POST = '@forexin_turkaslanifree'
GROUP = 'https://t.me/forexinturkaslanilitcommuniti'
MAINBOT = '@TurkaslaniSiteBot'
FREE_CHANNEL = '@forexin_turkaslanifree'
BASE_CHANNEL = '@Forexin_Turkaslani_Base'
INSTA = 'https://www.instagram.com/forexin.turkaslani'
YOUTUBE = 'https://www.youtube.com/@Forexin.turkaslani'
QUIZ = SITE + 'quiz.html'
DATA_FILE = 'trades.json'
ADMIN_FILE = 'admin.json'
GROUP_FILE = 'group_id.txt'
INVITE_FILE = 'invites.json'
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

INVITES = {}
try:
    with open(INVITE_FILE) as f: INVITES = json.load(f)
except Exception: pass

def save_invites():
    try:
        with open(INVITE_FILE, 'w') as f: json.dump(INVITES, f)
    except Exception: pass

def save_group(gid):
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
    try:
        with open(DATA_FILE, 'w') as f: json.dump(TRADES, f)
    except Exception: pass

def ensure_admin(uid):
    global ADMIN
    if ADMIN is None:
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

GLOSS = {
    'lat': 'لات: واحد حجم معامله؛ ۱ لات = ۱۰۰۰ واحد ارز پایه.',
    'pip': 'پیپ: کوچک‌ترین واحد تغییر قیمت (معمولاً رقم چهارم اعشار).',
    'stop': 'استاپ: سفارش محدودکنندهٔ ضرر (Stop Loss).',
    'ahrom': 'اهرم: سرمایهٔ قرضی از بروکر برای بزرگ‌تر کردن معامله.',
    'spread': 'اسپرد: فاصلهٔ بین قیمت خرید و فروش.',
    'target': 'تارگت: هدف سود معامله.',
    'session': 'سشن: بازهٔ زمانی فعالیت بازار (لندن/نیویورک).',
    'candle': 'کندل: نمایش قیمت باز/بسته/بالا/پایین در یک بازه.',
    'pattern': 'پترن: الگوی تکرارشوندهٔ قیمتی در چارت.',
    'lit': 'LIT: استراتژی اختصاصی آکادمی فارکسین ترک اصلانی.',
    'vip': 'VIP: کانال ویژهٔ سیگنال‌های آکادمی.'
}

BASE_GUIDE = '''📌 راهنمای کامل ورود به کانال بیس (آکادمی)

🎯 کانال بیس: @Forexin_Turkaslani_Base
آکادمی عملی: آموزش استراتژی LIT، کار با صرافی و بروکر، مدیریت سرمایه.

🔑 روش ورود (تنها روش):
1️⃣ ربات رسمی: @TurkaslaniSiteBot و بنویسید /start
2️⃣ دکمه «🎟️ لینک دعوت» را بزنید؛ لینک اختصاصی شما نمایش داده می‌شود.
3️⃣ لینک‌تان را برای ۲ دوست بفرستید.
4️⃣ دوست‌ها با لینک شما عضو کانال رایگان شوند؛ هر عضو موفق = ۱ دعوت.
5️⃣ بعد از ۲ دعوت واقعی، لینک ورود به کانال بیس خودکار ارسال می‌شود. 🎉

 تیم Forexin Turkaslani'''

WELCOME_PRIV = 'سلام! 👋\nمن دستیار فارکسین ترک اصلانی هستم.\n<i>📊 ژورنال معاملاتی | 💰 قیمت لحظه‌ای | 🎬 دانلودر | 📚 آموزش</i>'

WELCOME_GROUP = '''سلام {first} عزیز! 🌟
به «LIT Community Forexin_Turkaslani» خوش آمدید.

کانال‌های ما:
1️⃣  کانال سیگنال و لایو (رایگان)
@forexin_turkaslanifree
2️⃣  کانال آموزش آکادمی
@Forexin_Turkaslani_Base
3️⃣  همین گروه (LIT Community)
4️⃣ ▶️ یوتیوب
youtube.com/@Forexin.turkaslani

⚠️ تمام مطالب صرفاً آموزشی‌اند.
🚫 ارسال لینک و تبلیغ ممنوع (۲ اخطار = مسدودیت).
با آرزوی سودهای پایدار 📈'''

FLAGS = {'USD': '🇺', 'EUR': '🇺', 'GBP': '🇬🇧', 'JPY': '🇯🇵', 'CNY': '🇨', 'AUD': '🇺', 'CAD': '🇨🇦', 'CHF': '🇨🇭', 'NZD': '🇳'}

def build_menu():
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(types.InlineKeyboardButton('🎟️ VIP', callback_data='code'), types.InlineKeyboardButton('❓ سوالات', callback_data='faq'))
    m.add(types.InlineKeyboardButton('💰 طلا', callback_data='gold'), types.InlineKeyboardButton('🇮🇷 تتر', callback_data='usdt'))
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
    m.add(types.InlineKeyboardButton('🎬 دانلود', callback_data='dl'), types.InlineKeyboardButton('📜 قوانین', callback_data='rules'))
    m.add(types.InlineKeyboardButton('🧠 آزمون', url=QUIZ), types.InlineKeyboardButton('📚 مقاله', url=ARTICLE))
    m.add(types.InlineKeyboardButton('🎁 لینک‌ها', callback_data='inv'), types.InlineKeyboardButton('🎟️ لینک دعوت', callback_data='invite'))
    m.add(types.InlineKeyboardButton('🚀 شروع', callback_data='st'))
    return m

def fetch_json(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    return json.load(urllib.request.urlopen(req, timeout=8, context=ctx))

def tehran_now():
    return datetime.now(timezone(timedelta(hours=3, minutes=30)))

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
            return f"🥇 <b>انس طلا:</b> خطا در دریافت\n<code>{str(e2)[:80]}</code>"

def get_usdt_only():
    results = []
    errs = []
    def clean(x): return int(float(str(x).replace(',', '')))
    def add(name, fn):
        try:
            p = fn()
            if p and p > 1000:
                results.append((name, p))
        except Exception as e:
            errs.append(f"{name}: {str(e)[:40]}")
    def tgju(market, sym):
        d = fetch_json('https://api.tgju.org/v1/market/indicator/summary-price-data?market=' + market + '&symbol=' + sym)
        data = d.get('data')
        item = data[0] if isinstance(data, list) and data else (list(data.values())[0] if isinstance(data, dict) and data else d)
        for k in ('price', 'current', 'last', 'value', 'close'):
            if isinstance(item, dict) and item.get(k):
                return clean(item[k])
        raise Exception('parse')
    add('دلار', lambda: tgju('fx', 'usd'))
    add('تتر', lambda: tgju('crypto', 'usdt'))
    add('نوبیتکس', lambda: clean(fetch_json('https://api.nobitex.ir/market/stats?srcCurrency=usdt&dstCurrency=rls')['stats']['usdt-rls']['latest']) // 10)
    def bonbast():
        d = fetch_json('https://bonbast.com/json')
        src = d.get('usdt') or d.get('usd')
        return clean(src['sell'])
    add('بن‌بست', bonbast)
    def tabdeal():
        for url in ('https://api1.tabdeal.org/r/api/v1/ticker?symbol=USDTIRT', 'https://api1.tabdeal.org/r/api/v1/public/ticker?symbol=USDTIRT'):
            try:
                d = fetch_json(url)
                return clean(d['data'].get('last') or d['data'].get('lastPrice'))
            except Exception:
                continue
        raise Exception('tabdeal')
    add('تبدیل', tabdeal)
    if results:
        lines = '\n'.join([f"🏦 {n}: {p:,} تومان" for n, p in results])
        avg = sum(p for _, p in results) // len(results)
        return f"🇮🇷 <b>قیمت لحظه‌ای تتر:</b>\n{lines}\n📊 میانگین: {avg:,} تومان\n<i>🤖 Forexin Bot</i>"
    return '🇮🇷 <b>قیمت تتر:</b> خطا در دریافت\n<code>' + ' | '.join(errs)[:300] + '</code>'

def news_today():
    try:
        d = fetch_json('https://nfs.faireconomy.media/ff_calendar_thisweek.json')
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
    except Exception: pass
    return None

def tiktok_dl(u):
    q = urllib.parse.quote(u, safe='')
    try:
        r = requests.get('https://www.tikwm.com/api/?hd=1&url=' + q, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        res = r.json()
        if res.get('code') == 0:
            return res['data']
    except Exception: pass
    try:
        r = requests.post('https://tikwm.com/api/', data={'url': u, 'hd': 1}, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        res = r.json()
        if res.get('code') == 0:
            return res['data']
    except Exception: pass
    try:
        r = requests.get('https://api.tiklydown.eu.org/api/download?url=' + q, timeout=20)
        d = r.json()
        v = d.get('video')
        if v and v.get('playback'):
            return {'play': v['playback'], 'hdplay': v['playback'], 'title': d.get('title', 'TikTok')}
    except Exception: pass
    raise Exception('tiktok all sources failed')

def handle_download(m, url):
    wait = bot.send_message(m.chat.id, '⏳ <b>در حال دانلود... صبر کنید!</b>')
    def job():
        try:
            if 'tiktok.com' in url:
                vd = tiktok_dl(url)
                vurl = vd.get('hdplay') or vd.get('play')
                if vurl and not vurl.startswith('http'):
                    vurl = 'https://tikwm.com' + vurl
                data = requests.get(vurl, timeout=30, headers={'User-Agent': 'Mozilla/5.0'}).content
                title = (vd.get('title') or 'TikTok Video')[:50]
            else:
                opts = {
                    'outtmpl': os.path.join(DL_DIR, '%(id)s.%(ext)s'),
                    'format': 'best[height<=720]',
                    'quiet': True, 'no_warnings': True,
                    'socket_timeout': 30, 'retries': 3,
                    'extractor_args': {'youtube': {'player_client': ['android', 'ios', 'tv']}},
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
            low = err.lower()
            if 'instagram.com' in url and ('login' in low or 'sign in' in low):
                msg = '❌ اینستاگرام نیاز به لاگین دارد. فقط لینک Reels عمومی بفرستید.'
            elif 'youtube.com' in url or 'youtu.be' in url:
                msg = f"❌ یوتیوب موقتاً سرور را مسدود کرد (بررسی ربات).\n💡 چند دقیقه بعد دوباره امتحان کنید یا از <code>ssyoutube.com</code> استفاده کنید.\n<code>{err[:80]}</code>"
            else:
                msg = f"❌ دانلود ناموفق بود.\n💡 تیک‌تاک: <code>snaptik.app</code> | اینستا: <code>snapinsta.app</code>\n<code>{err[:100]}</code>"
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
        if d == 'st':
            if c.message.chat.type in ('group', 'supergroup'):
                bot.send_message(chat, WELCOME_PRIV, reply_markup=group_menu())
            else:
                bot.send_message(chat, WELCOME_PRIV, reply_markup=build_menu())
        elif d == 'inv':
            bot.send_message(chat, f"🎁 <b>لینک‌های مفید:</b>\n🤖 ربات اصلی: {MAINBOT}\n📢 کانال سیگنال: @forexin_turkaslanifree\n🎓 کانال بیس: @Forexin_Turkaslani_Base\n💬 گروه: @forexinturkaslanilitcommuniti")
        elif d == 'gold':
            bot.send_message(chat, get_gold_only())
        elif d == 'usdt':
            bot.send_message(chat, get_usdt_only())
        elif d == 'dl':
            bot.send_message(chat, '🎬 <b>لینک ویدیو را بفرستید:</b>\n(یوتیوب، اینستاگرام، تیک‌تاک)')
        elif d == 'rules':
            bot.send_message(chat, '📜 <b>قوانین گروه:</b>\n۱. احترام متقابل\n۲. عدم تبلیغ و اسپم\n۳. فقط مباحث ترید و آموزشی\n۴. ارسال لینک = حذف + اخطار (۲ اخطار = مسدودیت)')
        elif d == 'code':
            bot.send_message(chat, '🎟️ <b>کد VIP خود را وارد کنید:</b>')
        elif d == 'faq':
            mk = types.InlineKeyboardMarkup(row_width=2)
            mk.add(types.InlineKeyboardButton('لات', callback_data='gloss_lat'), types.InlineKeyboardButton('پیپ', callback_data='gloss_pip'))
            mk.add(types.InlineKeyboardButton('استاپ', callback_data='gloss_stop'), types.InlineKeyboardButton('اهرم', callback_data='gloss_ahrom'))
            mk.add(types.InlineKeyboardButton('اسپرد', callback_data='gloss_spread'), types.InlineKeyboardButton('تارگت', callback_data='gloss_target'))
            mk.add(types.InlineKeyboardButton('سشن', callback_data='gloss_session'), types.InlineKeyboardButton('کندل', callback_data='gloss_candle'))
            mk.add(types.InlineKeyboardButton('پترن', callback_data='gloss_pattern'), types.InlineKeyboardButton('LIT', callback_data='gloss_lit'))
            mk.add(types.InlineKeyboardButton('VIP', callback_data='gloss_vip'))
            bot.send_message(chat, '❓ <b>یکی را انتخاب کن:</b>', reply_markup=mk)
        elif d.startswith('gloss_'):
            bot.send_message(chat, GLOSS.get(d[6:], '❓'))
        elif d == 'fb':
            bot.send_message(chat, '💬 <b>بازخورد خود را بنویسید تا به مدیریت برسد:</b>')
        elif d == 'base':
            bot.send_message(chat, BASE_GUIDE)
        elif d == 'invite':
            rec = INVITES.setdefault(str(uid), {'count': 0, 'ok': False})
            if rec.get('ok'):
                bot.send_message(chat, '✅ دسترسی شما فعال است!\n🎓 کانال بیس: @Forexin_Turkaslani_Base')
            else:
                if not rec.get('link'):
                    try:
                        rec['link'] = bot.create_chat_invite_link(FREE_CHANNEL, name=str(uid)).invite_link
                        save_invites()
                    except Exception as e:
                        bot.send_message(chat, f"❌ ساخت لینک ناموفق بود؛ ربات باید در کانال ادمین باشد.\n<code>{str(e)[:80]}</code>")
                        bot.answer_callback_query(c.id)
                        return
                bot.send_message(chat, f"🎁 <b>لینک دعوت شخصی شما:</b>\n<code>{rec['link']}</code>\n\nآن را برای ۲ دوست بفرستید. هر عضو موفق = ۱ دعوت.\n📊 فعلی: {rec.get('count', 0)} از ۲")
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

@bot.chat_member_handler(func=lambda cm: True)
def on_member(cm):
    try:
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
                    bot.send_message(int(uid), f"🎉 دسترسی باز شد!\n🎓 لینک ورود به کانال بیس:\n{bl}")
                else:
                    bot.send_message(int(uid), f"✅ یک نفر با لینک شما عضو شد! ({rec['count']} از ۲)")
    except Exception: pass

@bot.message_handler(func=lambda m: True)
def txt(m):
    uid = m.from_user.id
    t = m.text.strip()
    is_grp = m.chat.type in ('group', 'supergroup')
    if is_grp:
        save_group(m.chat.id)

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
            bot.infinity_polling(allowed_updates=['message', 'callback_query', 'chat_member'])
        except Exception:
            _t.sleep(5)
