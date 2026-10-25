import asyncio
import logging
import os
import tempfile
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.exceptions import TelegramAPIError

import config
import database
import llm_client
import card_generator
import monetization
from prompts import MODES

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("mega_bot")

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

class Mode(StatesGroup):
    waiting_photo = State()
    admin_give_bonus = State()

# Меню категорий
def _main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Анализ фото", callback_data="cat_photo")],
        [InlineKeyboardButton(text="❤️ Отношения", callback_data="cat_love")],
        [InlineKeyboardButton(text="🔮 Мистика", callback_data="cat_mystic")],
        [InlineKeyboardButton(text="😂 Мемы", callback_data="cat_meme")],
        [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="invite")]
    ])

def _cat_photo_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Токсик-Чек", callback_data="m_toxic")],
        [InlineKeyboardButton(text="😎 Кент-Чек", callback_data="m_kent")],
        [InlineKeyboardButton(text="🤬 Уровень кринжа", callback_data="m_cringe")],
        [InlineKeyboardButton(text="🕵️ Психопрофиль", callback_data="m_psycho")],
        [InlineKeyboardButton(text="🔮 Узнать ауру", callback_data="m_aura")],
        [InlineKeyboardButton(text="📱 Возраст по лицу", callback_data="m_age")],
        [InlineKeyboardButton(text="💀 Уровень одиночества", callback_data="m_lonely")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

def _cat_love_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Анализатор отношений", callback_data="m_relationship")],
        [InlineKeyboardButton(text="⚖️ Кто главный в переписке", callback_data="m_leader")],
        [InlineKeyboardButton(text="🎯 Тип твоего краша", callback_data="m_crush")],
        [InlineKeyboardButton(text="🌶️ Оценка флекса", callback_data="m_flex")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

def _cat_mystic_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Гадалка", callback_data="m_fortune")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

def _cat_meme_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="😂 Мем-Генератор", callback_data="m_meme")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])

# Админ-меню
def _admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Выдать попытки по ID", callback_data="admin_give")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")]
    ])

# Проверка подписки с уведомлением
async def _require_subscription(message_or_cb):
    is_sub = await monetization.is_subscribed(bot, message_or_cb.from_user.id)
    if not is_sub:
        kb = monetization.subscribe_kb()
        text = "👋 <b>Ты отписался от канала!</b>\n\nПодпишись снова, чтобы пользоваться ботом."
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text, reply_markup=kb)
        else:
            await message_or_cb.message.edit_text(text, reply_markup=kb)
            await message_or_cb.answer()
        return False
    return True


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # Рефералка
    args = message.text.split(maxsplit=1)
    ref_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try: ref_by = int(args[1][4:])
        except: pass
    await database.register_user(message.from_user.id, message.from_user.username, ref_by)
    if ref_by:
        await database.add_referral_bonus(ref_by)

    if not await _require_subscription(message): return

    ref_count = await database.get_referral_count(message.from_user.id)
    ref_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{message.from_user.id}"
    
    text = (f"👋 <b>Добро пожаловать в Mega-Bot!</b>\n\n"
            f"Выбери категорию:\n\n"
            f"🎁 Приглашено: <b>{ref_count}</b> друзей (+1 проверка)\n"
            f"🔗 Твоя ссылка:\n<code>{ref_link}</code>")
    await message.answer(text, reply_markup=_main_menu_kb())

@dp.callback_query(F.data == "back_main")
async def cb_back_main(cb: CallbackQuery):
    if not await _require_subscription(cb): return
    await cb.message.edit_text("Выбери категорию:", reply_markup=_main_menu_kb())
    await cb.answer()

@dp.callback_query(F.data.startswith("cat_"))
async def cb_category(cb: CallbackQuery):
    if not await _require_subscription(cb): return
    cat = cb.data.split("_")[1]
    if cat == "photo":
        await cb.message.edit_text("📸 <b>Анализ фото:</b>", reply_markup=_cat_photo_kb())
    elif cat == "love":
        await cb.message.edit_text("❤️ <b>Отношения:</b>", reply_markup=_cat_love_kb())
    elif cat == "mystic":
        await cb.message.edit_text("🔮 <b>Мистика:</b>", reply_markup=_cat_mystic_kb())
    elif cat == "meme":
        await cb.message.edit_text("😂 <b>Мемы:</b>", reply_markup=_cat_meme_kb())
    await cb.answer()

@dp.callback_query(F.data == "invite")
async def cb_invite(cb: CallbackQuery):
    if not await _require_subscription(cb): return
    ref_count = await database.get_referral_count(cb.from_user.id)
    ref_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{cb.from_user.id}"
    await cb.message.edit_text(
        f"🎁 Приглашено: <b>{ref_count}</b> друзей\n\n🔗 Твоя ссылка:\n<code>{ref_link}</code>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]])
    )
    await cb.answer()

