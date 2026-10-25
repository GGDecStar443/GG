# Мега-бот: 13 режимов + UX + админка + защита (ФИНАЛ)
import asyncio
import logging
import os
import re
import random
import tempfile
import time
import shutil
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile, FSInputFile,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.exceptions import TelegramAPIError

import config
import database
import llm_client
import card_generator
import monetization
from prompts import MODES

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("mega_bot")

bot = Bot(token=config.BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


class Mode(StatesGroup):
    waiting_photo = State()
    admin_give_bonus = State()


MODE_NAMES = {
    "toxic": "🧪 Токсик-Чек", "kent": "😎 Кент-Чек", "fortune": "🔮 Гадалка",
    "meme": "😂 Мем-Генератор", "relationship": "❤️ Анализатор отношений",
    "cringe": "🤬 Уровень кринжа", "flex": "🌶️ Оценка флекса",
    "psycho": "🕵️ Психопрофиль", "aura": "🔮 Узнать ауру",
    "leader": "⚖️ Кто главный", "age": "📱 Возраст по лицу",
    "crush": "🎯 Тип краша", "lonely": "💀 Уровень одиночества",
}

MODE_HINTS = {
    "toxic": "Скинь <b>скрин переписки</b> с человеком 👇",
    "kent": "Скинь <b>фото кента</b> (или своё) 👇",
    "fortune": "Скинь <b>любое фото</b> — погадаю 👇",
    "meme": "Скинь <b>любое фото</b> — сделаю мем 👇",
    "relationship": "Скинь <b>фото с партнёром</b> 👇",
    "cringe": "Скинь <b>своё селфи</b> (или скрин профиля) 👇",
    "flex": "Скинь <b>скрин поста</b> из соцсетей 👇",
    "psycho": "Скинь <b>своё селфи</b> 👇",
    "aura": "Скинь <b>любое фото</b> — определю ауру 👇",
    "leader": "Скинь <b>скрин переписки</b> 👇",
    "age": "Скинь <b>своё селфи</b> (лицо крупно) 👇",
    "crush": "Скинь <b>фото краша</b> 👇",
    "lonely": "Скинь <b>своё селфи</b> или фото комнаты 👇",
}

# Какое поле использовать как "score" для логов
MODE_SCORE_FIELD = {
    "toxic": "flags",
    "kent": "kent_level",
    "fortune": "luck",
    "cringe": "cringe",
    "flex": "flex",
    "relationship": "compat",
    "leader": "balance",
    "age": "age",
    "lonely": "lonely",
    "psycho": None,
    "aura": None,
    "crush": None,
    "meme": None,
}

WRONG_TYPE_MSG = (
    "⚠️ <b>Я работаю только с картинками!</b>\n\n"
    "Скинь <b>фото</b>, а не видео / документ / музыку."
)

_user_last_request = {}

_BAD_WORDS = re.compile(
    r"(?:хуй|хуя|хуе|хуё|пизд|бля|блят|ебал|ебать|ебёт|ебу|ебись|"
    r"сук[аи]|муда|муди|долбо|дроч|гандон|залуп|манда|"
    r"fuck|shit|bitch|asshole|cunt|dick|pussy)",
    re.IGNORECASE,
)


def _is_spam_text(text: str) -> bool:
    if not text or len(text) < 3:
        return False
    if _BAD_WORDS.search(text):
        return True
    words = text.split()
    if len(words) <= 2 and len(text) > 30 and text.isupper():
        return True
    return False


# ═══════════════════════════════════════════
# КЛАВИАТУРЫ
# ═══════════════════════════════════════════
def _main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📸 Анализ фото", callback_data="cat_photo")],
        [InlineKeyboardButton(text="❤️ Отношения", callback_data="cat_love")],
        [InlineKeyboardButton(text="🔮 Мистика", callback_data="cat_mystic")],
        [InlineKeyboardButton(text="😂 Мемы", callback_data="cat_meme")],
        [InlineKeyboardButton(text="🎲 Случайный анализ", callback_data="random_mode")],
        [InlineKeyboardButton(text="🏆 Топ недели", callback_data="top_week")],
        [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="invite")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
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
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])

