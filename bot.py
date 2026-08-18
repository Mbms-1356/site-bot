import os
import json
import threading
import time as _t
import re
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
DATA_FILE = os.path.join(os.path.expanduser('~'), 'trades.json')
ADMIN_FILE = os.path.join(os.path.expanduser('~'), 'admin.json')
DL_DIR = os.path.join(os.path.expanduser('~'), 'dl')
os.makedirs(DL_DIR, exist_ok=True)

ADMIN = None
try:
    with open(ADMIN_FILE) as f:
        ADMIN = json.load(f)['id']
except Exception:
    pass

USERS = set()
state = {}
used_codes = set()
WARNS = {}
WARN_TXT = {
'fa':'⚠️ ارسال لینک/تبلیغ ممنوع است! (اخطار {n}/3)',
'en':'⚠️ Links/ads are not allowed! (Warning {n}/3)',
'tr':'⚠️ Link/reklam yasaktır! (Uyarı {n}/3)',
'az':'⚠️ Link/reklam qadağandır! (Xəbərdarlıq {n}/3)',
'ur':'⚠️ لنک/اشتہار ممنوع ہے! (انتباہ {n}/3)',
'ku':'⚠️ Lînk/reklam qedexe ye! (Hişyarî {n}/3)',
'ar':'⚠️ الروابط/الإعلانات ممنوعة! (تحذير {n}/3)'
}

try:
    with open(DATA_FILE) as f:
        TRADES = json.load(f)
except Exception:
    TRADES = []

def save_trades():
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(TRADES, f)
    except Exception:
        pass

def ensure_admin(uid):
    global ADMIN
    if ADMIN is None:
        ADMIN = uid
        try:
            with open(ADMIN_FILE, 'w') as f:
                json.dump({'id': uid}, f)
        except Exception:
            pass
        return True
    return uid == ADMIN

SESS = [('سیدنی',0,30),('توکیو',3,30),('لندن',10,30),('نیویورک',15,30)]

