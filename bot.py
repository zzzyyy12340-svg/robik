from rubka import Robot
from rubka.context import Message
from rubka.keypad import ChatKeypadBuilder
import random
import time
import logging
import requests
import sqlite3
import os
import qrcode
import urllib.parse
import re
from google import genai
from datetime import datetime
import pytz
import jdatetime

# ================= تنظیمات =================
BOT_TOKEN = "CBHABJ0UMTEHUGXEPHQHHQBNQNJOELKPCHOPKHZSQJVIWFQTMHPVZPSWZGYHJBCT"
ADMIN_ID = "u0Jxj6A07e15668fcbda51fff7fa3ce0"
ADMIN_USERNAME = "Y__Sh_1"
AI_API_KEY = "AQ.Ab8RN6Ikm1km0mAsBfnNFT-q6eWaFuzVF-jD3RwblVCnjXpsSA"

logging.basicConfig(level=logging.INFO)
bot = Robot(token=BOT_TOKEN)

# ================= دیتابیس =================
def get_db():
    conn = sqlite3.connect('rubika_bot.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS users")
    c.execute('''CREATE TABLE users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        is_banned INTEGER DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

# ================= دیتا =================
JOKES = ["😂 چرا برنامه‌نویس‌ها عینک می‌زنن؟ چون C# می‌بینن!", "🤣 به یه هکر گفتن چرا هک نمی‌کنی؟ گفت پینگم بالاست!"]
RIDDLES = ["🧠 چیست که هرچه از آن بگیری، بزرگ‌تر می‌شود؟ (چاله)", "🧠 صبح روی چهار پا، ظهر دو پا، شب سه پا؟ (انسان)"]
FAL_HAFEZ = ["🍀 **فال حافظ:**\n\nدوش وقت سحر از غصه نجاتم دادند\n(تعبیر: خبر خوشی به تو می‌رسد.)"]
COUNTRIES = {"Asia/Tehran": "🇮🇷 ایران", "America/New_York": "🇺🇸 آمریکا", "Europe/London": "🇬🇧 انگلیس", "Europe/Berlin": "🇩🇪 آلمان", "Asia/Tokyo": "🇯🇵 ژاپن"}

# ================= منوها =================
def get_main_keypad():
    builder = ChatKeypadBuilder()
    builder.row(builder.button(id="btn_clock", text="🕰 ساعت"), builder.button(id="btn_weather", text="🌤 هواشناسی"))
    builder.row(builder.button(id="btn_ai", text="🤖 هوش مصنوعی"), builder.button(id="btn_img", text="🎨 ساخت عکس"))
    builder.row(builder.button(id="btn_calendar", text="📅 تقویم شمسی"), builder.button(id="btn_translate", text="🌐 ترجمه"))
    builder.row(builder.button(id="btn_tools", text="🛠 ابزارها"), builder.button(id="btn_games", text="🎮 بازی‌ها"))
    builder.row(builder.button(id="btn_joke", text="😂 جوک"), builder.button(id="btn_admin_panel", text="👑 پنل مدیریت"))
    return builder.build()

def get_tools_keypad():
    builder = ChatKeypadBuilder()
    builder.row(builder.button(id="tool_calc", text="🧮 ماشین‌حساب"), builder.button(id="tool_qr", text="📸 ساخت QR"))
    builder.row(builder.button(id="tool_date", text="📅 مبدل تاریخ"), builder.button(id="tool_pass", text="🔑 پسورد ساز"))
    builder.row(builder.button(id="tool_unit", text="📏 مبدل واحد"), builder.button(id="btn_back", text="🔙 بازگشت"))
    return builder.build()

def get_games_keypad():
    builder = ChatKeypadBuilder()
    builder.row(builder.button(id="btn_dice", text="🎲 تاس"), builder.button(id="btn_coin", text="🪙 شیر یا خط"))
    builder.row(builder.button(id="btn_riddle", text="🧠 معما"), builder.button(id="btn_guess", text="🔢 حدس عدد"))
    builder.row(builder.button(id="btn_back", text="🔙 بازگشت"))
    return builder.build()

def get_clocks_keypad():
    builder = ChatKeypadBuilder()
    keys = list(COUNTRIES.keys())
    for i in range(0, len(keys), 2):
        if i + 1 < len(keys):
            builder.row(builder.button(id=f"clock_{keys[i]}", text=COUNTRIES[keys[i]]), builder.button(id=f"clock_{keys[i+1]}", text=COUNTRIES[keys[i+1]]))
        else:
            builder.row(builder.button(id=f"clock_{keys[i]}", text=COUNTRIES[keys[i]]))
    builder.row(builder.button(id="btn_back", text="🔙 بازگشت"))
    return builder.build()

def get_admin_keypad():
    builder = ChatKeypadBuilder()
    builder.row(builder.button(id="admin_stats", text="📊 آمار"), builder.button(id="admin_list", text="👥 لیست کاربران"))
    builder.row(builder.button(id="admin_ban", text="🚫 بن"), builder.button(id="admin_unban", text="✅ آنبن"))
    builder.row(builder.button(id="admin_broadcast", text="📢 پیام همگانی"), builder.button(id="admin_msg", text="✉️ پیام به کاربر"))
    builder.row(builder.button(id="admin_back", text="🔙 بازگشت"))
    return builder.build()

# ================= توابع کمکی =================
def get_weather(city):
    try:
        geo = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1", timeout=10).json()
        if not geo.get("results"): return "❌ شهر پیدا نشد."
        lat, lon = geo["results"][0]["latitude"], geo["results"][0]["longitude"]
        w = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m", timeout=10).json()
        c = w.get("current", {})
        return f"🌤 **آب و هوای {geo['results'][0]['name']}:**\n\n🌡 دما: {c.get('temperature_2m', '?')}°C\n💧 رطوبت: {c.get('relative_humidity_2m', '?')}%"
    except Exception: return "❌ خطا در آب و هوا."

def translate_text(text):
    try:
        res = requests.get(f"https://api.mymemory.translated.net/get?q={text}&langpair=fa|en", timeout=10).json()
        return f"🌐 **ترجمه:**\n\n`{res.get('responseData', {}).get('translatedText', 'خطا')}`"
    except: return "❌ خطا در ترجمه."

def ask_ai(text):
    try:
        client = genai.Client(api_key=AI_API_KEY)
        response = client.models.generate_content(model="gemini-2.0-flash", contents=f"به زبان فارسی و مفید جواب بده: {text}")
        return f"🤖 **پاسخ:**\n\n{response.text}"
    except Exception as e:
        logging.error(f"AI: {e}")
        return "❌ خطا در هوش مصنوعی (VPN را روشن کنید)."

def generate_image(prompt):
    try:
        encoded = urllib.parse.quote(prompt[:500])
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=800&height=800&nologo=true"
        r = requests.get(url, timeout=60)
        if r.status_code == 200 and len(r.content) > 1000:
            filename = f"img_{random.randint(1000,9999)}.jpg"
            with open(filename, 'wb') as f: f.write(r.content)
            return filename
        return None
    except: return None

def is_admin(username, user_id):
    if str(user_id).strip() == str(ADMIN_ID).strip(): return True
    if username and username.strip().lower().replace('@', '') == ADMIN_USERNAME.strip().lower(): return True
    return False

# ================= تقویم شمسی =================
def get_shamsi_calendar():
    """دریافت تاریخ شمسی با روز هفته و مناسبت‌ها"""
    try:
        now = jdatetime.datetime.now()
        weekdays = ['شنبه', 'یک‌شنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنج‌شنبه', 'جمعه']
        months = ['فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند']
        
        weekday = weekdays[now.weekday()]
        month_name = months[now.month - 1]
        
        # مناسبت‌های تقریبی (فقط چند نمونه)
        events = {
            (1, 1): "🌸 عید نوروز",
            (1, 13): "🌿 سیزده‌بدر",
            (2, 2): "📚 روز معلم",
            (3, 14): "🕊 رحلت امام خمینی",
            (7, 13): "🎓 روز دانشجو",
            (11, 22): "✊ پیروزی انقلاب",
            (12, 29): "🧹 روز ملی شدن صنعت نفت"
        }
        
        event = events.get((now.month, now.day), "")
        event_text = f"\n\n🎉 **مناسبت:** {event}" if event else ""
        
        return (
            f"📅 **تقویم شمسی:**\n\n"
            f"🗓 تاریخ: **{now.year}/{now.month:02d}/{now.day:02d}**\n"
            f"📆 روز هفته: **{weekday}**\n"
            f"🌙 ماه: **{month_name}**\n"
            f"⏰ ساعت: {datetime.now().strftime('%H:%M:%S')}"
            f"{event_text}"
        )
    except Exception as e:
        return f"❌ خطا در تقویم: {e}"

# ================= مدیریت گروه =================
def get_replied_user(message):
    if hasattr(message, 'reply_to_message_id') and message.reply_to_message_id:
        if hasattr(message, 'raw_data') and message.raw_data:
            replied = message.raw_data.get('reply_to_message', {})
            if replied and 'sender_id' in replied: return replied['sender_id']
    return None

def handle_group_admin(bot, message, command):
    user_id = str(message.sender_id)
    username = getattr(message, 'sender_username', '') or ""
    if not is_admin(username, user_id):
        message.reply("⛔ فقط ادمین ربات می‌تواند از این دستور استفاده کند."); return
    target_id = get_replied_user(message)
    if not target_id:
        message.reply("❌ لطفاً روی پیام کاربر مورد نظر ریپلای بزنید."); return
    try:
        if command == 'ban': bot.ban_chat_member(chat_id=message.chat_id, user_id=target_id); message.reply(f"✅ کاربر `{target_id}` بن شد.")
        elif command == 'kick': bot.kick_chat_member(chat_id=message.chat_id, user_id=target_id); message.reply(f"✅ کاربر `{target_id}` اخراج شد.")
        elif command == 'promote': bot.promote_chat_member(chat_id=message.chat_id, user_id=target_id, can_delete_messages=True); message.reply(f"✅ کاربر `{target_id}` ادمین شد.")
    except Exception as e: message.reply(f"❌ خطا: {e}")

# ================= هندلرها =================
@bot.on_message(commands=["start"])
def start_handler(bot: Robot, message: Message):
    user_id = str(message.sender_id)
    username = getattr(message, 'sender_username', '') or ""
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    user = conn.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if user and user['is_banned'] == 1:
        message.reply("⛔ شما مسدود شده‌اید."); return
    message.reply_keypad("🌟 **به ربات جامع خوش آمدید!**\n\nیک گزینه را انتخاب کنید:", get_main_keypad())

@bot.on_message(commands=["ban"])
def ban_handler(bot: Robot, message: Message): handle_group_admin(bot, message, 'ban')
@bot.on_message(commands=["kick"])
def kick_handler(bot: Robot, message: Message): handle_group_admin(bot, message, 'kick')
@bot.on_message(commands=["promote"])
def promote_handler(bot: Robot, message: Message): handle_group_admin(bot, message, 'promote')

@bot.on_callback()
def callback_handler(bot: Robot, message: Message):
    btn_id = getattr(message.aux_data, 'button_id', '') if hasattr(message, 'aux_data') else ''
    user_id = str(message.sender_id)
    username = getattr(message, 'sender_username', '') or ""
    if not hasattr(bot, 'user_states'): bot.user_states = {}
    if not hasattr(bot, 'game_states'): bot.game_states = {}
    
    conn = get_db()
    user = conn.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if user and user['is_banned'] == 1 and not is_admin(username, user_id):
        message.reply("⛔ شما مسدود هستید."); return

    if btn_id == "btn_clock": message.reply_keypad("🌍 **انتخاب کشور:**", get_clocks_keypad())
    elif btn_id.startswith("clock_"):
        tz_str = btn_id.replace("clock_", "")
        try:
            now = datetime.now(pytz.timezone(tz_str))
            message.reply(f"🕰 **ساعت {COUNTRIES.get(tz_str, tz_str)}:**\n\n`{now.strftime('%H:%M:%S | %Y-%m-%d')}`")
        except: message.reply("❌ خطا در ساعت.")
    elif btn_id == "btn_weather": bot.user_states[user_id] = 'weather'; message.reply("🌤 نام شهر را بفرستید:")
    elif btn_id == "btn_ai": bot.user_states[user_id] = 'ai'; message.reply("🤖 سوال خود را بپرسید:")
    elif btn_id == "btn_img": bot.user_states[user_id] = 'image'; message.reply("🎨 توضیح عکس را بفرستید:")
    elif btn_id == "btn_fal": message.reply(random.choice(FAL_HAFEZ))
    elif btn_id == "btn_calendar": message.reply(get_shamsi_calendar())
    elif btn_id == "btn_translate": bot.user_states[user_id] = 'translate'; message.reply("🌐 متن فارسی را بفرستید:")
    elif btn_id == "btn_joke": message.reply(f"😂 **جوک:**\n\n{random.choice(JOKES)}")
    elif btn_id == "btn_tools": message.reply_keypad("🛠 **ابزارها:**", get_tools_keypad())
    elif btn_id == "btn_games": message.reply_keypad("🎮 **بازی‌ها:**", get_games_keypad())
    elif btn_id == "btn_back": message.reply_keypad("🏠 منوی اصلی:", get_main_keypad())

    elif btn_id == "tool_calc": bot.user_states[user_id] = 'calc'; message.reply("🧮 عبارت ریاضی را بفرستید:")
    elif btn_id == "tool_qr": bot.user_states[user_id] = 'qr'; message.reply("📸 متن یا لینک را بفرستید:")
    elif btn_id == "tool_date": bot.user_states[user_id] = 'date'; message.reply("📅 تاریخ شمسی را بفرستید (مثال: 1402/05/15):")
    elif btn_id == "tool_pass": bot.user_states[user_id] = 'password'; message.reply("🔑 طول پسورد را بفرستید (مثال: 12):")
    elif btn_id == "tool_unit": bot.user_states[user_id] = 'unit'; message.reply("📏 مقدار و واحد را بفرستید (مثال: 10 km):")

    elif btn_id == "btn_dice": message.reply(f"🎲 شما تاس انداختید: **{random.randint(1, 6)}**")
    elif btn_id == "btn_coin": message.reply(f"🪙 نتیجه: **{random.choice(['🦁 شیر', '🦅 خط'])}**")
    elif btn_id == "btn_riddle": message.reply(f"🧠 **معما:**\n\n{random.choice(RIDDLES)}")
    elif btn_id == "btn_guess":
        bot.game_states[user_id] = random.randint(1, 100); message.reply("🔢 یک عدد بین ۱ تا ۱۰۰ حدس بزنید:")

    elif btn_id == "btn_admin_panel" and is_admin(username, user_id): message.reply_keypad("👑 **پنل مدیریت:**", get_admin_keypad())
    elif btn_id == "admin_stats" and is_admin(username, user_id):
        conn = get_db(); total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]; banned = conn.execute("SELECT COUNT(*) FROM users WHERE is_banned=1").fetchone()[0]; conn.close()
        message.reply(f"📊 کل: {total}\n🚫 بن: {banned}\n✅ فعال: {total - banned}")
    elif btn_id == "admin_list" and is_admin(username, user_id):
        conn = get_db(); users = conn.execute("SELECT user_id, username, is_banned FROM users LIMIT 30").fetchall(); conn.close()
        text = "👥 **کاربران:**\n"
        for u in users: text += f"{'🚫' if u['is_banned'] else '✅'} `{u['user_id']}`\n"
        message.reply(text)
    elif btn_id == "admin_ban" and is_admin(username, user_id): bot.user_states[user_id] = 'admin_ban'; message.reply("🚫 آیدی کاربر را بفرستید:")
    elif btn_id == "admin_unban" and is_admin(username, user_id): bot.user_states[user_id] = 'admin_unban'; message.reply("✅ آیدی کاربر را بفرستید:")
    elif btn_id == "admin_broadcast" and is_admin(username, user_id): bot.user_states[user_id] = 'admin_broadcast'; message.reply("📢 متن پیام همگانی را بفرستید:")
    elif btn_id == "admin_msg" and is_admin(username, user_id): bot.user_states[user_id] = 'admin_msg'; message.reply("✉️ آیدی کاربر و متن پیام را بفرستید (مثال: u0... سلام):")
    elif btn_id == "admin_back" and is_admin(username, user_id): message.reply_keypad("🏠 منوی اصلی:", get_main_keypad())

@bot.on_message()
def text_handler(bot: Robot, message: Message):
    if not message.text or message.text.startswith('/'): return
    user_id = str(message.sender_id)
    username = getattr(message, 'sender_username', '') or ""
    if not hasattr(bot, 'user_states'): bot.user_states = {}
    state = bot.user_states.get(user_id, '')

    if state == 'weather': bot.user_states[user_id] = ''; message.reply(get_weather(message.text))
    elif state == 'translate': bot.user_states[user_id] = ''; message.reply(translate_text(message.text))
    elif state == 'ai': bot.user_states[user_id] = ''; message.reply(ask_ai(message.text))
    elif state == 'image':
        bot.user_states[user_id] = ''; message.reply("⏳ در حال ساخت عکس...")
        img_file = generate_image(message.text)
        if img_file:
            try: message.reply_image(path=img_file, text=f"🎨 {message.text}")
            except Exception as e: message.reply(f"❌ خطا: {e}")
            finally:
                if os.path.exists(img_file): os.remove(img_file)
        else: message.reply("❌ خطا در ساخت عکس.")
    elif state == 'calc':
        bot.user_states[user_id] = ''
        try:
            if re.match(r'^[\d\+\-\*\/\(\)\.\s]+$', message.text): message.reply(f"🧮 نتیجه: `{eval(message.text)}`")
            else: message.reply("❌ فقط اعداد و عملگر.")
        except: message.reply("❌ خطا.")
    elif state == 'qr':
        bot.user_states[user_id] = ''
        try:
            qr = qrcode.make(message.text); filename = f"qr_{random.randint(1000,9999)}.png"; qr.save(filename)
            message.reply_image(path=filename, text=f"📸 QR: `{message.text}`"); os.remove(filename)
        except Exception as e: message.reply(f"❌ خطا: {e}")
    elif state == 'date':
        bot.user_states[user_id] = ''
        try:
            parts = message.text.split('/')
            if len(parts) == 3: message.reply(f"📅 میلادی تقریبی: {int(parts[0]) + 621}/{parts[1]}/{parts[2]}")
            else: message.reply("❌ فرمت: 1402/05/15")
        except: message.reply("❌ خطا.")
    elif state == 'password':
        bot.user_states[user_id] = ''
        try:
            length = int(message.text)
            import string
            chars = string.ascii_letters + string.digits + "!@#$%^&*"
            pwd = ''.join(random.choice(chars) for _ in range(length))
            message.reply(f"🔑 **پسورد شما:**\n\n`{pwd}`")
        except: message.reply("❌ یک عدد معتبر بفرستید.")
    elif state == 'unit': bot.user_states[user_id] = ''; message.reply("📏 **مبدل واحد:**\n\n(به زودی)")
    elif hasattr(bot, 'game_states') and user_id in bot.game_states:
        try:
            guess = int(message.text); secret = bot.game_states[user_id]
            if guess == secret: message.reply(f"🎉 آفرین! عدد **{secret}** بود."); del bot.game_states[user_id]
            elif guess < secret: message.reply("⬆️ بزرگ‌تر.")
            else: message.reply("⬇️ کوچک‌تر.")
        except ValueError: message.reply("❌ عدد معتبر بفرستید.")
    elif state == 'admin_ban' and is_admin(username, user_id):
        bot.user_states[user_id] = ''
        conn = get_db(); conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (message.text.strip(),)); conn.commit(); conn.close()
        message.reply("✅ کاربر بن شد.")
    elif state == 'admin_unban' and is_admin(username, user_id):
        bot.user_states[user_id] = ''
        conn = get_db(); conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (message.text.strip(),)); conn.commit(); conn.close()
        message.reply("✅ کاربر آنبن شد.")
    elif state == 'admin_broadcast' and is_admin(username, user_id):
        bot.user_states[user_id] = ''
        conn = get_db(); users = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall(); conn.close()
        success = 0
        for u in users:
            try: bot.send_message(u['user_id'], f"📢 **پیام همگانی:**\n\n{message.text}"); success += 1; time.sleep(0.1)
            except: pass
        message.reply(f"✅ ارسال به {success} کاربر.")
    elif state == 'admin_msg' and is_admin(username, user_id):
        bot.user_states[user_id] = ''
        try:
            target, msg = message.text.split(maxsplit=1)
            bot.send_message(target.strip(), f"✉️ **پیام ادمین:**\n\n{msg}"); message.reply("✅ ارسال شد.")
        except: message.reply("❌ فرمت: u0... سلام")

if __name__ == "__main__":
    print("🤖 ربات در حال اجرا...")
    while True:
        try: bot.run()
        except Exception as e: print(f"⚠️ خطا: {e}"); time.sleep(5)
