import os
import json
import threading
import time as _t
import urllib.request
from datetime import datetime, timedelta, timezone
import telebot
from telebot import types
from flask import Flask, request
import yt_dlp

TOKEN = '8978486498:AAGjeMhm0f6BMjVX2JA7LbrN4Bcv6M_LET8'
bot = telebot.TeleBot(TOKEN)

SITE = 'https://mbms-1356.github.io/forexin-site-/'
CHANNEL = 'https://t.me/forexin_turkaslanifree'
CHANNEL_POST = '@forexin_turkaslanifree'
INSTA = 'https://www.instagram.com/forexin.turkaslani'
YOUTUBE = 'https://www.youtube.com/@Forexin.turkaslani'
QUIZ = SITE + 'quiz.html'
DL_DIR = os.path.join(os.path.expanduser('~'), 'dl')
os.makedirs(DL_DIR, exist_ok=True)

ADMIN = None
USERS = set()
state = {}
used_codes = set()

SESS = [('سیدنی',0,30),('توکیو',3,30),('لندن',10,30),('نیویورک',15,30)]

FAQ = [
('پیپ','کوچک‌ترین واحد تغییر قیمت؛ معمولاً رقم چهارم اعشار (۰٫۰۰۰۱).'),
('لات','واحد حجم معامله؛ لات استاندارد = ۱۰۰۰۰ واحد ارز پایه.'),
('اهرم','سرمایهٔ قرضی از بروکر؛ سود و زیان را چند برابر می‌کند — مراقب!'),
('مارجین','وثیقه‌ای که بروکر برای معاملهٔ اهرمی نگه می‌دارد.'),
('استاپ','خروج خودکار در حد زیان — بیمهٔ زندگی معامله‌گر!'),
('تارگت','خروج در سود هدف؛ در LIT تارگت = نقدینگی مقابل.'),
('اسپرد','فاصلهٔ قیمت خرید و فروش؛ هزینهٔ بروکر.'),
('سشن','سیدنی ۰۰:۳۰ | توکیو ۰۳:۳۰ | لندن ۱۰:۳۰ | نیویورک ۱۵:۳۰ (تهران) — زنده: /time'),
('بروکر','بروکر رسمی ما WM Markets است؛ لینک IB به‌زودی در سایت.'),
('vip','با دعوت یا اشتراک؛ اگر کد آزمون داری دکمهٔ «فعال‌سازی کد VIP» را بزن.'),
('دعوت','برای آکادمی بیس: @TurkaslaniFx_bot — دو دوست واقعی دعوت کن.'),
('سایت','آدرس سایت: ' + SITE),
('آزمون','آزمون LIT + هدیهٔ ۷ روز VIP: ' + QUIZ),
('واژه','واژه‌نامهٔ ۳۰ اصطلاح: ' + SITE + 'vajeh.html'),
('کندل','آموزش کندل‌استیک: ' + SITE + 'candle.html'),
('پترن','پترن‌های کلاسیک: ' + SITE + 'patterns.html'),
('lit','استراتژی LIT: ' + SITE + 'lit.html'),
('تله','ابزار پول هوشمند برای شکار نقدینگی؛ سایه‌های بلند یعنی تله!'),
('بیلدآپ','تجمع نقدینگی؛ جلوی آن خلاف جهت نایست.'),
('سایکل','هر ۹۰ دقیقه یک جریان سفارش الگوریتمی جدید؛ سفارش اصلی در سقف سایکل.'),
('ریسک','دی‌تریدر: ۰٫۲۵ تا ۰٫۵٪ | اسکالپر: ۰٫۵ تا ۱٪ | سوینگ: ۱ تا ٪.'),
('اینستا','اینستاگرام: ' + INSTA),
('یوتیوب','یوتیوب: ' + YOUTUBE),
('دانلود','🎬 لینک یوتیوب/اینستا/تیک‌تاک را بفرست تا دانلود کنم!'),
('طلا','💰 قیمت لحظه‌ای طلا: /gold'),
('ساعت','ساعت تهران و سشن‌ها: /time'),
('ماشین','ماشین‌حساب پیپ: /pip لات پیپ'),
('پشتیبانی','@FX_Dow_Jones یا دکمهٔ «بازخورد به ادمین».'),
('کانال','کانال سیگنال رایگان: ' + CHANNEL)
]