QUOTES = [
'بازار هرگز اشتباه نمی‌کند؛ فقط دیدگاه ما اشتباه است. — Jesse Livermore',
'صبر، نیمی از پیروزی در ترید است.',
'تریدر حرفه‌ای ریسک را مدیریت می‌کند؛ آماتور سود را دنبال می‌کند.',
'ترس و طمع، دو دشمن بزرگ تریدرند.',
'معامله‌ای که از دست رفت، بهتر از معامله‌ای است که استاپ ندارد.',
'انضباط یعنی انجام دادن کاری که باید، وقتی که نمی‌خواهی.',
'تریدر موفق کسی است که ضررهای کوچک را می‌پذیرد تا سودهای بزرگ بگیرد.',
'هر ضرر، یک درس است — اگر یادش بگیری.',
'احساساتت را پشت درِ بازار بگذار.',
'ترید شطرنج است، نه قمار؛ فکر کن، بعد حرکت کن.',
'بدون برنامه وارد شدن، یعنی برای باختن آماده شدن.',
'استاپ‌لاس هزینه نیست؛ بیمهٔ زندگی معامله‌گر است.',
'یک ترید خوب، حاصل هزار ساعت تمرین است.',
'روند دوست توست — تا وقتی که تمام شود.',
'پول هوشمند ردپا می‌گذارد؛ دنبالش کن.',
'نقدینگی سوخت حرکت است؛ جایی که نقدینگی هست، قیمت می‌رود.',
'هر کندل یک داستان می‌گوید؛ یاد بگیر بخوانی‌اش.',
'تله‌ها همه‌جا هستند — صبر کن تا شکارچیان شکار شوند.',
'سایکل ۹۰ دقیقه، ساعتِ پول هوشمند است.',
'CHoK اول، BOS دوم؛ ساختار را بشناس، بعد وارد شو.',
'۱٪ ریسک، ۱۰۰٪ بقا.',
'حسابی که خالی نشود، همیشه فرصت جبران دارد.',
'اهرم شمشیر دو لبه است؛ هم سود را چند برابر می‌کند، هم زیان را.',
'پارشیال کن، نفس بکش، ادامه بده.',
'پولت را در یک معامله شرط نبند؛ پخش کن.',
'دراوداون روزانه حد دارد؛ اگر رسیدی، کامپیوتر را خاموش کن.',
'تریدر برنده، تریدری است که هنوز در بازی است.',
'سود مرکب، هشتمین عجایب دنیاست.',
'هرگز با پولی ترید نکن که نمی‌توانی از دست بدهی.',
'سرمایه‌ات مقدس است؛ از آن مثل یک سرباز محافظت کن.',
'ترید آسان است؛ آسان ماندن سخت است.',
'موفقیت در ترید، جمع تصمیم‌های کوچک هر روز است.',
'تریدر آماتور وقتی می‌برد شاد است؛ تریدر حرفه‌ای وقتی خوب اجرا می‌کند.',
'هر معامله یک فرصت یادگیری است، حتی ضررها.',
'تریدرها مثل عقاب‌اند: صبر می‌کنند، بعد شیرجه می‌زنند.',
'به فرآیند پایبند باش، نه به نتیجه.',
'موفقیت در ترید یک ماراتن است، نه یک سرعت.',
'ذهن آرام، چارت روشن می‌بیند.',
'بهترین معامله، معامله‌ای است که نکردی.',
'ترید ورزش ذهن است؛ ذهنت را آماده نگه دار.',
'هر روز یک صفحهٔ جدید از چارت است؛ دیروز را فراموش کن.',
'پول هوشمند همیشه یک قدم جلوتر است؛ یاد بگیر مثل او فکر کنی.',
'بازار پاداش صبر را می‌دهد، نه سرعت را.',
'تریدر موفق کسی است که وقتی همه می‌ترسند، می‌خرد.',
'هر سایکل یک فرصت است؛ آماده باش.',
'تله‌ها را بشناس، تا شکار نشوی.',
'حرکت با نخبگان، معامله برای برد.',
'استراتژی LIT یعنی دیدن چیزی که دیگران نمی‌بینند.',
'معامله‌ای که با منطق گرفته شده، حتی اگر ضرر شود، درست بوده.',
'هرگز ناامید نشو؛ بازار همیشه فرصت جدید می‌سازد.',
'LIT یعنی Liquidity, Imbalance, Trend — سه راز پول هوشمند.',
'EPA حرکت سالم است؛ ایمبالانس یعنی جابه‌جایی پول.',
'بیلدآپ نقدینگی جلوی ریورسال می‌ایستد — خلاف جهت نایست.',
'سفارش اصلی در سقف سایکل ۹۰ است؛ لیمیتت را آنجا بگذار.',
'SMT تلهٔ اسمارت مانی است؛ ریجکتِ بلند = ورود طلایی.'
]

FAQ = [
('پیپ','کوچک‌ترین واحد تغییر قیمت؛ معمولاً رقم چهارم اعشار.'),
('لات','واحد حجم معامله؛ لات استاندارد = ۱۰۰۰۰ واحد ارز پایه.'),
('اهرم','سرمایهٔ قرضی از بروکر؛ سود و زیان را چند برابر می‌کند.'),
('استاپ','خروج خودکار در حد زیان — بیمهٔ زندگی معامله‌گر!'),
('تارگت','خروج در سود هدف؛ در LIT تارگت = نقدینگی مقابل.'),
('اسپرد','فاصلهٔ قیمت خرید و فروش؛ هزینهٔ بروکر.'),
('سشن','سیدنی ۰۰:۳۰ | توکیو ۰۳:۳۰ | لندن ۱۰:۳۰ | نیویورک ۱۵:۳۰ (تهران) — /time'),
('vip','با دعوت یا اشتراک؛ اگر کد آزمون داری دکمهٔ VIP را بزن.'),
('دعوت','برای آکادمی بیس: @TurkaslaniFx_bot'),
('سایت','آدرس سایت: ' + SITE),
('آزمون','آزمون LIT + ۷ روز VIP: ' + QUIZ),
('کندل','آموزش کندل‌استیک: ' + SITE + 'candle.html'),
('پترن','پترن‌های کلاسیک: ' + SITE + 'patterns.html'),
('lit','استراتژی LIT: ' + SITE + 'lit.html'),
('دانلود','🎬 لینک یوتیوب/اینستا/تیک‌تاک را بفرست تا دانلود کنم!'),
('طلا','💰 قیمت لحظه‌ای: /gold'),
('معامله','📊 ثبت معامله: /trade ورود استاپ تارگت')
]

