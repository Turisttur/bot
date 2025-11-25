
# 📁 bot.py — исправленная версия (для aiogram >=3.10)
import asyncio
import logging
from datetime import datetime, timedelta, time
import pytz
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# 🔑 === ВСТАВЬТЕ СВОИ ДАННЫЕ ===
BOT_TOKEN = "8454009227:AAEV5eAl8L3pxUC_JQa6FI8dsJAZ2yHtdQc"  # ← замените
ADMIN_CHAT_ID = 6734540756  # ← замените
# ==============================

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

TRANSLATIONS = {
    "ru": {
        "start": "🌸 Добро пожаловать в ASEM PODO @ BEAUTY!\n\nВыберите действие:",
        "book": "📅 Записаться",
        "contact": "📞 Контакты",
        "lang": "ҚҚ",
        "back": "⬅️ Назад",
        "service_select": "Выберите услугу:",
        "name_prompt": "Введите ваше имя:",
        "phone_prompt": "Введите ваш телефон:",
        "choose_day": "Выберите день:",
        "choose_time": "Выберите время:",
        "confirmed": "✅ Запись подтверждена!\n\n📅 {date}\n⏰ {time}\n💅 {service}\n📍 Аягоз, ул. Актамберды, 23\n\nСпасибо, что выбираете нас! 🫶",
        "admin_new": "🆕 Новая запись!\n👤 {name}\n📱 {phone}\n📅 {date}\n⏰ {time}\n💅 {service}"
    },
    "kk": {
        "start": "🌸 ASEM PODO @ BEAUTY-ға қош келдіңіз!\n\nӘрекетті таңдаңыз:",
        "book": "📅 Кезекке жазылу",
        "contact": "📞 Байланыс",
        "lang": "РУ",
        "back": "⬅️ Артқа",
        "service_select": "Қызметті таңдаңыз:",
        "name_prompt": "Атыңызды енгізіңіз:",
        "phone_prompt": "Телефон номеріңізді енгізіңіз:",
        "choose_day": "Күнді таңдаңыз:",
        "choose_time": "Уақытты таңдаңыз:",
        "confirmed": "✅ Тіркелу расталды!\n\n📅 {date}\n⏰ {time}\n💅 {service}\n📍 Аяғоз, Актамберды к-сі, 23\n\nБізді таңдағаныңызға рахмет! 🫶",
        "admin_new": "🆕 Жаңа тіркелу!\n👤 {name}\n📱 {phone}\n📅 {date}\n⏰ {time}\n💅 {service}"
    }
}

SERVICES = [
    ("Медицинская подология", "Медициналық подология"),
    ("Эстетический маникюр", "Эстетикалық маникюр"),
    ("Педикюр премиум", "Педикюр премиум"),
    ("Визаж", "Макияж")
]

# === FSM States ===
class Booking(StatesGroup):
    choosing_service = State()
    entering_name = State()
    entering_phone = State()
    choosing_day = State()
    choosing_time = State()

# === Вспомогательные функции ===
def get_lang(msg) -> str:
    return msg.from_user.language_code[:2] if msg.from_user.language_code else "ru"

def _(key: str, lang: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["ru"]).get(key, key)

def get_main_menu(lang: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_("book", lang), callback_data="book")],
            [InlineKeyboardButton(text=_("contact", lang), callback_data="contact")],
            [InlineKeyboardButton(text=_("lang", lang), callback_data=f"switch_lang_{lang}")]
        ]
    )

def get_days_kb():
    now = datetime.now(TIMEZONE)
    buttons = []
    for i in range(14):
        day = now + timedelta(days=i)
        wd = day.strftime("%a").lower()[:3]
        if WORKING_HOURS[wd]:
            text = day.strftime("%d %b")
            if i == 0: text = "Сегодня"
            elif i == 1: text = "Завтра"
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"day_{day.strftime('%Y-%m-%d')}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_times_kb(date_str: str):
    day = datetime.strptime(date_str, "%Y-%m-%d")
    wd = day.strftime("%a").lower()[:3]
    hours = WORKING_HOURS[wd]
    if not hours:
        return None
    start, end = hours
    slots = []
    current = datetime.combine(day.date(), start)
    while current < datetime.combine(day.date(), end):
        if (current - datetime.now(TIMEZONE)).total_seconds() > 1800:
            slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=60)
    if not slots:
        return None
    buttons = [[InlineKeyboardButton(t, callback_data=f"time_{t}")] for t in slots]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="choose_day")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === Инициализация ===
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# === ХЕНДЛЕРЫ ===

@dp.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    lang = get_lang(msg)
    await state.set_state(None)  # сброс состояния
    await msg.answer(_("start", lang), reply_markup=get_main_menu(lang))

@dp.callback_query(F.data == "main")
async def back_to_main(cb: CallbackQuery, state: FSMContext):
    lang = get_lang(cb.message)
    await state.set_state(None)
    await cb.message.edit_text(_("start", lang), reply_markup=get_main_menu(lang))

@dp.callback_query(F.data == "book")
async def book_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.choosing_service)
    buttons = [
        [InlineKeyboardButton(ru, callback_data=f"srv_{ru}")] for ru, _ in SERVICES
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="main")])
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
    if not kb:
        await cb.answer("Нет свободного времени", show_alert=True)
        return
    await cb.message.edit_text("Выберите время:", reply_markup=kb)

@dp.callback_query(F.data.startswith("time_"))
async def time(cb: CallbackQuery, state: FSMContext):
    tm = cb.data[5:]
    data = await state.get_data()
    date_obj = datetime.strptime(data["date"], "%Y-%m-%d")
    date_fmt = date_obj.strftime("%d.%m")
    
    # Клиенту
    await cb.message.edit_text(
        _("confirmed", get_lang(cb.message)).format(
            date=date_fmt, time=tm, service=data["service"]
        )
    )
    
    # Админу
    await bot.send_message(
        ADMIN_CHAT_ID,
        _("admin_new", "ru").format(
            name=data["name"],
            phone=data["phone"],
            date=date_fmt,
            time=tm,
            service=data["service"]
        )
    )
    await state.clear()

@dp.callback_query(F.data == "contact")
async def contact(cb: CallbackQuery):
    text = (
        "📍 *Аягоз, ул. Актамберды, 23*\n"
        "🕒 *Пн–Пт:* 10:00–20:00\n"
        "📱 +7 777 123 45 67\n"
        "🌐 [asem-podo.pages.dev](https://asem-podo.pages.dev)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("💬 WhatsApp", url="https://wa.me/77771234567")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main")]
    ])
    await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)

@dp.callback_query(F.data.startswith("switch_lang_"))
async def switch_lang(cb: CallbackQuery, state: FSMContext):
    lang = "kk" if cb.data.endswith("ru") else "ru"
    await cb.message.edit_text(_("start", lang), reply_markup=get_main_menu(lang))

# === Главный запуск ===
async def main():
    logging.basicConfig(level=logging.INFO)
    print("✅ Бот запущен. Ожидаю сообщения...")
    await dp.start_polling(bot, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    asyncio.run(main())