def _cat_love_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❤️ Анализатор отношений", callback_data="m_relationship")],
        [InlineKeyboardButton(text="⚖️ Кто главный", callback_data="m_leader")],
        [InlineKeyboardButton(text="🎯 Тип краша", callback_data="m_crush")],
        [InlineKeyboardButton(text="🌶️ Оценка флекса", callback_data="m_flex")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])

def _cat_mystic_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔮 Гадалка", callback_data="m_fortune")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])

def _cat_meme_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="😂 Мем-Генератор", callback_data="m_meme")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")],
    ])

def _admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Выдать попытки", callback_data="admin_give")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🚫 Чёрный список", callback_data="admin_blacklist")],
        [InlineKeyboardButton(text="💾 Сделать бэкап", callback_data="admin_backup")],
    ])

def _share_kb(mode: str):
    share_text = f"Смотри, что про меня выдал AI! 👉 @{config.BOT_USERNAME}"
    share_url = f"https://t.me/share/url?url={config.BOT_LINK}&text={share_text}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Поделиться с другом", url=share_url)],
        [
            InlineKeyboardButton(text="🔄 Поменять фото", callback_data=f"retry_{mode}"),
            InlineKeyboardButton(text="🏠 В меню", callback_data="back_main"),
        ],
        [InlineKeyboardButton(text="🎲 Другой режим", callback_data="random_mode")],
    ])


# ═══════════════════════════════════════════
# ХЕЛПЕРЫ
# ═══════════════════════════════════════════
async def _get_limit_text(user_id: int) -> str:
    try:
        used = await database.get_today_requests(user_id)
        bonus = await database.get_bonus_today(user_id)
        limit = config.DAILY_LIMIT + bonus
        left = max(0, limit - used)
        return f"⚡ <b>Осталось на сегодня: {left} из {limit}</b>"
    except Exception:
        return ""


async def _safe_delete(msg: Message, delay: int = 10):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


async def _require_subscription(message_or_cb):
    is_sub = await monetization.is_subscribed(bot, message_or_cb.from_user.id)
    if not is_sub:
        kb = monetization.subscribe_kb()
        text = "👋 <b>Ты отписался от канала!</b>\n\nПодпишись снова, чтобы пользоваться ботом."
        if isinstance(message_or_cb, Message):
            await message_or_cb.answer(text, reply_markup=kb)
        else:
            try:
                await message_or_cb.message.edit_text(text, reply_markup=kb)
            except TelegramAPIError:
                await message_or_cb.message.answer(text, reply_markup=kb)
            await message_or_cb.answer()
        return False
    return True


async def _require_not_banned(user_id: int) -> bool:
    status = await database.get_ban_status(user_id)
    return not status["is_banned"]


# ═══════════════════════════════════════════
# ГЛОБАЛЬНЫЙ ПЕРЕХВАТЧИК
# ═══════════════════════════════════════════
@dp.errors()
async def global_error_handler(event):
    log.exception("Unhandled error: %s", event.exception)
    update = event.update
    try:
        if update.message:
            await update.message.answer(
                "😅 Что-то пошло не так. Попробуй ещё раз или нажми /start",
                reply_markup=_main_menu_kb(),
            )
        elif update.callback_query:
            await update.callback_query.answer("Ошибка. Попробуй ещё раз.", show_alert=True)
    except Exception as e:
        log.error("Failed to send error message: %s", e)
    return True