WELCOME = '''سلام {first} عزیز! 🌟
به «LIT Community Forexin_Turkaslani» خوش آمدید.

به جمع تریدرهای حرفه‌ای و خانواده فارکسین ترک اصلانی خوش آمدید. کانال‌های ما:

1️⃣ 📣 کانال سیگنال و لایو (رایگان)
@forexin_turkaslanifree
✅ تحلیل‌های لحظه‌ای و نکات میلی‌متری

2️⃣ 🎓 کانال بیس و آموزش آکادمی
@Forexin_Turkaslani_Base
✅ اصول استراتژی LIT و مدیریت سرمایه

3️⃣ 💬 همین گروه (LIT Community)
@forexinturkaslanilitcommuniti
✅ پرسش و پاسخ و رفع اشکال چارت

4️⃣ ▶️ کانال یوتیوب
youtube.com/@Forexin.turkaslani
✅ ویدیوهای آموزشی کامل

⚠️ تمام مطالب صرفاً آموزشی‌اند. مسئولیت معاملات با خودتان است.
🛡️ ارسال لینک و تبلیغ ممنوع (۳ اخطار = مسدودیت).

با آرزوی سودهای پایدار 📈'''

def menu():
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton('🎟️ فعال‌سازی کد VIP', callback_data='code'),
          types.InlineKeyboardButton('❓ سؤالات متداول', callback_data='faq'))
    m.add(types.InlineKeyboardButton('💰 قیمت طلا', callback_data='gold'),
          types.InlineKeyboardButton('🎬 دانلود ویدیو', callback_data='dl'))
    m.add(types.InlineKeyboardButton('📊 ثبت معامله', callback_data='tr'),
          types.InlineKeyboardButton('📈 گزارش من', callback_data='rp'))
    m.add(types.InlineKeyboardButton('💬 بازخورد به ادمین', callback_data='fb'),
          types.InlineKeyboardButton('🧠 آزمون LIT', url=QUIZ))
    m.add(types.InlineKeyboardButton('🌐 وب‌سایت', url=SITE),
          types.InlineKeyboardButton('📢 کانال سیگنال', url=CHANNEL))
    m.add(types.InlineKeyboardButton('📸 اینستاگرام', url=INSTA),
          types.InlineKeyboardButton('▶️ یوتیوب', url=YOUTUBE))
    return m

def group_menu():
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton('📜 قوانین گروه', callback_data='rules'),
          types.InlineKeyboardButton('🧠 آزمون LIT', url=QUIZ))
    m.add(types.InlineKeyboardButton('🌐 وب‌سایت', url=SITE),
          types.InlineKeyboardButton('📢 کانال سیگنال', url=CHANNEL))
    return m

