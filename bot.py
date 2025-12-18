import asyncio, sqlite3, os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

# ================= SOZLAMALAR =================
BOT_TOKEN = "8291345152:AAEeOP-2U9AfYvwCFnxrwDoFg7sjyWGwqGk"
API_ID = 32460736
API_HASH = "285e2a8556652e6f4ffdb83658081031"
ADMIN_IDS = [6731395876, 6302873072]

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

os.makedirs("sessions", exist_ok=True)

# ================= DATABASE =================
db = sqlite3.connect("bot.db")
sql = db.cursor()

sql.execute("""CREATE TABLE IF NOT EXISTS users (
user_id INTEGER PRIMARY KEY,
approved INTEGER,
expire TEXT)""")

sql.execute("""CREATE TABLE IF NOT EXISTS sessions (
user_id INTEGER,
phone TEXT)""")

sql.execute("""CREATE TABLE IF NOT EXISTS groups (
user_id INTEGER,
phone TEXT,
chat_id INTEGER,
title TEXT)""")

sql.execute("""CREATE TABLE IF NOT EXISTS sender (
user_id INTEGER,
phone TEXT,
text TEXT,
photo TEXT,
interval INTEGER,
active INTEGER)""")

db.commit()

# ================= YORDAMCHI =================
def is_admin(uid): return uid in ADMIN_IDS

def is_allowed(uid):
    if is_admin(uid): return True
    sql.execute("SELECT approved,expire FROM users WHERE user_id=?", (uid,))
    r = sql.fetchone()
    if not r: return False
    if r[0] == 0: return False
    return datetime.strptime(r[1], "%Y-%m-%d") > datetime.now()

def main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📱 Raqamlar", "👥 Guruhlar")
    kb.add("📤 Habar yuborish")
    return kb

back = ReplyKeyboardMarkup(resize_keyboard=True).add("⬅️ Ortga")

clients = {}
send_tasks = {}

# ================= START =================
@dp.message_handler(commands=["start"])
async def start(m: types.Message):
    if is_allowed(m.from_user.id):
        await m.answer("✅ Bot ishga tushdi", reply_markup=main_menu())
    else:
        kb = ReplyKeyboardMarkup(resize_keyboard=True).add("📨 Adminga so‘rov")
        await m.answer("Botdan foydalanish uchun admin ruxsati kerak", reply_markup=kb)

# ================= ADMIN SO‘ROV =================
@dp.message_handler(text="📨 Adminga so‘rov")
async def req(m: types.Message):
    for a in ADMIN_IDS:
        try:
            await bot.send_message(
                a,
                f"👤 @{m.from_user.username or m.from_user.id}\n"
                f"Botdan foydalanish uchun so‘rov yubordi.\n\n"
                f"Necha oy ruxsat berilsin? (faqat raqam)"
            )
        except Exception as e:
            print(f"Admin {a} ga yuborilmadi:", e)

    await m.answer("⏳ So‘rov yuborildi. Admin javobini kuting.")


@dp.message_handler(lambda m: m.text.isdigit() and is_admin(m.from_user.id))
async def admin_answer(m: types.Message):
    months = int(m.text)
    expire = (datetime.now()+timedelta(days=30*months)).strftime("%Y-%m-%d")
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"ok|{expire}"),
        InlineKeyboardButton("❌ Rad", callback_data="no")
    )
    await m.answer(f"{months} oyga ruxsat berilsinmi?", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("ok"))
async def ok(c: types.CallbackQuery):
    expire = c.data.split("|")[1]
    uid = c.message.reply_to_message.from_user.id
    sql.execute("REPLACE INTO users VALUES (?,?,?)", (uid,1,expire))
    db.commit()
    await bot.send_message(uid, "✅ Admin sizni tasdiqladi")
    await c.message.edit_text("Tasdiqlandi")

@dp.callback_query_handler(text="no")
async def no(c: types.CallbackQuery):
    uid = c.message.reply_to_message.from_user.id
    await bot.send_message(uid, "❌ Admin sizni rad etdi")
    await c.message.edit_text("Rad etildi")