# ═══════════════════════════════════════════
# СТАРТ
# ═══════════════════════════════════════════
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    if not await _require_not_banned(message.from_user.id):
        status = await database.get_ban_status(message.from_user.id)
        if status.get("is_permanent"):
            await message.answer("🚫 Ты забанен навсегда за нарушения. Обратись к админу.")
        else:
            await message.answer(f"⏳ Ты забанен на {status.get('remaining_min', 30)} мин. за нарушения.")
        return

    args = message.text.split(maxsplit=1)
    ref_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_by = int(args[1][4:])
        except ValueError:
            pass
    if ref_by == message.from_user.id:
        ref_by = None

    await database.register_user(message.from_user.id, message.from_user.username, ref_by)
    if ref_by:
        try:
            await database.add_referral_bonus(ref_by)
        except Exception as e:
            log.warning("Referral bonus failed: %s", e)

    if not await _require_subscription(message):
        return

    # Ежедневный бонус
    daily_given = await database.check_daily_bonus(message.from_user.id)
    daily_text = "🎁 <b>+1 бесплатная проверка</b> за вход сегодня!\n\n" if daily_given else ""

    ref_count = await database.get_referral_count(message.from_user.id)
    ref_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{message.from_user.id}"
    limit_text = await _get_limit_text(message.from_user.id)

    text = (
        "👋 <b>Добро пожаловать в Mega-Bot!</b>\n\n"
        f"{daily_text}"
        f"{limit_text}\n\n"
        "Выбери категорию:\n\n"
        f"🎁 Приглашено: <b>{ref_count}</b> друзей (+1 проверка за каждого)\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>"
    )
    await message.answer(text, reply_markup=_main_menu_kb())


# ═══════════════════════════════════════════
# HELP
# ═══════════════════════════════════════════
HELP_TEXT = (
    "📖 <b>КАК ЭТО РАБОТАЕТ:</b>\n\n"
    "1️⃣ Выбери режим из меню\n"
    "2️⃣ Скинь нужное фото:\n"
    "   • 🧪 Токсик-Чек → <b>скрин переписки</b>\n"
    "   • 😎 Кент-Чек → <b>фото друга</b>\n"
    "   • 📱 Возраст → <b>своё селфи</b>\n"
    "   • ❤️ Отношения → <b>фото с партнёром</b>\n"
    "3️⃣ Получи карточку за 5-10 сек\n"
    "4️⃣ Поделись с другом\n\n"
    f"⚡ <b>Лимит:</b> {config.DAILY_LIMIT} проверок/день\n"
    "🎁 <b>За друга:</b> +1 проверка\n"
    "🏆 <b>Топ недели:</b> соревнуйся с другими\n\n"
    "❓ <b>Есть вопрос?</b> Напиши админу: /myref — узнать свою ссылку"
)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В меню", callback_data="back_main")]
    ]))


@dp.callback_query(F.data == "help")
async def cb_help(cb: CallbackQuery):
    try:
        await cb.message.edit_text(HELP_TEXT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_main")]
        ]))
    except TelegramAPIError:
        await cb.message.answer(HELP_TEXT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 В меню", callback_data="back_main")]
        ]))
    await cb.answer()


# ═══════════════════════════════════════════
# КАТЕГОРИИ
# ═══════════════════════════════════════════
@dp.callback_query(F.data == "back_main")
async def cb_back_main(cb: CallbackQuery):
    if not await _require_not_banned(cb.from_user.id):
        await cb.answer("Ты забанен", show_alert=True)
        return
    if not await _require_subscription(cb):
        return
    limit_text = await _get_limit_text(cb.from_user.id)
    text = f"Выбери категорию:\n\n{limit_text}" if limit_text else "Выбери категорию:"
    try:
        await cb.message.edit_text(text, reply_markup=_main_menu_kb())
    except TelegramAPIError:
        await cb.message.answer(text, reply_markup=_main_menu_kb())
    await cb.answer()


