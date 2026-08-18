import telebot
from telebot import types
from flask import Flask, request

TOKEN = '8978486498:AAGjeMhm0f6BMjVX2JA7LbrN4Bcv6M_LET8'
bot = telebot.TeleBot(TOKEN)

SITE = 'https://mbms-1356.github.io/forexin-site-/'
CHANNEL = 'https://t.me/forexin_turkaslanifree'
QUIZ = SITE + 'quiz.html'

ADMIN = None
USERS = set()
state = {}
used_codes = set()

FAQ = [
('پیپ','پیپ (Pip) کوچک‌ترین واحد تغییر قیمت است؛ معمولاً رقم چهارم اعشار (۰٫۰۰۰۱).'),
('لات','لات (Lot) واحد حجم معامله است؛ لات استاندارد = ۱۰۰۰۰۰ واحد ارز پایه.'),
('اهرم','اهرم (Leverage) سرمایهٔ قرضی از بروکر است؛ سود و زیان را چند برابر می‌کند — مراقب!'),
('سشن','سشن‌ها به وقت تهران: سیدنی ۰۰:۳۰ | توکیو ۰۳:۳۰ | لندن ۱۰:۳۰ | نیویورک ۱۵:۳۰'),
('بروکر','بروکر رسمی ما WM Markets است؛ لینک IB به‌زودی در سایت.'),
('vip','VIP با دعوت یا اشتراک فعال می‌شود؛ اگر کد آزمون داری، دکمهٔ «فعال‌سازی کد VIP» را بزن.'),
('دعوت','برای آکادمی بیس به ربات اصلی برو: @TurkaslaniFx_bot — دو دوست واقعی دعوت کن.'),
('سایت','آدرس سایت: ' + SITE),
('آزمون','آزمون LIT + هدیه: ' + QUIZ),
('اسپرد','اسپرد فاصلهٔ قیمت خرید و فروش است؛ هزینهٔ بروکر.')
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
    args = m.text.split()
    if ADMIN is None:
        ADMIN = uid
        bot.send_message(uid, '🛠️ شما ادمین ربات سایت شدید!\nلیدها و بازخوردها همین‌جا می‌آید.\nاطلاع‌رسانی: /broadcast متن')
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
    st = state.get(uid)
    if st:
        step = st['step']
        if step == 'getcode':
            code = m.text.strip()
            if code in used_codes:
                bot.send_message(uid, '⚠️ این کد قبلاً استفاده شده.')
            else:
                state[uid] = {'step':'name','code':code}
                bot.send_message(uid, '✅ کد معتبر است!\nنام و نام خانوادگی‌ات را بنویس:')
            return
        if step == 'name':
            st['name'] = m.text.strip()
            st['step'] = 'phone'
            bot.send_message(uid, '📱 حالا شمارهٔ تلگرامت را بفرست:')
            return
        if step == 'phone':
            used_codes.add(st['code'])
            if ADMIN:
                bot.send_message(ADMIN, '🎁 لید جدید آزمون!\n👤 ' + st['name'] + '\n📱 ' + m.text.strip() + '\n🎟️ کد: ' + st['code'])
            del state[uid]
            bot.send_message(uid, '🎉 عالی! کدت فعال شد.\n۷ روز VIP رایگان — ادمین به‌زودی پیام می‌دهد. ✅', reply_markup=menu())
            return
        if step == 'fb':
            if ADMIN:
                bot.send_message(ADMIN, '💬 بازخورد کاربر ' + str(uid) + ':\n' + m.text)
            del state[uid]
            bot.send_message(uid, '✅ پیامت به ادمین رسید. ممنون! 🙏', reply_markup=menu())
            return
    t = m.text.strip()
    for k,v in FAQ:
        if k in t:
            bot.send_message(uid, '💡 ' + v)
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

# ---------- وب‌سرور + وب‌هوک (برای Render) ----------
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
    app.run(host='0.0.0.0', port=10000)