def gold_price():
    url = 'https://data-asg.goldprice.org/dbXRates/USD'
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    d = json.load(urllib.request.urlopen(req, timeout=10))
    return round(d['items'][0]['xau_price'], 2)

def menu():
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton('🎟️ فعال‌سازی کد VIP', callback_data='code'),
          types.InlineKeyboardButton('❓ سؤالات متداول', callback_data='faq'))
    m.add(types.InlineKeyboardButton('💰 قیمت طلا', callback_data='gold'),
          types.InlineKeyboardButton('🎬 دانلود ویدیو', callback_data='dl'))
    m.add(types.InlineKeyboardButton('💬 بازخورد به ادمین', callback_data='fb'),
          types.InlineKeyboardButton('🧠 آزمون LIT', url=QUIZ))
    m.add(types.InlineKeyboardButton('🌐 وب‌سایت', url=SITE),
          types.InlineKeyboardButton('📢 کانال سیگنال', url=CHANNEL))
    m.add(types.InlineKeyboardButton('📸 اینستاگرام', url=INSTA),
          types.InlineKeyboardButton('▶️ یوتیوب', url=YOUTUBE))
    return m

def handle_link(m, url):
    wait = bot.send_message(m.chat.id, '⏳ در حال دانلود... صبر کن!')
    def work():
        try:
            opts = {'outtmpl': os.path.join(DL_DIR, '%(id)s.%(ext)s'), 'format': 'best', 'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(opts) as y:
                info = y.extract_info(url, download=True)
                fn = y.prepare_filename(info)
            size = os.path.getsize(fn)
            if size > 49*1024*1024:
                bot.send_message(m.chat.id, '⚠️ فایل بزرگ‌تر از ۵۰MB است؛ لینک کوچک‌تر بفرست.')
            else:
                with open(fn, 'rb') as f:
                    bot.send_video(m.chat.id, f, caption='🎬 ' + (info.get('title') or '') + '\n🤖 Forexin Site Bot')
            try: os.remove(fn)
            except Exception: pass
            bot.delete_message(m.chat.id, wait.message_id)
        except Exception as e:
            bot.send_message(m.chat.id, '⚠️ دانلود نشد: ' + str(e)[:150])
    threading.Thread(target=work, daemon=True).start()

def notifier():
    last = ''
    while True:
        try:
            tz = timezone(timedelta(hours=3, minutes=30))
            now = datetime.now(tz)
            key = now.strftime('%Y-%m-%d %H:%M')
            if key != last:
                last = key
                for fa, h, mi in SESS:
                    if now.hour == h and now.minute == mi:
                        try: bot.send_message(CHANNEL_POST, '🟢 سشن ' + fa + ' باز شد!')
                        except Exception: pass
                if now.hour == 9 and now.minute == 0:
                    k, v = FAQ[now.timetuple().tm_yday % len(FAQ)]
                    try: bot.send_message(CHANNEL_POST, '📚 واژهٔ روز: ' + k + '\n💡 ' + v + '\n🤖 Forexin Site Bot')
                    except Exception: pass
        except Exception:
            pass
        _t.sleep(20)

@bot.message_handler(commands=['start'])
def start(m):
    global ADMIN
    uid = m.from_user.id
    if m.chat.type != 'private':
        bot.send_message(m.chat.id, 'سلام! 🤖 دستیار سایت فارکسین هستم؛ برای سؤال و دانلود، پی‌وی پیام بده.')
        return
    args = m.text.split()
    if ADMIN is None:
        ADMIN = uid
        bot.send_message(uid, '🛠️ شما ادمین ربات سایت شدید!\n📢 کانال: /post متن\n👥 اعضا: /broadcast متن\n🕰️ سشن‌ها: /time\n💰 طلا: /gold\n🧮 پیپ: /pip لات پیپ')
        return
    USERS.add(uid)
    if len(args) > 1:
        a = args[1]
        if a == 'web':
            bot.send_message(uid, '👋 دیدم از سایت اومدی!\nکد VIP یا سؤالت را بفرست. 🎟️', reply_markup=menu())
            return
        if a.startswith('VIP7-'):
            if a in used_codes:
                bot.send_message(uid, '⚠️ این کد قبلاً استفاده شده.')
            else:
                state[uid] = {'step':'name','code':a}
                bot.send_message(uid, '🎟️ کدت ثبت شد!\nنام و نام خانوادگی‌ات را بنویس:')
            return
    bot.send_message(uid, 'سلام ' + (m.from_user.first_name or 'دوست عزیز') + '! 🌟\nدستیار سایت فارکسین ترک‌اصلانی:\n🎬 دانلود ویدیو | 💰 قیمت طلا | 📚 آموزش\n👇 چه کمکی کنم؟', reply_markup=menu())

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    uid = c.from_user.id
    if c.data == 'code':
        state[uid] = {'step':'getcode'}
        bot.send_message(uid, '🎟️ کد VIP را بفرست (از صفحهٔ نتیجهٔ آزمون):')
    elif c.data == 'faq':
        mk = types.InlineKeyboardMarkup()
        row = []
        for i,(k,v) in enumerate(FAQ):
            row.append(types.InlineKeyboardButton(k, callback_data='f'+str(i)))
            if len(row)==2: mk.add(*row); row=[]
        if row: mk.add(*row)
        bot.send_message(uid, '❓ یکی را انتخاب کن:', reply_markup=mk)
    elif c.data == 'fb':
        state[uid] = {'step':'fb'}
        bot.send_message(uid, '💬 پیام/پیشنهاد/انتقادت را بنویس؛ مستقیم به ادمین می‌رسد:')
    elif c.data == 'gold':
        try:
            bot.send_message(uid, '💰 قیمت لحظه‌ای طلا (XAU/USD): $' + str(gold_price()))
        except Exception:
            bot.send_message(uid, '⚠️ قیمت طلا الان در دسترس نیست؛ چند دقیقهٔ دیگر دوباره بزن.')
    elif c.data == 'dl':
        bot.send_message(uid, '🎬 لینک یوتیوب / اینستاگرام / تیک‌تاک را همین‌جا بفرست تا برایت دانلود کنم!')
    elif c.data.startswith('f'):
        bot.send_message(uid, '💡 ' + FAQ[int(c.data[1:])][1])
    bot.answer_callback_query(c.id)

@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'), content_types=['text'])
def txt(m):
    uid = m.from_user.id
    is_group = m.chat.type in ('group', 'supergroup')
    t = m.text.strip()
    if not is_group and ('youtube.com' in t or 'youtu.be' in t or 'instagram.com' in t or 'tiktok.com' in t):
        handle_link(m, t.split()[0])
        return
    for k,v in FAQ:
        if k in t:
            bot.send_message(m.chat.id, '💡 ' + v)
            return
    if is_group:
        return
    st = state.get(uid)
    if st:
        step = st['step']
        if step == 'getcode':
            if t in used_codes:
                bot.send_message(uid, '⚠️ این کد قبلاً استفاده شده.')
            else:
                state[uid] = {'step':'name','code':t}
                bot.send_message(uid, '✅ کد معتبر است!\nنام و نام خانوادگی‌ات را بنویس:')
            return
        if step == 'name':
            st['name'] = t
            st['step'] = 'phone'
            bot.send_message(uid, '📱 حالا شمارهٔ تلگرامت را بفرست:')
            return
        if step == 'phone':
            used_codes.add(st['code'])
            if ADMIN:
                bot.send_message(ADMIN, '🎁 لید جدید آزمون!\n👤 ' + st['name'] + '\n📱 ' + t + '\n🎟️ کد: ' + st['code'])
            del state[uid]
            bot.send_message(uid, '🎉 عالی! کدت فعال شد.\n۷ روز VIP رایگان — ادمین به‌زودی پیام می‌دهد. ✅', reply_markup=menu())
            return
        if step == 'fb':
            if ADMIN:
                bot.send_message(ADMIN, '💬 بازخورد کاربر ' + str(uid) + ':\n' + m.text)
            del state[uid]
            bot.send_message(uid, '✅ پیامت به ادمین رسید. ممنون! 🙏', reply_markup=menu())
            return
    if m.forward_from or m.forward_from_chat:
        bot.send_message(uid, '📨 پیام فورواردی رسید!\nسؤالت را با کلمهٔ کلیدی بنویس یا لینک ویدیو بفرست 🎬', reply_markup=menu())
        return
    bot.send_message(uid, '🤔 متوجه نشدم؛ از منو انتخاب کن یا لینک ویدیو بفرست 🎬', reply_markup=menu())

@bot.message_handler(commands=['time'])
def timecmd(m):
    tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tz)
    th = now.hour + now.minute/60
    lines = ['🕰️ ساعت تهران: ' + now.strftime('%H:%M')]
    for fa, h, mi in SESS:
        o = h + mi/60
        c = o + 9
        openb = (o < c and o <= th < c) or (o > c and (th >= o or th < c))
        lines.append(('🟢 ' if openb else '🔴 ') + fa + (' — باز' if openb else ' — بسته'))
    bot.send_message(m.chat.id, '\n'.join(lines))