@dp.callback_query(F.data.startswith("cat_"))
async def cb_category(cb: CallbackQuery):
    if not await _require_not_banned(cb.from_user.id):
        await cb.answer("Ты забанен", show_alert=True)
        return
    if not await _require_subscription(cb):
        return
    cat = cb.data.split("_", 1)[1]
    try:
        if cat == "photo":
            await cb.message.edit_text("📸 <b>Анализ фото:</b>", reply_markup=_cat_photo_kb())
        elif cat == "love":
            await cb.message.edit_text("❤️ <b>Отношения:</b>", reply_markup=_cat_love_kb())
        elif cat == "mystic":
            await cb.message.edit_text("🔮 <b>Мистика:</b>", reply_markup=_cat_mystic_kb())
        elif cat == "meme":
            await cb.message.edit_text("😂 <b>Мемы:</b>", reply_markup=_cat_meme_kb())
    except TelegramAPIError:
        if cat == "photo":
            await cb.message.answer("📸 <b>Анализ фото:</b>", reply_markup=_cat_photo_kb())
        elif cat == "love":
            await cb.message.answer("❤️ <b>Отношения:</b>", reply_markup=_cat_love_kb())
        elif cat == "mystic":
            await cb.message.answer("🔮 <b>Мистика:</b>", reply_markup=_cat_mystic_kb())
        elif cat == "meme":
            await cb.message.answer("😂 <b>Мемы:</b>", reply_markup=_cat_meme_kb())
    await cb.answer()


@dp.callback_query(F.data == "invite")
async def cb_invite(cb: CallbackQuery):
    if not await _require_not_banned(cb.from_user.id):
        await cb.answer("Ты забанен", show_alert=True)
        return
    if not await _require_subscription(cb):
        return
    ref_count = await database.get_referral_count(cb.from_user.id)
    ref_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{cb.from_user.id}"
    text = (
        f"🎁 Приглашено: <b>{ref_count}</b> друзей\n\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>\n\n"
        f"За каждого друга: +1 проверка (макс +{config.REFERRAL_DAILY_LIMIT}/день)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except TelegramAPIError:
        await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data == "random_mode")
async def cb_random(cb: CallbackQuery, state: FSMContext):
    if not await _require_not_banned(cb.from_user.id):
        await cb.answer("Ты забанен", show_alert=True)
        return
    if not await _require_subscription(cb):
        return
    mode = random.choice(list(MODES.keys()))
    await state.set_state(Mode.waiting_photo)
    await state.update_data(mode=mode)
    name = MODE_NAMES.get(mode, mode.upper())
    hint = MODE_HINTS.get(mode, "Скинь фото 👇")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])
    text = f"🎲 Выпал режим: <b>{name}</b>\n\n{hint}"
    try:
        await cb.message.answer(text, reply_markup=kb)
    except Exception:
        pass
    await cb.answer("Рандом выбрал режим!", show_alert=False)


@dp.callback_query(F.data.startswith("retry_"))
async def cb_retry(cb: CallbackQuery, state: FSMContext):
    if not await _require_not_banned(cb.from_user.id):
        await cb.answer("Ты забанен", show_alert=True)
        return
    if not await _require_subscription(cb):
        return
    mode = cb.data.split("_", 1)[1]
    if mode not in MODES:
        await cb.answer("Неизвестный режим", show_alert=True)
        return
    await state.set_state(Mode.waiting_photo)
    await state.update_data(mode=mode)
    name = MODE_NAMES.get(mode, mode.upper())
    hint = MODE_HINTS.get(mode, "Скинь фото 👇")
    text = f"🔄 <b>{name}</b> — скинь новое фото\n\n{hint}"
    try:
        await cb.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
        ]))
    except Exception:
        pass
    await cb.answer("Жду новое фото!")


