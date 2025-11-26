# bot.py — для Render Free Web Service (порт 10000)
import asyncio
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta, time
import pytz
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import os
import sys
import aiohttp

CALENDAR_WEBHOOK = "https://script.google.com/macros/s/AKfycbwYowZ-08UQL1Dh0HorTcBB9liso9l64eiuplqPqspwX66YCXMR8DLQWNhVcjNoTB0p/exec"  # ← ваш URL




# ✅ Гарантируем единственный запуск
if "RUNNING" in os.environ:
    print("🔁 Бот уже запущен — выход.")
    sys.exit(0)
os.environ["RUNNING"] = "1"

# 🔑 Настройки
BOT_TOKEN = "8454009227:AAHP3Q1HArGgcr519se0Qye4x7eQp4-cjZ4"
ADMIN_CHAT_ID = 6734540756

# === HTTP сервер для Render (порт 10000) ===
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok","bot":"running"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_HEAD(self):  # ← добавьте этот метод
        if self.path == "/healthz":
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

def run_http_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Запускаем HTTP-сервер в фоновом потоке
threading.Thread(target=run_http_server, daemon=True).start()
print(f"✅ HTTP health server running on port {os.getenv('PORT', 10000)}")

# === Основной бот (aiogram polling) ===
TIMEZONE = pytz.timezone("Asia/Almaty")
WORKING_HOURS = {
    "mon": (time(10, 0), time(20, 0)),
    "tue": (time(10, 0), time(20, 0)),
    "wed": (time(10, 0), time(20, 0)),
    "thu": (time(10, 0), time(20, 0)),
    "fri": (time(10, 0), time(20, 0)),
    "sat": (time(10, 0), time(18, 0)),
    "sun": None
}

class Booking(StatesGroup):
    choosing_service = State()
    entering_name = State()
    entering_phone = State()
    choosing_day = State()
    choosing_time = State()

def get_days_kb():
    now = datetime.now(TIMEZONE)
    buttons = []
    for i in range(14):
        day = now + timedelta(days=i)
        wd = day.strftime("%a").lower()[:3]
        if WORKING_HOURS[wd]:
            text = "Сегодня" if i == 0 else "Завтра" if i == 1 else day.strftime("%d %b")
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"day_{day.strftime('%Y-%m-%d')}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_times_kb(date_str):
    day = datetime.strptime(date_str, "%Y-%m-%d")
    wd = day.strftime("%a").lower()[:3]
    hours = WORKING_HOURS[wd]
    if not hours:
        return None
    start, end = hours
    slots = []
    # ✅ Сделать current aware:
    current = TIMEZONE.localize(datetime.combine(day.date(), start))
    end_dt = TIMEZONE.localize(datetime.combine(day.date(), end))
    while current < end_dt:
        if (current - datetime.now(TIMEZONE)).total_seconds() > 1800:
            slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=60)
    if not slots:
        return None
    buttons = [[InlineKeyboardButton(text=t, callback_data=f"time_{t}")] for t in slots]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="choose_day")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def start(msg: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Записаться", callback_data="book")],
        [InlineKeyboardButton(text="📞 Контакты", callback_data="contact")]
    ])
    await msg.answer("🌸 Добро пожаловать в ASEM PODO @ BEAUTY!", reply_markup=kb)

@dp.callback_query(F.data == "main")
async def main_menu(cb: CallbackQuery, state: FSMContext):
    await start(cb.message, state)

@dp.callback_query(F.data == "book")
async def book(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.choosing_service)
    buttons = [
        [InlineKeyboardButton(text="Медицинская подология", callback_data="srv_Медподология")],
        [InlineKeyboardButton(text="Эстетический маникюр", callback_data="srv_Маникюр")],
        [InlineKeyboardButton(text="Педикюр премиум", callback_data="srv_Педикюр")],
        [InlineKeyboardButton(text="Визаж", callback_data="srv_Визаж")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")]
    ]
    await cb.message.edit_text("Выберите услугу:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data.startswith("srv_"))
async def srv(cb: CallbackQuery, state: FSMContext):
    service = cb.data[4:]
    await state.update_data(service=service)
    await state.set_state(Booking.entering_name)
    await cb.message.edit_text("Введите ваше имя:")

@dp.message(Booking.entering_name)
async def name(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await state.set_state(Booking.entering_phone)
    await msg.answer("Введите ваш телефон:")

@dp.message(Booking.entering_phone)
async def phone(msg: Message, state: FSMContext):
    await state.update_data(phone=msg.text)
    await state.set_state(Booking.choosing_day)
    await msg.answer("Выберите день:", reply_markup=get_days_kb())

@dp.callback_query(F.data.startswith("day_"))
async def day(cb: CallbackQuery, state: FSMContext):
    date = cb.data[4:]
    await state.update_data(date=date)
    await state.set_state(Booking.choosing_time)
    kb = get_times_kb(date)
    if kb:
        await cb.message.edit_text("Выберите время:", reply_markup=kb)
    else:
        await cb.answer("Нет свободного времени в этот день.", show_alert=True)

@dp.callback_query(F.data.startswith("time_"))
async def time(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not 
        await cb.message.answer("⚠️ Сессия устарела. Начните с /start.")
        await state.clear()
        return

    # --- Получение данных ---
    service = data.get("service", "не указана")
    name = data.get("name", "—")
    phone = data.get("phone", "—")
    date_str = data.get("date")
    tm = cb.data[5:]

    if not date_str:
        await cb.message.answer("❌ Не указана дата. Начните с /start.")
        await state.clear()
        return

    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    date_fmt = date_obj.strftime("%d.%m")

    # --- ✅ Отправка в Google Apps Script (календарь) ---
    if CALENDAR_WEBHOOK:
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "name": name,
                    "phone": phone,
                    "date": date_str,
                    "time": tm,
                    "service": service
                }
                async with session.post(CALENDAR_WEBHOOK, json=payload) as resp:
                    result = await resp.json()
                    if result.get("status") == "ok":
                        print(f"✅ Событие создано в Google Calendar: {result.get('eventId')}")
                    else:
                        print(f"⚠️ Ошибка Google Calendar: {result.get('message')}")
                        await bot.send_message(ADMIN_CHAT_ID, f"❌ Не удалось добавить в календарь: {name}")
        except Exception as e:
            print(f"⚠️ Webhook error: {e}")

    # --- Ответ клиенту и админу ---
    await cb.message.edit_text(
        f"✅ Запись подтверждена!\n\n📅 {date_fmt}\n⏰ {tm}\n💅 {service}\n📍 Аягоз, ул. Актамберды, 23"
    )
    
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"🆕 Новая запись!\n👤 {name}\n📱 {phone}\n📅 {date_fmt}\n⏰ {tm}\n💅 {service}"
    )
    await state.clear()
@dp.callback_query(F.data == "contact")
async def contact(cb: CallbackQuery):
    text = (
        "📍 *Аягоз, ул. Актамберды, 23*\n"
        "🕒 *Пн–Пт:* 10:00–20:00\n"
        "🕒 *Сб:* 10:00–18:00\n"
        "📱 +7 777 123 45 67\n"
        "🌐 [asem-podo.pages.dev](https://asem-podo.pages.dev)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 WhatsApp", url="https://wa.me/77771234567")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")]
    ])
    await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

async def main():
    logging.basicConfig(level=logging.INFO)
    print("✅ Telegram bot started. Polling...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