def gold_price():
    try:
        req = urllib.request.Request('https://data-asg.goldprice.org/dbXRates/USD', headers={'User-Agent':'Mozilla/5.0'})
        d = json.load(urllib.request.urlopen(req, timeout=10))
        return round(d['items'][0]['xau_price'], 2)
    except Exception:
        return None

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
                bot.send_message(m.chat.id, '⚠️ فایل بزرگ‌تر از ۵۰MB است.')
            else:
                with open(fn, 'rb') as f:
                    bot.send_video(m.chat.id, f, caption='🎬 ' + (info.get('title') or '') + '\n🤖 Forexin Site Bot')
            try: os.remove(fn)
            except Exception: pass
            bot.delete_message(m.chat.id, wait.message_id)
        except Exception as e:
            bot.send_message(m.chat.id, '⚠️ دانلود نشد: ' + str(e)[:150])
    threading.Thread(target=work, daemon=True).start()

def report(trades, title):
    if not trades:
        return '📊 ' + title + '\n\n❌ معامله‌ای ثبت نشده.'
    wins = [t for t in trades if t.get('result') == 'win']
    losses = [t for t in trades if t.get('result') == 'loss']
    openn = [t for t in trades if t.get('result') is None]
    rrs = [t['rr'] for t in trades if t.get('rr')]
    avg_rr = round(sum(rrs)/len(rrs), 2) if rrs else 0
    closed = len(wins) + len(losses)
    wr = round(len(wins)/closed*100, 1) if closed > 0 else 0
    return '📊 ' + title + '\n\n📈 تعداد: ' + str(len(trades)) + '\n✅ برنده: ' + str(len(wins)) + '\n❌ بازنده: ' + str(len(losses)) + '\n⏳ باز: ' + str(len(openn)) + '\n🎯 Win Rate: ' + str(wr) + '٪\n💎 میانگین R:R: ' + str(avg_rr)

def today():
    tz = timezone(timedelta(hours=3, minutes=30))
    return datetime.now(tz).strftime('%Y-%m-%d')

def week_start():
    tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tz)
    return (now - timedelta(days=now.weekday())).strftime('%Y-%m-%d')

def month_start():
    tz = timezone(timedelta(hours=3, minutes=30))
    return datetime.now(tz).strftime('%Y-%m-01')

def is_link(txt):
    return bool(re.search(r'https?://|t\.me/|@[\w]{5,}|\.com|\.ir|\.net', txt.lower()))

@bot.message_handler(commands=['start'])
def start(m):
    uid = m.from_user.id
    if m.chat.type in ('group', 'supergroup'):
        bot.send_message(m.chat.id, WELCOME.format(first=m.from_user.first_name or 'دوست عزیز'), reply_markup=group_menu())
        return
    args = m.text.split()
    if ADMIN is None:
        ensure_admin(uid)
        bot.send_message(uid, '🛠️ ادمین ربات شدید!\n\n📊 /trade ورود استاپ تارگت\n✅ /win شماره | ❌ /loss شماره\n📈 /report | week | month\n🏆 /stats\n📢 /post متن | 👥 /broadcast متن')
        return
    USERS.add(uid)
    if len(args) > 1:
        a = args[1]
        if a == 'web':
            bot.send_message(uid, '👋 از سایت اومدی!\nکد VIP یا سؤالت را بفرست.', reply_markup=menu())
            return
        if a.startswith('VIP7-'):
            if a in used_codes:
                bot.send_message(uid, '⚠️ این کد قبلاً استفاده شده.')
            else:
                state[uid] = {'step':'name','code':a}
                bot.send_message(uid, '🎟️ کدت ثبت شد!\nنام و نام خانوادگی:')
            return
    bot.send_message(uid, 'سلام ' + (m.from_user.first_name or 'دوست عزیز') + '! 🌟\nدستیار فارکسین:\n📊 ثبت معامله | 💰 طلا | 🎬 دانلود\n👇 چه کمکی کنم؟', reply_markup=menu())

@bot.message_handler(content_types=['new_chat_members'])
def new_member(m):
    for u in m.new_chat_members:
        if not u.is_bot:
            try:
                bot.send_message(m.chat.id, WELCOME.format(first=u.first_name or 'دوست عزیز'), reply_markup=group_menu())
            except Exception:
                pass