@dp.callback_query(F.data == "top_week")
async def cb_top_week(cb: CallbackQuery):
    if not await _require_not_banned(cb.from_user.id):
        await cb.answer("Ты забанен", show_alert=True)
        return
    if not await _require_subscription(cb):
        return
    top = await database.get_weekly_top()
    if not top:
        text = "🏆 Топ недели пока пуст. Стань первым!"
    else:
        lines = []
        for i, (username, user_id, cnt) in enumerate(top, 1):
            name = f"@{username}" if username else f"User#{user_id}"
            lines.append(f"  {i}. <b>{name}</b> — {cnt} проверок")
        text = "🏆 <b>Топ-10 недели:</b>\n\n" + "\n".join(lines) + "\n\n<i>Проверок за последние 7 дней</i>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except TelegramAPIError:
        await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


@dp.callback_query(F.data.startswith("m_"))
async def cb_choose_mode(cb: CallbackQuery, state: FSMContext):
    if not await _require_not_banned(cb.from_user.id):
        await cb.answer("Ты забанен", show_alert=True)
        return
    if not await _require_subscription(cb):
        return
    mode = cb.data.split("_", 1)[1]
    if mode not in MODES:
        await cb.answer("Неизвестный режим", show_alert=True)
        return
    await state.set_state(Mode.waiting_photo)
    await state.update_data(mode=mode)
    name = MODE_NAMES.get(mode, mode.upper())
    hint = MODE_HINTS.get(mode, "Скинь фото 👇")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])
    text = f"Режим: <b>{name}</b>\n\n{hint}"
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except TelegramAPIError:
        await cb.message.answer(text, reply_markup=kb)
    await cb.answer()


# ═══════════════════════════════════════════
# КОМАНДЫ
# ═══════════════════════════════════════════
@dp.message(Command("myref"))
async def cmd_myref(m: Message):
    ref_count = await database.get_referral_count(m.from_user.id)
    ref_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{m.from_user.id}"
    await m.answer(
        f"🎁 Приглашено: <b>{ref_count}</b> друзей\n\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>"
    )


# ═══════════════════════════════════════════
# АДМИН-ПАНЕЛЬ
# ═══════════════════════════════════════════
@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    await message.answer("👑 <b>Админ-панель</b>", reply_markup=_admin_menu_kb())


@dp.callback_query(F.data == "admin_give")
async def cb_admin_give(cb: CallbackQuery, state: FSMContext):
    if cb.from_user.id != config.ADMIN_ID:
        await cb.answer("Только для админа", show_alert=True)
        return
    await state.set_state(Mode.admin_give_bonus)
    await cb.message.edit_text(
        "Введи <b>ID пользователя</b> и <b>количество попыток</b> через пробел:\n"
        "Пример: <code>123456789 10</code>"
    )
    await cb.answer()


@dp.message(Mode.admin_give_bonus, F.text)
async def process_admin_give(message: Message, state: FSMContext):
    if message.from_user.id != config.ADMIN_ID:
        return
    try:
        uid_str, amount_str = message.text.split()
        uid = int(uid_str)
        amount = int(amount_str)
        if amount <= 0:
            raise ValueError
        await database.add_bonus(uid, amount)
        await message.answer(f"✅ Пользователю <code>{uid}</code> начислено <b>+{amount}</b> попыток.")
        try:
            await bot.send_message(uid, f"🎉 Тебе начислено <b>+{amount}</b> попыток! Спасибо за участие.")
        except Exception:
            pass
    except Exception:
        await message.answer("❌ Ошибка. Формат: <code>ID количество</code>")
    await state.clear()


