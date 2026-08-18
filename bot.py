import os
import telebot
from telebot import types
from flask import Flask, request

TOKEN = '8978486498:AAGjeMhm0f6BMjVX2JA7LbrN4Bcv6M_LET8'
bot = telebot.TeleBot(TOKEN)

SITE = 'https://mbms-1356.github.io/forexin-site-/'
CHANNEL = 'https://t.me/forexin_turkaslanifree'
CHANNEL_POST = '@forexin_turkaslanifree'
QUIZ = SITE + 'quiz.html'

ADMIN = None
USERS = set()
state = {}
used_codes = set()

FAQ = [
('پیپ','پیپ (Pip) کوچک‌ترین واحد تغییر قیمت است؛ معمولاً رقم چهارم اعشار (۰٫۰۰۰۱).'),
('لات','لات (Lot) واحد حجم معامله است؛ لات استاندارد = ۱۰۰۰۰ واحد ارز پایه.'),
('اهرم','اهرم (Leverage) سرمایهٔ قرضی از بروکر است؛ سود و زیان را چند برابر می‌کند — مراقب!'),
('مارجین','مارجین وثیقه‌ای است که بروکر برای باز نگه داشتن معاملهٔ اهرمی نگه می‌دارد.'),
('استاپ','استاپ‌لاس (Stop Loss) یعنی خروج خودکار در حد زیان — بیمهٔ زندگی معامله‌گر! هرگز بدون استاپ وارد نشو.'),
('تارگت','تارگت (Take Profit) یعنی خروج خودکار در سود هدف. در LIT تارگت = نقدینگی مقابل (استخر بعدی).'),
('اسپرد','اسپرد فاصلهٔ قیمت خرید و فروش است؛ هزینهٔ بروکر.'),
('سشن','سشن‌ها به وقت تهران: سیدنی ۰۰:۳۰ | توکیو ۰۳:۳۰ | لندن ۱۰:۳۰ | نیویورک ۱۵:۳۰'),
('بروکر','بروکر رسمی ما WM Markets است؛ لینک IB به‌زودی در سایت.'),
('vip','VIP با دعوت یا اشتراک فعال می‌شود؛ اگر کد آزمون داری، دکمهٔ «فعال‌سازی کد VIP» را بزن.'),
('دعوت','برای آکادمی بیس به ربات اصلی برو: @TurkaslaniFx_bot — دو دوست واقعی دعوت کن.'),
('سایت','آدرس سایت: ' + SITE),
('آزمون','آزمون LIT + هدیهٔ ۷ روز VIP: ' + QUIZ),
('واژه','واژه‌نامهٔ ۳۰ اصطلاح کلیدی: ' + SITE + 'vajeh.html'),
('کندل','آموزش کامل کندل‌استیک با ورود و تارگت: ' + SITE + 'candle.html'),
('پترن','پترن‌های کلاسیک (سر و شانه، پرچم، دوقلوها): ' + SITE + 'patterns.html'),
('lit','استراتژی LIT یعنی Liquidity، Imbalance، Trend — آموزش کامل: ' + SITE + 'lit.html'),
('تله','تله (Trap) ابزار پول هوشمند برای شکار نقدینگی است؛ سایه‌های بلند یعنی تله! یادگیری: ' + SITE + 'lit.html'),
('بیلدآپ','بیلدآپ یعنی تجمع نقدینگی؛ جلوی بیلدآپ خلاف جهت نایست — شانس ریورسال کم است.'),
('سایکل','سایکل ۹۰ دقیقه: هر ۹۰ دقیقه یک جریان سفارش الگوریتمی جدید؛ سفارش اصلی در سقف سایکل.'),
('ریسک','دی‌تریدر: ۰٫۲۵ تا ٫۵٪ | اسکالپر: ۰٫۵ تا ۱٪ | سوینگ: ۱ تا ۲٪ — هرگز بیشتر!'),
('پشتیبانی','برای پشتیبانی به ادمین پیام بده: @FX_Dow_Jones یا دکمهٔ «بازخورد به ادمین» را بزن.'),
('کانال','کانال سیگنال رایگان: ' + CHANNEL)
]

def menu():
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton('🎟️ فعال‌سازی کد VIP', callback_data='code'),
          types.InlineKeyboardButton('❓ سؤالات متداول', callback_data='faq'))
    m.add(types.InlineKeyboardButton('💬 بازخورد به ادمین', callback_data='fb'),
          types.InlineKeyboardButton('🧠 آزمون LIT', url=QUIZ))
    m.add(types.InlineKeyboardButton('🌐 وب‌سایت', url=SITE),
          types.InlineKeyboardButton('📢 کانال سیگنال', url=CHANNEL))
    return m

@bot.message_handler(commands=['start'])
def start(m):
    global ADMIN
    uid = m.from_user.id
    if m.chat.type != 'private':
        bot.send_message(m.chat.id, 'سلام! 🤖 دستیار سایت فارکسین هستم؛ برای سؤالات خصوصی، پی‌وی پیام بده.')
        return
    args = m.text.split()
    if ADMIN is None:
        ADMIN = uid
        bot.send_message(uid, '🛠️ شما ادمین ربات سایت شدید!\nلیدها و بازخوردها همین‌جا می‌آید.\n📢 ارسال به کانال: /post متن\n👥 اطلاع‌رسانی به اعضا: /broadcast متن')
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
    bot.send_message(uid, 'سلام ' + (m.from_user.first_name or 'دوست عزیز') + '! 🌟\nدستیار سایت فارکسین ترک‌اصلانی هستم.\n👇 چه کمکی کنم؟', reply_markup=menu())

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
    elif c.data.startswith('f'):
        bot.send_message(uid, '💡 ' + FAQ[int(c.data[1:])][1])
    bot.answer_callback_query(c.id)

@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/'), content_types=['text'])
def txt(m):
    uid = m.from_user.id
    is_group = m.chat.type in ('group', 'supergroup')
    t = m.text.strip()
    # جستجوی سؤالات متداول (هم خصوصی، هم گروه)
    for k,v in FAQ:
        if k in t:
            bot.send_message(m.chat.id, '💡 ' + v)
            return
    if is_group:
        return  # در گروه، فقط به سؤالات شناخته‌شده جواب بده
    st = state.get(uid)
    if st:
        step = st['step']
        if step == 'getcode':
            code = t
            if code in used_codes:
                bot.send_message(uid, '⚠️ این کد قبلاً استفاده شده.')
            else:
                state[uid] = {'step':'name','code':code}
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
        bot.send_message(uid, '📨 پیام فورواردی‌ات رسید!\nاگر سؤال داری، خودت با کلمه‌های کلیدی بنویس (مثلاً «پیپ»، «سشن»، «VIP») یا از منو انتخاب کن 👇', reply_markup=menu())
        return
    bot.send_message(uid, '🤔 متوجه نشدم؛ از منو انتخاب کن 👇', reply_markup=menu())

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

# ---------- وب‌سرور + وب‌هوک (برای هاست) / پولینگ (برای گوشی) ----------
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

if __name__ == '__main__':
    if os.environ.get('PORT'):
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '10000')))
    else:
        print('🚀 Bot started in polling mode')
        bot.infinity_polling()
