# 📁 bot.py — Telegram-бот для ASEM PODO @ BEAUTY
# ✅ Работает на PythonAnywhere Free Account
# ✅ Поддержка: календарь, выбор услуги, подтверждение, уведомление админу

import asyncio
from datetime import datetime, timedelta, time
import pytz
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# 🔑 === ВСТАВЬТЕ СВОИ ДАННЫЕ ЗДЕСЬ ===
BOT_TOKEN = "8454009227:AAEV5eAl8L3pxUC_JQa6FI8dsJAZ2yHtdQc"   # ← ЗАМЕНИТЕ НА СВОЙ ТОКЕН от @BotFather
ADMIN_CHAT_ID = 6734540756                                        # ← ЗАМЕНИТЕ НА ВАШ Telegram ID (узнать у @userinfobot)
# =====================================

TIMEZONE = pytz.timezone("Asia/Almaty")

# Рабочие часы: пн–пт 10:00–20:00, сб 10:00–18:00, вс — выходной
WORKING_HOURS = {
    "mon": (time(10, 0), time(20, 0)),
    "tue": (time(10, 0), time(20, 0)),
    "wed": (time(10, 0), time(20, 0)),
    "thu": (time(10, 0), time(20, 0)),
    "fri": (time(10, 0), time(20, 0)),
    "sat": (time(10, 0), time(18, 0)),
    "sun": None
}

# Переводы (РУ / ҚҚ)
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

# Инициализация
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

class Booking(StatesGroup):
    choosing_service = State()
    entering_name = State()
    entering_phone = State()
    choosing_day = State()
    choosing_time = State()

def get_user_lang(msg) -> str:
    return msg.from_user.language_code[:2] if msg.from_user.language_code else "ru"

def _(key: str, lang: str) -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["ru"]).get(key, key)

def get_main_menu(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=_("book", lang), callback_data="book")],
        [InlineKeyboardButton(text=_("contact", lang), callback_data="contact")],
        [InlineKeyboardButton(text=_("lang", lang), callback_data=f"switch_lang_{lang}")]
    ])

def get_days_keyboard(lang: str):
    now = datetime.now(TIMEZONE)
    buttons = []
    for i in range(14):  # 2 недели вперёд
        day = now + timedelta(days=i)
        wd = day.strftime("%a").lower()[:3]
        if WORKING_HOURS[wd]:
            text = day.strftime("%d %b")
            if i == 0:
                text = "Сегодня"
            elif i == 1:
                text = "Завтра"
            buttons.append([InlineKeyboardButton(text=text, callback_data=f"day_{day.strftime('%Y-%m-%d')}")])
    buttons.append([InlineKeyboardButton(text=_("back", lang), callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_times_keyboard(date_str: str):
    day = datetime.strptime(date_str, "%Y-%m-%d")
    wd = day.strftime("%a").lower()[:3]
    hours = WORKING_HOURS[wd]
    if not hours:
        return None
    start, end = hours
    slots = []
    current = datetime.combine(day.date(), start)
    end_dt = datetime.combine(day.date(), end)
    while current < end_dt:
        # Пропускаем время в прошлом и ближайшие 30 мин
        if (current - datetime.now(TIMEZONE)).total_seconds() > 1800:
            slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=60)  # интервал 60 мин
    if not slots:
        return None
    buttons = [[InlineKeyboardButton(t, callback_data=f"time_{t}")] for t in slots]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="choose_day")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# === ХЕНДЛЕРЫ ===

@router.message(Command("start"))
async def cmd_start(msg: Message, state: FSMContext):
    lang = get_user_lang(msg)
    await state.update_data(lang=lang)
    await msg.answer(_("start", lang), reply_markup=get_main_menu(lang))

@router.callback_query(F.data == "main")
async def back_to_main(cb: CallbackQuery, state: FSMContext):
    lang = (await state.get_data()).get("lang", "ru")
    await cb.message.edit_text(_("start", lang), reply_markup=get_main_menu(lang))

@router.callback_query(F.data == "book")
async def book_start(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Booking.choosing_service)
    buttons = []
    for ru, kk in SERVICES:
        buttons.append([InlineKeyboardButton(text=ru, callback_data=f"srv_{ru}")])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="main")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await cb.message.edit_text("Выберите услугу:", reply_markup=kb)

@router.callback_query(F.data.startswith("srv_"))
async def service_selected(cb: CallbackQuery, state: FSMContext):
    service = cb.data[4:]
    await state.update_data(service=service)
    await state.set_state(Booking.entering_name)
    await cb.message.edit_text("Введите ваше имя:")

@router.message(Booking.entering_name)
async def name_entered(msg: Message, state: FSMContext):
    await state.update_data(name=msg.text)
    await state.set_state(Booking.entering_phone)
    await msg.answer("Введите ваш телефон:")

@router.message(Booking.entering_phone)
async def phone_entered(msg: Message, state: FSMContext):
    await state.update_data(phone=msg.text)
    await state.set_state(Booking.choosing_day)
    await msg.answer("Выберите день:", reply_markup=get_days_keyboard("ru"))

@router.callback_query(F.data.startswith("day_"))
async def day_selected(cb: CallbackQuery, state: FSMContext):
    date = cb.data[4:]
    await state.update_data(date=date)
    await state.set_state(Booking.choosing_time)
    kb = get_times_keyboard(date)
    if not kb:
        await cb.answer("В этот день нет свободного времени. Выберите другой.", show_alert=True)
        return
    await cb.message.edit_text("Выберите время:", reply_markup=kb)

@router.callback_query(F.data.startswith("time_"))
async def time_selected(cb: CallbackQuery, state: FSMContext):
    time_str = cb.data[5:]
    data = await state.get_data()
    data["time"] = time_str
    # Форматируем дату
    date_obj = datetime.strptime(data["date"], "%Y-%m-%d")
    date_fmt = date_obj.strftime("%d.%m")
    # Ответ клиенту
    await cb.message.edit_text(
        _("confirmed", data.get("lang", "ru")).format(
            date=date_fmt,
            time=time_str,
            service=data["service"]
        )
    )
    # Уведомление админу
    await bot.send_message(
        ADMIN_CHAT_ID,
        _("admin_new", "ru").format(
            name=data["name"],
            phone=data["phone"],
            date=date_fmt,
            time=time_str,
            service=data["service"]
        )
    )
    await state.clear()

@router.callback_query(F.data == "contact")
async def show_contact(cb: CallbackQuery):
    text = (
        "📍 *Аягоз, ул. Актамберды, 23*\n"
        "🕒 *Пн–Пт:* 10:00–20:00\n"
        "🕒 *Сб:* 10:00–18:00\n"
        "📱 +7 777 123 45 67\n"
        "🌐 [asem-podo.pages.dev](https://asem-podo.pages.dev)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("💬 WhatsApp", url="https://wa.me/77771234567")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main")]
    ])
    await cb.message.edit_text(text, parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=True)

@router.callback_query(F.data.startswith("switch_lang_"))
async def switch_language(cb: CallbackQuery, state: FSMContext):
    current_lang = cb.data.split("_")[-1]
    new_lang = "kk" if current_lang == "ru" else "ru"
    await state.update_data(lang=new_lang)
    await cb.message.edit_text(_("start", new_lang), reply_markup=get_main_menu(new_lang))

# === ЗАПУСК ===
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    print("✅ Бот запущен. Ожидаю сообщения...")
    print(f"🤖 @asem_podo_bot готов к работе!")
    asyncio.run(dp.start_polling(bot))