@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(cb: CallbackQuery):
    if cb.from_user.id != config.ADMIN_ID:
        await cb.answer("Только для админа", show_alert=True)
        return
    try:
        s = await database.get_full_stats()
        modes_text = "\n".join(
            f"  {MODE_NAMES.get(m, m)}: <b>{c}</b>"
            for m, c in sorted(s["by_mode"].items(), key=lambda x: -x[1])
        ) or "  —"
        top_users_text = "\n".join(
            f"  {i+1}. @{u[0] or u[1]} — {u[2]}"
            for i, u in enumerate(s["top_users"])
        ) or "  —"
        text = (
            "📊 <b>СТАТИСТИКА</b>\n\n"
            f"👥 Всего юзеров: <b>{s['total_users']}</b>\n"
            f"📅 Новых сегодня: <b>{s['new_today']}</b>\n"
            f"🔥 Активных сегодня: <b>{s['active_today']}</b>\n\n"
            f"📨 Запросов сегодня: <b>{s['requests_today']}</b>\n"
            f"📨 Запросов всего: <b>{s['requests_total']}</b>\n"
            f"💾 В кэше: <b>{s['cache_size']}</b>\n\n"
            f"<b>По режимам:</b>\n{modes_text}\n\n"
            f"<b>ТОП-5 активных:</b>\n{top_users_text}"
        )
        await cb.message.answer(text)
    except Exception as e:
        log.exception("Stats error: %s", e)
        await cb.message.answer("Ошибка при сборе статистики.")
    await cb.answer()


@dp.callback_query(F.data == "admin_blacklist")
async def cb_admin_blacklist(cb: CallbackQuery):
    if cb.from_user.id != config.ADMIN_ID:
        await cb.answer("Только для админа", show_alert=True)
        return
    try:
        banned = await database.get_banned_users()
        if not banned:
            await cb.message.edit_text("✅ Чёрный список пуст.", reply_markup=_admin_menu_kb())
            await cb.answer()
            return
        for (user_id, username, count, banned_until, is_perm, reason) in banned[:5]:
            name = f"@{username}" if username else f"ID: {user_id}"
            if is_perm:
                status_text = "🚫 <b>ПЕРМАНЕНТНЫЙ БАН</b>"
            else:
                try:
                    ban_dt = datetime.fromisoformat(banned_until) if banned_until else None
                    remaining = int((ban_dt - datetime.now()).total_seconds() / 60) if ban_dt else 0
                    status_text = f"⏳ Бан ещё {remaining} мин."
                except Exception:
                    status_text = "⏳ Временный бан"
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Помиловать", callback_data=f"pardon_{user_id}")]
            ])
            await cb.message.answer(
                f"{name}\n{status_text}\nНарушений: {count} | Причина: {reason}",
                reply_markup=kb
            )
        await cb.answer()
    except Exception as e:
        log.exception("Blacklist error: %s", e)
        await cb.message.answer("Ошибка при загрузке ЧС.")
        await cb.answer()


@dp.callback_query(F.data.startswith("pardon_"))
async def cb_pardon(cb: CallbackQuery):
    if cb.from_user.id != config.ADMIN_ID:
        await cb.answer("Только для админа", show_alert=True)
        return
    user_id = int(cb.data.split("_")[1])
    await database.pardon_user(user_id)
    await cb.message.edit_text(f"✅ Пользователь <code>{user_id}</code> помилован.")
    try:
        await bot.send_message(user_id, "🎉 Ты был разбанен! Можешь снова пользоваться ботом.")
    except Exception:
        pass
    await cb.answer()


@dp.callback_query(F.data == "admin_backup")
async def cb_admin_backup(cb: CallbackQuery):
    if cb.from_user.id != config.ADMIN_ID:
        await cb.answer("Только для админа", show_alert=True)
        return
    try:
        if not os.path.exists(config.DB_PATH):
            await cb.message.answer("❌ База не найдена.")
            await cb.answer()
            return
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
        backup_path = f"/tmp/backup_{date_str}.db"
        shutil.copy(config.DB_PATH, backup_path)
        size_kb = os.path.getsize(backup_path) // 1024
        await cb.message.answer_document(
            document=FSInputFile(backup_path),
            caption=f"💾 Бэкап от {date_str} ({size_kb} KB)",
        )
        os.remove(backup_path)
    except Exception as e:
        log.exception("Backup error: %s", e)
        await cb.message.answer(f"❌ Ошибка бэкапа: {e}")
    await cb.answer()


