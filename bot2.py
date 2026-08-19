import os, json, threading, time as _t, re, urllib.request, urllib.parse, ssl, html
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
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36'

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
CACHE_FILE = 'usdt_cache.json'
BLOCK_FILE = 'blocklist.json'
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

USDT_CACHE = {}
try:
    with open(CACHE_FILE) as f: USDT_CACHE = json.load(f)
except Exception: pass

BLOCKLIST = set()
try:
    with open(BLOCK_FILE) as f: BLOCKLIST = set(json.load(f))
except Exception: pass

def save_invites():
    try:
        with open(INVITE_FILE, 'w') as f: json.dump(INVITES, f)
    except Exception: pass

def save_usdt_cache(p, src):
    global USDT_CACHE
    USDT_CACHE = {'price': int(p), 'ts': int(_t.time()), 'src': src}
    try:
        with open(CACHE_FILE, 'w') as f: json.dump(USDT_CACHE, f)
    except Exception: pass

def save_blocklist():
    try:
        with open(BLOCK_FILE, 'w') as f: json.dump(list(BLOCKLIST), f)
    except Exception: pass

def block_user(uid):
    BLOCKLIST.add(int(uid))
    save_blocklist()

def is_blocked(uid):
    return int(uid) in BLOCKLIST

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
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    return json.load(urllib.request.urlopen(req, timeout=6, context=ctx))

def fetch_text(url, referer=None):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {'User-Agent': UA}
    if referer: headers['Referer'] = referer
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=10, context=ctx).read().decode('utf-8', 'ignore')

def tehran_now():
    return datetime.now(timezone(timedelta(hours=3, minutes=30)))

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

def gold18_text(p):
    try:
        g = fetch_json('https://api.gold-api.com/price/XAU')
        ounce = float(g['price'])
        return f"\n🥇 طلای ۱۸ عیار: {int(p * ounce / 31.1035 * 0.75):,} تومان/گرم"
    except Exception:
        return ''