@bot.callback_query_handler(func=lambda c: c.data.startswith(('w','l')) and c.data[1:].isdigit())
def trade_result(c):
    if not ensure_admin(c.from_user.id):
        bot.answer_callback_query(c.id, 'فقط ادمین'); return
    tid = int(c.data[1:])
    for t in TRADES:
        if t['id'] == tid:
            t['result'] = 'win' if c.data.startswith('w') else 'loss'
            save_trades()
            txt = '✅ برنده!' if t['result']=='win' else '❌ بازنده!'
            try:
                bot.edit_message_text(c.message.text + '\n\n🏁 نتیجه: ' + txt, c.message.chat.id, c.message.message_id)
            except Exception:
                pass
            bot.answer_callback_query(c.id, txt)
            return
    bot.answer_callback_query(c.id, 'پیدا نشد')

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    uid = c.from_user.id
    if c.data == 'rules':
        bot.send_message(c.message.chat.id, '📜 قوانین گروه:\n\n۱. احترام متقابل\n۲. ممنوع: تبلیغ، اسپم، توهین\n۳. سؤالات فقط دربارهٔ ترید\n۴. اشتراک اطلاعات شخصی ممنوع\n۵. تخلف = حذف\n\n⚠️ مسئولیت معاملات با خودتان است.')
    elif c.data == 'code':
        state[uid] = {'step':'getcode'}
        bot.send_message(uid, '🎟️ کد VIP را بفرست:')
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
        bot.send_message(uid, '💬 پیام/پیشنهادت را بنویس:')
    elif c.data == 'gold':
        p = gold_price()
        if p: bot.send_message(uid, '💰 طلا (XAU/USD): $' + str(p))
        else: bot.send_message(uid, '⚠️ قیمت در دسترس نیست.')
    elif c.data == 'dl':
        bot.send_message(uid, '🎬 لینک یوتیوب / اینستا / تیک‌تاک را همین‌جا بفرست!')
    elif c.data == 'tr':
        bot.send_message(uid, '📊 فرمت:\n/trade ورود استاپ تارگت\n\nمثال: /trade 2345.50 2340.00 2360.00')
    elif c.data == 'rp':
        tr = [t for t in TRADES if t['user'] == uid]
        bot.send_message(uid, report(tr, 'گزارش کلی تو'))
    elif c.data.startswith('f'):
        bot.send_message(uid, '💡 ' + FAQ[int(c.data[1:])][1])
    bot.answer_callback_query(c.id)

@bot.message_handler(commands=['trade'])
def trade_cmd(m):
    if not ensure_admin(m.from_user.id):
        bot.reply_to(m, '⚠️ فقط ادمین می‌تواند معامله ثبت کند.')
        return
    parts = m.text.split()
    try:
        entry = float(parts[1]); stop = float(parts[2]); target = float(parts[3])
    except Exception:
        bot.reply_to(m, '📊 فرمت: /trade ورود استاپ تارگت\nمثال: /trade 2345.50 2340.00 2360.00')
        return
    risk = abs(entry - stop)
    reward = abs(target - entry)
    rr = round(reward/risk, 2) if risk > 0 else 0
    direction = 'BUY 🟢' if target > entry else 'SELL 🔴'
    tid = len(TRADES) + 1
    TRADES.append({'id':tid,'user':m.from_user.id,'entry':entry,'stop':stop,'target':target,'risk':round(risk,4),'reward':round(reward,4),'rr':rr,'dir':direction,'date':today(),'result':None})
    save_trades()
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton('✅ برنده (TP)', callback_data='w'+str(tid)),
           types.InlineKeyboardButton('❌ بازنده (SL)', callback_data='l'+str(tid)))
    bot.reply_to(m, '📊 معامله #'+str(tid)+' ثبت شد!\n\n'+direction+'\n🎯 ورود: '+str(entry)+'\n🛡️ استاپ: '+str(stop)+'\n🏆 تارگت: '+str(target)+'\n⚖️ ریسک: '+str(round(risk,4))+'\n💰 ریوارد: '+str(round(reward,4))+'\n💎 R:R = '+str(rr), reply_markup=mk)