# ═══════════════════════════════════════════
# ЗАЩИТА: НЕ-ФОТО
# ═══════════════════════════════════════════
@dp.message(F.video | F.document | F.audio | F.voice | F.video_note
            | F.sticker | F.animation | F.contact | F.location | F.poll)
async def handle_unsupported_content(message: Message):
    if not await _require_not_banned(message.from_user.id):
        return
    msg = await message.answer(WRONG_TYPE_MSG, reply_markup=_main_menu_kb())
    asyncio.create_task(_safe_delete(msg, 10))


# ═══════════════════════════════════════════
# ОБРАБОТЧИК ФОТО
# ═══════════════════════════════════════════
@dp.message(Mode.waiting_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext):
    tmp = None
    user_id = message.from_user.id

    try:
        if not await _require_not_banned(user_id):
            status = await database.get_ban_status(user_id)
            if status.get("is_permanent"):
                await message.answer("🚫 Ты забанен навсегда.")
            else:
                await message.answer(f"⏳ Ты забанен на {status.get('remaining_min', 30)} мин.")
            return

        now = time.time()
        last = _user_last_request.get(user_id, 0)
        if now - last < 5:
            msg = await message.answer("⏳ Не так быстро! Подожди 5 секунд.")
            asyncio.create_task(_safe_delete(msg, 5))
            return
        _user_last_request[user_id] = now

        if not await _require_subscription(message):
            return

        if not await database.can_make_request(user_id, config.DAILY_LIMIT):
            ref_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{user_id}"
            await message.answer(
                "🚫 Лимит на сегодня исчерпан.\n\n"
                f"🎁 Пригласи друга — получишь +{config.REFERRAL_BONUS} проверку:\n"
                f"<code>{ref_link}</code>",
            )
            return

        data = await state.get_data()
        mode = data.get("mode")
        if not mode:
            await message.answer("Режим потерян. Нажми /start")
            return

        try:
            photo = message.photo[-1]
            if photo.file_size and photo.file_size > 20 * 1024 * 1024:
                await message.answer("❌ Фото больше 20 МБ.")
                return
            file = await bot.get_file(photo.file_id)
            fd, tmp = tempfile.mkstemp(suffix=".jpg")
            os.close(fd)
            await bot.download_file(file.file_path, destination=tmp)
            with open(tmp, "rb") as f:
                img_bytes = f.read()
            if not img_bytes:
                await message.answer("❌ Фото пустое. Попробуй другое.")
                return
        except Exception as e:
            log.exception("Download error: %s", e)
            await message.answer("❌ Не смог скачать фото.")
            return

        wait = await message.answer("🔍 Анализирую...")

        result = await database.get_cached(img_bytes, mode)
        from_cache = result is not None

        if not from_cache:
            try:
                result = await llm_client.analyze(img_bytes, mode=mode)
                await database.save_cache(img_bytes, mode, result)
            except Exception as e:
                log.exception("LLM error: %s", e)
                try:
                    await wait.edit_text("😴 Бот устал, попробуй через минуту.")
                except Exception:
                    pass
                return

        try:
            if mode == "meme":
                card_bytes = await asyncio.to_thread(
                    card_generator.create_meme_with_photo, img_bytes, result
                )
            else:
                card_bytes = await asyncio.to_thread(
                    card_generator.create_card, result, mode
                )
        except Exception as e:
            log.exception("Card error: %s", e)
            try:
                await wait.edit_text("Не смог собрать карточку.")
            except Exception:
                pass
            return

        captions = {
            "toxic": f"🧪 Токсик: <b>{result.get('toxic', '—')}</b> | Флаги: <b>{result.get('flags', 0)}%</b>",
            "kent": f"😎 Кент: <b>{result.get('verdict', '—')}</b> | Уровень: <b>{result.get('kent_level', 0)}%</b>",
            "fortune": f"🔮 Удача: <b>{result.get('luck', 0)}%</b> | {result.get('prediction', '—')}",
            "cringe": f"🤬 Кринж: <b>{result.get('cringe', 0)}%</b> | {result.get('verdict', '—')}",
            "flex": f"🌶️ Флекс: <b>{result.get('flex', 0)}%</b> | {result.get('verdict', '—')}",
            "psycho": f"🕵️ Тип: <b>{result.get('type', '—')}</b>\n{result.get('character', '—')}",
            "aura": f"🔮 Аура: <b>{result.get('color', '—')}</b> | {result.get('meaning', '—')}",
            "age": f"📱 Возраст: <b>{result.get('age', 0)}</b> | Ментальный: <b>{result.get('mental', 0)}</b>",
            "relationship": f"❤️ Совместимость: <b>{result.get('compat', 0)}%</b> | Главный: <b>{result.get('leader', '—')}</b>",
            "crush": f"🎯 Тип: <b>{result.get('type', '—')}</b>\nИщет: {result.get('seeks', '—')}",
            "leader": f"⚖️ Главный: <b>{result.get('leader', '—')}</b> | Баланс: <b>{result.get('balance', 50)}%</b>",
            "lonely": f"💀 Одиночество: <b>{result.get('lonely', 0)}%</b> | {result.get('status', '—')}",
            "meme": "😂 Мем готов!",
        }
        caption = captions.get(mode, "Готово!") + "\n\n💡 <i>Поделись с другом — пусть тоже проверит!</i>"

        try:
            pf = BufferedInputFile(card_bytes, filename="card.jpg")
            await message.answer_photo(photo=pf, caption=caption, reply_markup=_share_kb(mode))
            try:
                await wait.delete()
            except Exception:
                pass
            # ─── БЕЗОПАСНЫЙ score ───
            if not from_cache:
                score_field = MODE_SCORE_FIELD.get(mode)
                raw = result.get(score_field, 0) if score_field else 0
                try:
                    score = int(raw) if raw else 0
                except (ValueError, TypeError):
                    score = 0
                await database.log_request(user_id, score, mode)
        except TelegramAPIError as e:
            log.exception("Send error: %s", e)
            try:
                await wait.edit_text("Не смог отправить результат.")
            except Exception:
                pass

        await state.clear()

    except Exception as e:
        log.exception("Unhandled error in handle_photo: %s", e)
        try:
            await message.answer("😅 Что-то пошло не так. Нажми /start")
        except Exception:
            pass
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