# ================= RAQAMLAR =================
@dp.message_handler(text="📱 Raqamlar")
async def phones(m: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    sql.execute("SELECT phone FROM sessions WHERE user_id=?", (m.from_user.id,))
    for p in sql.fetchall(): kb.add(p[0])
    kb.add("➕ Raqam qo‘shish", "⬅️ Ortga")
    await m.answer("📱 Raqamlar", reply_markup=kb)

@dp.message_handler(text="➕ Raqam qo‘shish")
async def add_phone(m): await m.answer("+998 bilan kiriting", reply_markup=back)

@dp.message_handler(lambda m: m.text.startswith("+998"))
async def phone(m):
    phone = m.text
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
    await client.connect()
    await client.send_code_request(phone)
    clients[m.from_user.id]=(client,phone)
    await m.answer("📨 Kodni kiriting")

@dp.message_handler(lambda m: m.from_user.id in clients)
async def code(m):
    client,phone = clients[m.from_user.id]
    await client.sign_in(phone,m.text)
    sql.execute("INSERT INTO sessions VALUES (?,?)",(m.from_user.id,phone))
    db.commit()
    await m.answer("✅ Session ulandi")
    await phones(m)

# ================= GURUHLAR =================
@dp.message_handler(text="👥 Guruhlar")
async def groups(m):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    sql.execute("SELECT phone FROM sessions WHERE user_id=?", (m.from_user.id,))
    for p in sql.fetchall(): kb.add(p[0])
    kb.add("⬅️ Ortga")
    await m.answer("Session tanlang", reply_markup=kb)

@dp.message_handler(lambda m: m.text.startswith("+998"))
async def list_groups(m):
    phone = m.text
    client = TelegramClient(f"sessions/{phone}", API_ID, API_HASH)
    await client.connect()
    dialogs = await client(GetDialogsRequest(
        offset_date=None, offset_id=0, offset_peer=InputPeerEmpty(),
        limit=200, hash=0))
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    for d in dialogs.chats:
        if d.megagroup or d.broadcast:
            kb.add(d.title)
            sql.execute("INSERT OR IGNORE INTO groups VALUES (?,?,?,?)",
                        (m.from_user.id, phone, d.id, d.title))
    db.commit()
    kb.add("⬅️ Ortga")
    await m.answer("Guruhlar qo‘shildi", reply_markup=kb)

# ================= HABAR YUBORISH =================
@dp.message_handler(text="📤 Habar yuborish")
async def send_menu(m):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    sql.execute("SELECT phone FROM sessions WHERE user_id=?", (m.from_user.id,))
    for p in sql.fetchall(): kb.add(p[0])
    kb.add("⬅️ Ortga")
    await m.answer("Session tanlang", reply_markup=kb)

@dp.message_handler(lambda m: m.text.startswith("+998"))
async def msg_text(m):
    await m.answer("Habar kiriting (rasm ixtiyoriy)")

@dp.message_handler(content_types=["text","photo"])
async def save_msg(m):
    text = m.caption or m.text
    photo = None
    if m.photo:
        photo = m.photo[-1].file_id
        await m.answer("📷 Rasm saqlandi, matn kiriting")
        return
    sql.execute("INSERT OR REPLACE INTO sender VALUES (?,?,?,?,?,?)",
        (m.from_user.id,m.text,text,photo,0,0))
    db.commit()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("5","10","15","20")
    await m.answer("Interval (minut)", reply_markup=kb)

@dp.message_handler(lambda m: m.text in ["5","10","15","20"])
async def interval(m):
    sql.execute("UPDATE sender SET interval=? WHERE user_id=?",
                (int(m.text)*60,m.from_user.id))
    db.commit()
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("▶️ Boshlash","⏹ To‘xtatish","⬅️ Ortga")
    await m.answer("Tayyor", reply_markup=kb)

async def sender_loop(uid):
    while True:
        sql.execute("SELECT phone,text,photo,interval FROM sender WHERE user_id=? AND active=1",(uid,))
        r = sql.fetchone()
        if not r: break
        phone,text,photo,interval = r
        client = TelegramClient(f"sessions/{phone}",API_ID,API_HASH)
        await client.connect()
        sql.execute("SELECT chat_id FROM groups WHERE user_id=? AND phone=?",(uid,phone))
        for g in sql.fetchall():
            if photo:
                await client.send_file(g[0],photo,caption=text)
            else:
                await client.send_message(g[0],text)
        await asyncio.sleep(interval)

@dp.message_handler(text="▶️ Boshlash")
async def start_send(m):
    sql.execute("UPDATE sender SET active=1 WHERE user_id=?", (m.from_user.id,))
    db.commit()
    send_tasks[m.from_user.id]=asyncio.create_task(sender_loop(m.from_user.id))
    await m.answer("🚀 Yuborish boshlandi", reply_markup=main_menu())

@dp.message_handler(text="⏹ To‘xtatish")
async def stop_send(m):
    sql.execute("UPDATE sender SET active=0 WHERE user_id=?", (m.from_user.id,))
    db.commit()
    if m.from_user.id in send_tasks:
        send_tasks[m.from_user.id].cancel()
    await m.answer("⛔ To‘xtatildi", reply_markup=main_menu())

@dp.message_handler(text="⬅️ Ortga")
async def back_menu(m): await m.answer("Bosh menyu", reply_markup=main_menu())

# ================= RUN =================
if __name__ == "__main__":
    executor.start_polling(dp)
