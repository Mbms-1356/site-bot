~~~`
import os, json, threading, time as _t, re, urllib.request, ssl
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
SITE = 'https://mbms-1356.github.io/forexin-site/'
CHANNEL = 'https://t.me/forexin_turkaslanifree'
CHANNEL_POST = '@forexin_turkaslanifree'
GROUP = 'https://t.me/forexinturkaslanilitcommuniti'
MAINBOT = 'https://t.me/TurkaslaniFx_bot'
INSTA = 'https://www.instagram.com/forexin.turkaslani'
YOUTUBE = 'https://www.youtube.com/@Forexin.turkaslani'
QUIZ = SITE + 'quiz.html'
DATA_FILE = 'trades.json'
ADMIN_FILE = 'admin.json'
DL_DIR = 'dl'
os.makedirs(DL_DIR, exist_ok=True)
ADMIN = None
try:
with open(ADMIN_FILE) as f: ADMIN = json.load(f)['id']
except Exception: pass
USERS, WARNS = set(), {}
WARN_TXT = {
'fa': '⚠️ ارسال لینک/تبلیغ ممنوع است! (اخطار {n}/3)',
'en': '⚠️ Links/ads are not allowed! (Warning {n}/3)',
'tr': '⚠️ Link/reklam yasaktır! (Uyarı {n}/3)',
'az': '⚠️ Link/reklam qadağandır! (Xəbərdarlıq {n}/3)',
'ur': '⚠️ لنک/اشتہار ممنوع ہے! (انتباہ {n}/3)',
'ku': '⚠️ Lînk/reklam qedexe ye! (Hişyarî {n}/3)',
'ar': '⚠️ الروابط/الإعلانات ممنوعة! (تحذير {n}/3)'
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
MENU = ['🎟️ VIP', '❓ سوالات', '💰 طلا', '🇮🇷 تتر', '🎬 دانلود', '📊 معامله', '📈 گزارش', '💬 بازخورد', '🧠 آزمون', '🌐 سایت', '📢 کانال', '📷 اینستا', '▶️ یوتیوب', '🎁 لینک‌ها', '🚀 شروع']
WELCOME_PRIV = 'سلام! 👋\nمن دستیار فارکسین ترک اصلانی هستم.\n📊 ژورنال معاملاتی | 💰 قیمت لحظه‌ای | 🎬 دانلودر'
WELCOME_GROUP = '''سلام {first} عزیز! 🌟
به «LIT Community Forexin_Turkaslani» خوش آمدید.
کانال‌های ما:
1️⃣ 📣 کانال سیگنال و لایو (رایگان)
@forexin_turkaslanifree
2️⃣ 🎓 کانال آموزش آکادمی
@Forexin_Turkaslani_Base
3️⃣ 💬 همین گروه (LIT Community)
4️⃣ ▶️ یوتیوب
youtube.com/@Forexin.turkaslani
⚠️ تمام مطالب صرفاً آموزشی‌اند.
🚫 ارسال لینک و تبلیغ ممنوع (۳ اخطار = مسدودیت).
با آرزوی سودهای پایدار 📈'''
def build_menu():
m = types.InlineKeyboardMarkup(row_width=2)
m.add(types.InlineKeyboardButton(MENU[0], callback_data='code'), types.InlineKeyboardButton(MENU[1], callback_data='faq'))
m.add(types.InlineKeyboardButton(MENU[2], callback_data='gold'), types.InlineKeyboardButton(MENU[3], callback_data='usdt'))
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
m.add(types.InlineKeyboardButton('📜 قوانین', callback_data='rules'), types.InlineKeyboardButton('🧠 آزمون', url=QUIZ))
m.add(types.InlineKeyboardButton('🎁 لینک‌ها', callback_data='inv'), types.InlineKeyboardButton('🚀 شروع', callback_data='st'))
return m
def fetch_json(url):
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(url, headers=headers)
return json.load(urllib.request.urlopen(req, timeout=8, context=ctx))
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
return f"📊 قیمت‌های لحظه‌ای:\n\n🥇 انس طلا: ${gold}\n🇮🇷 تتر: {usdt} تومان\n\n🔄 آپدیت خودکار از صرافی‌های ایرانی"
def handle_download(m, url):
wait = bot.send_message(m.chat.id, '⏳ در حال دانلود... صبر کنید!')
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
if len(data) > 4810241024:
bot.send_message(m.chat.id, '⚠️ فایل سنگین‌تر از ۴۸MB است و قابل ارسال نیست.')
else:
fp = os.path.join(DL_DIR, 'send.mp4')
with open(fp, 'wb') as f:
f.write(data)
with open(fp, 'rb') as f:
bot.send_video(m.chat.id, f, caption=f"{title}\n🤖 Forexin Downloader", supports_streaming=True)
try: os.remove(fp)
except Exception: pass
try: bot.delete_message(m.chat.id, wait.message_id)
except Exception: pass
except Exception as e:
err = str(e)
if 'login' in err.lower() or 'sign in' in err.lower():
msg = '❌ اینستاگرام نیاز به لاگین دارد. فقط لینک Reels عمومی بفرستید.'
else:
msg = f"❌ دانلود ناموفق بود.\n💡 لینک تیک‌تاک را در snaptik.app و اینستا را در snapinsta.app امتحان کنید.\n{err[:100]}"
bot.send_message(m.chat.id, msg)
try: bot.delete_message(m.chat.id, wait.message_id)
except Exception: pass
threading.Thread(target=job, daemon=True).start()
def is_link(txt):
return bool(re.search(r'https?://|t.me/|@[\w]{5,}|.com|.ir', txt.lower()))
def tehran_now():
return datetime.now(timezone(timedelta(hours=3, minutes=30)))
@bot.message_handler(content_types=['new_chat_members'])
def new_member(m):
for u in m.new_chat_members:
if not u.is_bot:
try:
bot.send_message(m.chat.id, WELCOME_GROUP.format(first=u.first_name or 'دوست عزیز'), reply_markup=group_menu())
except Exception: pass
@bot.message_handler(commands=['start'])
def start(m):
uid = m.from_user.id
if m.chat.type in ('group', 'supergroup'):
bot.send_message(m.chat.id, WELCOME_PRIV, reply_markup=group_menu())
return
if ADMIN is None:
ensure_admin(uid)
bot.send_message(uid, '🛠️ شما ادمین شدید!')
return
USERS.add(uid)
bot.send_message(uid, WELCOME_PRIV, reply_markup=build_menu())
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
chat = c.message.chat.id
d = c.data
try:
if d == 'st':
bot.send_message(chat, WELCOME_PRIV, reply_markup=build_menu())
elif d == 'inv':
bot.send_message(chat, f"🎁 لینک‌های مفید:\n🤖 ربات اصلی: {MAINBOT}\n💬 گروه: {GROUP}\n📢 کانال: {CHANNEL}")
elif d in ('gold', 'usdt'):
bot.send_message(chat, get_prices())
elif d == 'dl':
bot.send_message(chat, '🎬 لینک ویدیو را بفرستید:\n(یوتیوب، اینستاگرام، تیک‌تاک)')
elif d == 'rules':
bot.send_message(chat, '📜 قوانین گروه:\n۱. احترام متقابل\n۲. عدم تبلیغ و اسپم\n۳. فقط مباحث ترید و آموزشی')
elif d == 'code':
bot.send_message(chat, '🎟️ کد VIP خود را وارد کنید:')
elif d == 'faq':
bot.send_message(chat, '❓ سوالات متداول:\n۱. مطالب آموزشی رایگان است؟ بله، در کانال و یوتیوب.\n۲. سیگنال‌ها کجا اعلام می‌شود؟ کانال رایگان.\n۳. استراتژی LIT چیست؟ دورهٔ آموزشی آکادمی.')
elif d == 'fb':
bot.send_message(chat, '💬 بازخورد خود را بنویسید تا به مدیریت برسد:')
elif d == 'tr':
bot.send_message(chat, '📊 برای ثبت معامله (فقط ادمین):\n/trade ورود استاپ تارگت')
elif d == 'rp':
wins = len([x for x in TRADES if x.get('result') == 'win'])
loss = len([x for x in TRADES if x.get('result') == 'loss'])
bot.send_message(chat, f"📈 گزارش معاملات:\n✅ برنده: {wins}\n❌ بازنده: {loss}\n📊 کل: {len(TRADES)}")
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
if is_grp and is_link(t) and not ensure_admin(uid):
try: bot.delete_message(m.chat.id, m.message_id)
except Exception: pass
WARNS[uid] = WARNS.get(uid, 0) + 1
langc = (m.from_user.language_code or 'fa').split('-')[0]
if langc not in WARN_TXT: langc = 'fa'
bot.send_message(m.chat.id, WARN_TXT[langc].format(n=WARNS[uid]))
if WARNS[uid] >= 3:
try: bot.ban_chat_member(m.chat.id, uid)
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
bot.reply_to(m, f"📊 معامله #{tid}\n🎯 ورود: {e}\n🛡️ استاپ: {s}\n🏆 تارگت: {tg}\n💎 R:R = {rr}", reply_markup=mk)
except Exception:
bot.reply_to(m, 'فرمت صحیح: /trade ورود استاپ تارگت')
return
if t.startswith('/report') and ensure_admin(uid):
wins = len([x for x in TRADES if x.get('result') == 'win'])
loss = len([x for x in TRADES if x.get('result') == 'loss'])
bot.reply_to(m, f"📈 گزارش:\n✅ {wins} | ❌ {loss}")
return
def notifier():
last = ''
last_quote_day = ''
last_news_day = ''
while True:
try:
now = tehran_now()
key = now.strftime('%Y-%m-%d %H:%M')
if key != last:
last = key
hm = (now.hour, now.minute)
if hm == (10, 30):
try: bot.send_message(CHANNEL_POST, '🟢 سشن لندن باز شد!\nحجم و نوسان واقعی بازار شروع شد.')
except Exception: pass
if hm == (15, 0) and now.strftime('%Y-%m-%d') != last_news_day:
last_news_day = now.strftime('%Y-%m-%d')
msg = '📰 یادآور اخبار اقتصادی:\nقبل از سشن نیویورک تقویم اقتصادی را چک کنید:\nwww.forexfactory.com/calendar'
if now.weekday() == 4 and now.day <= 7:
msg += '\n\n⚠️ جمعهٔ اول ماه — روز NFP! نوسان شدید، مراقب باشید!'
try: bot.send_message(CHANNEL_POST, msg)
except Exception: pass
if hm == (15, 30):
try: bot.send_message(CHANNEL_POST, '🟢 سشن نیویورک باز شد!')
except Exception: pass
if hm == (19, 30):
try: bot.send_message(CHANNEL_POST, '🔴 سشن لندن بسته شد — نیویورک ادامه دارد.')
except Exception: pass
if hm == (9, 0) and now.strftime('%Y-%m-%d') != last_quote_day:
last_quote_day = now.strftime('%Y-%m-%d')
q = QUOTES[now.timetuple().tm_yday % len(QUOTES)]
try: bot.send_message(CHANNEL_POST, f"🌟 جملهٔ روز:\n\n💡 {q}\n\n🤖 Forexin Bot")
except Exception: pass
except Exception: pass
_t.sleep(20)
threading.Thread(target=notifier, daemon=True).start()
if name == 'main':
print('🚀 Bot started in polling mode')
while True:
try:
bot.infinity_polling()
except Exception:
_t.sleep(5)