@bot.message_handler(commands=['gold'])
def goldcmd(m):
    try:
        bot.reply_to(m, '💰 قیمت لحظه‌ای طلا (XAU/USD): $' + str(gold_price()))
    except Exception:
        bot.reply_to(m, '⚠️ قیمت طلا الان در دسترس نیست؛ چند دقیقهٔ دیگر دوباره بزن.')

@bot.message_handler(commands=['pip'])
def pipcmd(m):
    parts = m.text.split()
    try:
        lots = float(parts[1]); pips = float(parts[2])
        bot.reply_to(m, '🧮 ارزش پیپ: حدود $' + str(round(pips*10*lots, 2)))
    except Exception:
        bot.reply_to(m, '🧮 روش استفاده: /pip لات پیپ\nمثال: /pip 0.1 20')

@bot.message_handler(commands=['broadcast'])
def bc(m):
    if m.from_user.id != ADMIN: return
    parts = m.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(m, '📢 روش استفاده: /broadcast متن پیام')
        return
    n = 0
    for u in list(USERS):
        try:
            bot.send_message(u, parts[1]); n += 1
        except Exception:
            pass
    bot.reply_to(m, '📢 ارسال شد به ' + str(n) + ' نفر.')

@bot.message_handler(commands=['post'])
def post(m):
    if m.from_user.id != ADMIN: return
    parts = m.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(m, '📢 روش استفاده: /post متن پیام کانال')
        return
    try:
        bot.send_message(CHANNEL_POST, parts[1])
        bot.reply_to(m, '✅ در کانال منتشر شد!')
    except Exception as e:
        bot.reply_to(m, '⚠️ خطا: ' + str(e) + '\nمطمئن شو ربات در کانال ادمین است.')

app = Flask(__name__)

@app.route('/')
def home():
    return '🤖 Forexin Site Bot is alive!'

@app.route('/setup')
def setup():
    url = 'https://' + request.host + '/hook'
    bot.set_webhook(url)
    return '✅ webhook set: ' + url

@app.route('/hook', methods=['POST'])
def hook():
    try:
        bot.process_new_updates(telebot.types.Update.de_json(request.get_json()))
    except Exception:
        pass
    return 'ok'

threading.Thread(target=notifier, daemon=True).start()

if __name__ == '__main__':
    if os.environ.get('PORT'):
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '10000')))
    else:
        print('🚀 Bot started in polling mode')
        bot.infinity_polling()