# ═══════════════════════════════════════════
# ТЕКСТ
# ═══════════════════════════════════════════
@dp.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if not await _require_not_banned(user_id):
        status = await database.get_ban_status(user_id)
        if status.get("is_permanent"):
            return
        await message.answer(f"⏳ Ты забанен на {status.get('remaining_min', 30)} мин.")
        return

    if _is_spam_text(message.text):
        result = await database.add_violation(user_id, reason="мат/спам")
        if result["action"] == "permanent_ban":
            await message.answer("🚫 <b>Ты забанен навсегда</b> за нарушения.")
            try:
                await bot.send_message(
                    config.ADMIN_ID,
                    f"🚨 <b>ПЕРМАНЕНТНЫЙ БАН</b>\n"
                    f"ID: <code>{user_id}</code>\n"
                    f"Нарушений: {result['count']}"
                )
            except Exception:
                pass
        elif result["action"] == "temp_ban":
            await message.answer("🚫 <b>Ты забанен на 30 минут</b> за мат/спам.")
        else:
            await message.answer(
                f"⚠️ <b>Предупреждение</b> ({result['count']}/3)\n"
                f"Мат и спам запрещены."
            )
        return

    await message.answer("Нажми /start, чтобы открыть меню.")


# ═══════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════
async def main():
    await database.init_db()
    log.info("Mega bot started. Model=%s | Channel=%s | Admin=%s | DB=%s",
             config.LLM_MODEL, config.REQUIRED_CHANNEL or "OFF",
             config.ADMIN_ID or "NOT SET", config.DB_PATH)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped.")