@bot.message_handler(commands=['win'])
def win_cmd(m):
    if not ensure_admin(m.from_user.id): return
    try:
        tid = int(m.text.split()[1])
        for t in TRADES:
            if t['id'] == tid and t['result'] is None:
                t['result'] = 'win'; save_trades()
                bot.reply_to(m, '✅ معامله #'+str(tid)+' برنده شد!')
                return
        bot.reply_to(m, '⚠️ پیدا نشد یا قبلاً بسته شده.')
    except Exception:
        bot.reply_to(m, '📊 روش: /win شماره')

@bot.message_handler(commands=['loss'])
def loss_cmd(m):
    if not ensure_admin(m.from_user.id): return
    try:
        tid = int(m.text.split()[1])
        for t in TRADES:
            if t['id'] == tid and t['result'] is None:
                t['result'] = 'loss'; save_trades()
                bot.reply_to(m, '❌ معامله #'+str(tid)+' بازنده شد.')
                return
        bot.reply_to(m, '⚠️ پیدا نشد یا قبلاً بسته شده.')
    except Exception:
        bot.reply_to(m, '📊 روش: /loss شماره')

@bot.message_handler(commands=['report'])
def report_cmd(m):
    parts = m.text.split()
    if len(parts) > 1 and parts[1] == 'week':
        bot.reply_to(m, report([t for t in TRADES if t['date'] >= week_start()], 'گزارش هفته'))
    elif len(parts) > 1 and parts[1] == 'month':
        bot.reply_to(m, report([t for t in TRADES if t['date'] >= month_start()], 'گزارش ماه'))
    else:
        bot.reply_to(m, report([t for t in TRADES if t['date'] == today()], 'گزارش امروز'))

@bot.message_handler(commands=['stats'])
def stats_cmd(m):
    bot.reply_to(m, report(TRADES, 'آمار کل'))

@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'), content_types=['text'])
def txt(m):
    uid = m.from_user.id
    is_group = m.chat.type in ('group', 'supergroup')
    t = m.text.strip()
    if is_group and is_link(t):
        if not ensure_admin(uid):
            try:
                bot.delete_message(m.chat.id, m.message_id)
            except Exception:
                pass
            langc = (m.from_user.language_code or 'fa').split('-')[0]
            if langc not in WARN_TXT:
                langc = 'fa'
            WARNS[uid] = WARNS.get(uid, 0) + 1
            n = WARNS[uid]
            try:
                bot.send_message(m.chat.id, WARN_TXT[langc].format(n=n))
            except Exception:
                pass
            if n >= 3:
                try:
                    bot.ban_chat_member(m.chat.id, uid)
                    bot.send_message(m.chat.id, '🚫 کاربر به دلیل تکرار تبلیغ مسدود شد.')
                except Exception:
                    pass
        return
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
                bot.send_message(uid, '⚠️ قبلاً استفاده شده.')
            else:
                state[uid] = {'step':'name','code':t}
                bot.send_message(uid, '✅ نام و نام خانوادگی:')
        elif step == 'name':
            st['name'] = t; st['step'] = 'phone'
            bot.send_message(uid, '📱 شماره تلگرام:')
        elif step == 'phone':
            used_codes.add(st['code'])
            if ADMIN:
                bot.send_message(ADMIN, '🎁 لید!\n👤 '+st['name']+'\n📱 '+t+'\n🎟️ '+st['code'])
            del state[uid]
            bot.send_message(uid, '🎉 فعال شد!', reply_markup=menu())
        elif step == 'fb':
            if ADMIN: bot.send_message(ADMIN, '💬 بازخورد:\n'+m.text)
            del state[uid]
            bot.send_message(uid, '✅ رسید!', reply_markup=menu())