@dp.callback_query(F.data.startswith("m_"))
async def cb_choose_mode(cb: CallbackQuery, state: FSMContext):
    if not await _require_subscription(cb): return
    mode = cb.data.split("_", 1)[1]
    if mode not in MODES:
        return await cb.answer("Неизвестный режим")
    
    await state.set_state(Mode.waiting_photo)
    await state.update_data(mode=mode)
    
    await cb.message.edit_text(f"Режим: <b>{mode.upper()}</b>\n\nСкинь фото 👇")
    await cb.answer()

# ─────────── АДМИНКА ───────────
@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    await message.answer("👑 <b>Админ-панель</b>", reply_markup=_admin_menu_kb())

@dp.callback_query(F.data == "admin_give")
async def cb_admin_give(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id != config.ADMIN_ID: return
    await state.set_state(Mode.admin_give_bonus)
    await cb.message.edit_text("Введи ID пользователя и количество попыток через пробел:\nПример: <code>123456789 10</code>")

@dp.message(Mode.admin_give_bonus, F.text)
async def process_admin_give(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID: return
    try:
        uid_str, amount_str = message.text.split()
        uid, amount = int(uid_str), int(amount_str)
        await database.add_bonus(uid, amount)
        await message.answer(f"✅ Пользователю <code>{uid}</code> начислено <b>+{amount}</b> попыток.")
        try:
            await bot.send_message(uid, f"🎉 Тебе начислено <b>+{amount}</b> попыток! Спасибо за участие.")
        except: pass
    except:
        await message.answer("❌ Ошибка. Введи в формате: <code>ID количество</code>")
    await state.clear()

@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(cb: CallbackQuery):
    if cb.from_user.id != config.ADMIN_ID: return
    s = await database.get_full_stats()
    text = (f"📊 Юзеров: {s['total_users']} | Запросов: {s['requests_total']}\n"
            f"Сегодня: {s['requests_today']} | Новых: {s['new_today']}")
    await cb.message.answer(text)
    await cb.answer()

# ─────────── ОБРАБОТКА ФОТО ───────────
@dp.message(Mode.waiting_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext):
    if not await _require_subscription(message): return

    user_id = message.from_user.id
    if not await database.can_make_request(user_id, config.DAILY_LIMIT):
        await message.answer("🚫 Лимит исчерпан. Пригласи друга или купи подписку!")
        return

    data = await state.get_data()
    mode = data.get("mode")
    if not mode: return

    tmp = None
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        fd, tmp = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        await bot.download_file(file.file_path, destination=tmp)
        with open(tmp, "rb") as f:
            img_bytes = f.read()
    except Exception as e:
        return await message.answer("Ошибка скачивания.")

    wait = await message.answer("🔍 Анализирую...")

    result = await database.get_cached(img_bytes, mode)
    from_cache = result is not None

    if not from_cache:
        try:
            result = await llm_client.analyze(img_bytes, mode=mode)
            await database.save_cache(img_bytes, mode, result)
        except Exception as e:
            log.error(e)
            return await wait.edit_text("😴 Бот устал...")

    try:
        if mode == "meme":
            card_bytes = card_generator.create_meme_with_photo(img_bytes, result)
        else:
            card_bytes = card_generator.create_card(result, mode=mode)
    except Exception:
        return await wait.edit_text("Ошибка карточки.")

    # Формирование текста
    captions = {
        "toxic": f"🧪 Токсик: {result.get('toxic')} | Флаги: {result.get('flags')}%",
        "kent": f"😎 Кент: {result.get('verdict')} | Уровень: {result.get('kent_level')}%",
        "fortune": f"🔮 Удача: {result.get('luck')}% | {result.get('prediction')}",
        "cringe": f"🤬 Кринж: {result.get('cringe')}% | {result.get('verdict')}",
        "flex": f"🌶️ Флекс: {result.get('flex')}% | {result.get('verdict')}",
        "psycho": f"🕵️ Тип: {result.get('type')} | {result.get('character')}",
        "aura": f"🔮 Аура: {result.get('color')} | {result.get('meaning')}",
        "age": f"📱 Возраст: {result.get('age')} | Ментальный: {result.get('mental')}",
        "relationship": f"❤️ Совместимость: {result.get('compat')}% | Главный: {result.get('leader')}",
        "crush": f"🎯 Тип: {result.get('type')} | Ищет: {result.get('seeks')}",
        "leader": f"⚖️ Главный: {result.get('leader')} | Баланс: {result.get('balance')}%",
        "lonely": f"💀 Одиночество: {result.get('lonely')}% | {result.get('status')}",
        "meme": f"😂 Мем готов!"
    }
    caption = captions.get(mode, "Готово!")

    try:
        pf = BufferedInputFile(card_bytes, filename="card.png")
        await message.answer_photo(photo=pf, caption=caption)
        await wait.delete()
        if not from_cache:
            score = result.get("flags", result.get("compat", 0))
            await database.log_request(user_id, score, mode)
    except Exception as e:
        await wait.edit_text("Ошибка отправки.")

    await state.clear()
    if tmp and os.path.exists(tmp): os.remove(tmp)

@dp.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    await message.answer("Выбери действие через меню /start")

async def main():
    await database.init_db()
    log.info("Bot started.")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