def get_usdt_only():
    results = []
    errs = []
    def add(name, fn):
        try:
            p = fn()
            if p and 1000 < p < 10000000:
                results.append((name, p))
        except Exception as e:
            errs.append(f"{name}: {str(e)[:25]}")
    def scrape_tabdeal():
        body = fetch_text('https://tabdeal.org/usdt-price', referer='https://tabdeal.org/')
        for pat in [r'USDT[^0-9]{0,200}?([0-9][0-9,]{4,8})\s*(?:تومان|ریال|IRT|T)',
                    r'تتر[^0-9]{0,200}?([0-9][0-9,]{4,8})\s*(?:تومان|ریال)',
                    r'>([0-9][0-9,]{5,9})<',
                    r'"price"\s*:\s*"?([0-9]+)"?']:
            m = re.search(pat, body, re.S | re.I)
            if m:
                v = clean(m.group(1))
                if 50000 < v < 500000:
                    return v
        raise Exception('parse')
    def scrape_omp():
        body = fetch_text('https://www.ompfinex.com/markets/usdt-price', referer='https://www.ompfinex.com/')
        for pat in [r'>([0-9][0-9,]{5,9})<', r'"price"\s*:\s*"?([0-9]+)"?']:
            m = re.search(pat, body, re.S | re.I)
            if m:
                v = clean(m.group(1))
                if 50000 < v < 500000:
                    return v
        raise Exception('parse')
    add('تبدیل', scrape_tabdeal)
    add('اُم‌فاینکس', scrape_omp)
    try:
        d = requests.post('https://api.tabdeal.org/api/v1/market/ticker?symbol=USDTIRT', headers={'User-Agent': UA}, timeout=6).json()
        p = clean(d.get('data', {}).get('last') or d.get('last') or 0)
        if 50000 < p < 500000:
            results.append(('تبدیلAPI', p))
    except Exception as e:
        errs.append(f"تبدیلAPI: {str(e)[:25]}")
    if results:
        name, p = results[0]
        save_usdt_cache(p, name)
        return f"🇮🇷 <b>قیمت لحظه‌ای بازار ایران:</b>\n🪙 تتر: {p:,} تومان{gold18_text(p)}\n🏦 منبع: {name}\n<i>🤖 Forexin Bot</i>"
    if USDT_CACHE.get('price'):
        age = int(_t.time()) - USDT_CACHE.get('ts', 0)
        if age < 24 * 3600:
            p = USDT_CACHE['price']
            mins = max(1, age // 60)
            return f"🇮🇷 <b>قیمت بازار ایران:</b>\n🪙 تتر: {p:,} تومان{gold18_text(p)}\n🕐 بروزرسانی: {mins} دقیقه پیش | منبع: {USDT_CACHE.get('src', 'مدیریت')}\n<i>🤖 Forexin Bot</i>"
    return '⚠️ <b>دریافت قیمت ممکن نشد.</b>\nمدیریت: /usdt قیمت را تنظیم کنید.\n<code>' + html.escape(' | '.join(errs)[:200]) + '</code>'

def news_today():
    try:
        d = fetch_json('https://nfs.faireconomy.media/ff_calendar_thisweek.json')
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
    except Exception: pass
    return None

def tiktok_dl(u):
    q = urllib.parse.quote(u, safe='')
    try:
        r = requests.get('https://www.tikwm.com/api/?hd=1&url=' + q, headers={'User-Agent': UA}, timeout=20)
        res = r.json()
        if res.get('code') == 0: return res['data']
    except Exception: pass
    try:
        r = requests.post('https://tikwm.com/api/', data={'url': u, 'hd': 1}, headers={'User-Agent': UA}, timeout=20)
        res = r.json()
        if res.get('code') == 0: return res['data']
    except Exception: pass
    raise Exception('tiktok failed')

def insta_dl_multi(url):
    """Try multiple Instagram download services"""
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

def yt_dl(url):
    """YouTube download with PO Token support (if installed)"""
    opts = {
        'outtmpl': os.path.join(DL_DIR, '%(id)s.%(ext)s'),
        'format': 'best[height<=720]/best',
        'quiet': True, 'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 30, 'retries': 3,
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
                vd = tiktok_dl(url)
                vurl = vd.get('hdplay') or vd.get('play')
                if vurl and not vurl.startswith('http'): vurl = 'https://tikwm.com' + vurl
                data = requests.get(vurl, timeout=30, headers={'User-Agent': UA}).content
                title = (vd.get('title') or 'TikTok')[:50]
            elif 'instagram.com' in url:
                try:
                    data, title = insta_dl_multi(url)
                except Exception as e:
                    data, title = yt_dl(url)
            else:
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
                msg = f'❌ اینستاگرام این ویدیو را نمی‌دهد.\n💡 از <code>igram.world</code> به‌صورت دستی استفاده کنید.\n<code>{html.escape(err[:80])}</code>'
            elif 'youtube.com' in url or 'youtu.be' in url:
                msg = f'❌ یوتیوب این ویدیو را نمی‌دهد.\n💡 از <code>ssyoutube.com</code> به‌صورت دستی استفاده کنید.\n<code>{html.escape(err[:80])}</code>'
            else:
                msg = f'❌ دانلود ناموفق.\n<code>{html.escape(err[:100])}</code>'
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
            if is_blocked(u.id):
                try:
                    bot.ban_chat_member(m.chat.id, u.id)
                    bot.send_message(m.chat.id, f'⛔ <b>{u.first_name}</b> قبلاً بن شده بود؛ دوباره حذف شد.')
                except Exception: pass
                continue
            try:
                bot.send_message(m.chat.id, WELCOME_GROUP.format(first=u.first_name or 'دوست'), reply_markup=group_menu())
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
            bot.send_message(chat, f"🎁 <b>لینک‌های مفید:</b>\n🤖 {MAINBOT}\n📢 @forexin_turkaslanifree\n🎓 @Forexin_Turkaslani_Base\n💬 @forexinturkaslanilitcommuniti")
        elif d == 'gold':
            bot.send_message(chat, get_gold_only())
        elif d == 'usdt':
            bot.send_message(chat, get_usdt_only())
        elif d == 'dl':
            bot.send_message(chat, '🎬 <b>لینک ویدیو را بفرستید:</b>\n(یوتیوب، اینستاگرام، تیک‌تاک)')
        elif d == 'rules':
            bot.send_message(chat, '📜 <b>قوانین:</b>\n۱. احترام\n۲. بدون تبلیغ\n۳. فقط مباحث ترید\n۴. لینک = ۲ اخطار = بن دائمی')
        elif d == 'code':
            bot.send_message(chat, '🎟️ <b>کد VIP را وارد کنید:</b>')
        elif d == 'faq':
            mk = types.InlineKeyboardMarkup(row_width=2)
            mk.add(types.InlineKeyboardButton('لات', callback_data='gloss_lat'), types.InlineKeyboardButton('پیپ', callback_data='gloss_pip'))
            mk.add(types.InlineKeyboardButton('استاپ', callback_data='gloss_stop'), types.InlineKeyboardButton('اهرم', callback_data='gloss_ahrom'))
            mk.add(types.InlineKeyboardButton('اسپرد', callback_data='gloss_spread'), types.InlineKeyboardButton('تارگت', callback_data='gloss_target'))
            mk.add(types.InlineKeyboardButton('سشن', callback_data='gloss_session'), types.InlineKeyboardButton('کندل', callback_data='gloss_candle'))
            mk.add(types.InlineKeyboardButton('پترن', callback_data='gloss_pattern'), types.InlineKeyboardButton('LIT', callback_data='gloss_lit'))
            mk.add(types.InlineKeyboardButton('VIP', callback_data='gloss_vip'))
            bot.send_message(chat, '❓ <b>انتخاب کن:</b>', reply_markup=mk)
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
                bot.send_message(m.chat.id, f'⛔ کاربر بن شد و در بلاک‌لیست دائمی قرار گرفت.')
            except Exception: pass
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
                if hm == (8, 0) and now.strftime('%Y-%m-%d') != last_cal_day:
                    last_cal_day = now.strftime('%Y-%m-%d')
                    n = news_today()
                    if n: post_all(n)
                if hm == (9, 0) and now.strftime('%Y-%m-%d') != last_quote_day:
                    last_quote_day = now.strftime('%Y-%m-%d')
                    q = QUOTES[now.timetuple().tm_yday % len(QUOTES)]
                    post_all(f"🌟 <b>جملهٔ روز:</b>\n💡 {q}")
                if hm == (9, 30): post_all('🟠 سشن فرانکفورت')
                if hm == (10, 30): post_all('🟢 سشن لندن')
                if hm == (15, 0) and now.strftime('%Y-%m-%d') != last_news_day:
                    last_news_day = now.strftime('%Y-%m-%d')
                    msg = '📰 قبل از نیویورک: اخبار را چک کنید.'
                    if now.weekday() == 4 and now.day <= 7:
                        msg += '\n⚠️ <b>NFP!</b>'
                    post_all(msg)
                if hm == (15, 30): post_all('🟢 سشن نیویورک')
                if hm == (19, 30): post_all('🔴 لندن بسته شد')
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