@bot.message_handler(commands=['time'])
def timecmd(m):
    tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tz)
    th = now.hour + now.minute/60
    lines = ['🕰️ ساعت تهران: '+now.strftime('%H:%M')]
    for fa, h, mi in SESS:
        o = h + mi/60
        c = o + 9
        openb = (o < c and o <= th < c) or (o > c and (th >= o or th < c))
        lines.append(('🟢 ' if openb else '🔴 ') + fa + (' — باز' if openb else ' — بسته'))
    bot.send_message(m.chat.id, '\n'.join(lines))

@bot.message_handler(commands=['gold'])
def goldcmd(m):
    p = gold_price()
    if p: bot.reply_to(m, '💰 طلا: $'+str(p))
    else: bot.reply_to(m, '⚠️ در دسترس نیست.')

@bot.message_handler(commands=['broadcast'])
def bc(m):
    if not ensure_admin(m.from_user.id): return
    parts = m.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(m, '📢 /broadcast متن'); return
    n = 0
    for u in list(USERS):
        try: bot.send_message(u, parts[1]); n += 1
        except Exception: pass
    bot.reply_to(m, '📢 ارسال شد به '+str(n))

@bot.message_handler(commands=['post'])
def post(m):
    if not ensure_admin(m.from_user.id): return
    parts = m.text.split(' ', 1)
    if len(parts) < 2:
        bot.reply_to(m, '📢 /post متن'); return
    try:
        bot.send_message(CHANNEL_POST, parts[1])
        bot.reply_to(m, '✅ منتشر شد!')
    except Exception as e:
        bot.reply_to(m, '⚠️ '+str(e))

def notifier():
    last = ''
    last_quote_day = ''
    last_news_day = ''
    while True:
        try:
            tz = timezone(timedelta(hours=3, minutes=30))
            now = datetime.now(tz)
            key = now.strftime('%Y-%m-%d %H:%M')
            if key != last:
                last = key
                hm = (now.hour, now.minute)
                if hm == (10, 30):
                    try: bot.send_message(CHANNEL_POST, '🟢 سشن لندن باز شد!')
                    except Exception: pass
                if hm == (15, 0) and today() != last_news_day:
                    last_news_day = today()
                    msg = '📰 یادآور اخبار اقتصادی:\nقبل از سشن نیویورک، تقویم اقتصادی را چک کن:\nwww.forexfactory.com/calendar'
                    if now.weekday() == 4 and now.day <= 7:
                        msg += '\n\n⚠️ امروز جمعهٔ اول ماه است — روز NFP! نوسان شدید!'
                    try: bot.send_message(CHANNEL_POST, msg)
                    except Exception: pass
                if hm == (15, 30):
                    try: bot.send_message(CHANNEL_POST, '🟢 سشن نیویورک باز شد!')
                    except Exception: pass
                if hm == (19, 30):
                    try: bot.send_message(CHANNEL_POST, '🔴 سشن لندن بسته شد — نیویورک ادامه دارد.')
                    except Exception: pass
                if hm == (9, 0) and today() != last_quote_day:
                    last_quote_day = today()
                    idx = now.timetuple().tm_yday % len(QUOTES)
                    try: bot.send_message(CHANNEL_POST, '🌟 جملهٔ روز:\n\n💡 '+QUOTES[idx]+'\n\n🤖 Forexin Site Bot')
                    except Exception: pass
        except Exception:
            pass
        _t.sleep(20)

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
    try: bot.process_new_updates(telebot.types.Update.de_json(request.get_json()))
    except Exception: pass
    return 'ok'

threading.Thread(target=notifier, daemon=True).start()

if __name__ == '__main__':
    if os.environ.get('PORT'):
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '10000')))
    else:
        print('🚀 Bot started in polling mode')
        bot.infinity_polling()
