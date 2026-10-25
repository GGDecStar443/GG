# Мега-бот: 4 режима + рефералка + подписка + кэш
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

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("mega_bot")

bot = Bot(token=config.BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


class Mode(StatesGroup):
    toxic = State()
    kent = State()
    fortune = State()
    meme = State()


MODE_INFO = {
    "toxic":   "🧪 Токсик-Чек",
    "kent":    "😎 Кент-Чек",
    "fortune": "🔮 Гадалка",
    "meme":    "😂 Мем-Генератор",
}


def _menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧪 Токсик-Чек",    callback_data="m_toxic")],
        [InlineKeyboardButton(text="😎 Кент-Чек",      callback_data="m_kent")],
        [InlineKeyboardButton(text="🔮 Гадалка",       callback_data="m_fortune")],
        [InlineKeyboardButton(text="😂 Мем-Генератор", callback_data="m_meme")],
    ])


async def _check_and_register(message: Message, referred_by: int = None):
    user_id = message.from_user.id
    username = message.from_user.username
    if referred_by == user_id:
        referred_by = None
    await database.register_user(user_id, username, referred_by)
    if referred_by:
        try:
            await database.add_referral_bonus(referred_by)
        except Exception as e:
            log.warning("Referral bonus failed: %s", e)


@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    args = message.text.split(maxsplit=1)
    referred_by = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1][4:])
        except ValueError:
            pass

    await _check_and_register(message, referred_by)

    if not await monetization.is_subscribed(bot, message.from_user.id):
        await message.answer(
            "👋 <b>Чтобы пользоваться ботом — подпишись на наш канал.</b>\n\n"
            "Это бесплатно и даёт доступ ко всем 4 режимам.",
            reply_markup=monetization.subscribe_kb(),
        )
        return

    ref_count = await database.get_referral_count(message.from_user.id)
    ref_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{message.from_user.id}"

    await message.answer(
        "👋 <b>Мега-Бот</b>\n\n"
        "Выбери режим:\n"
        "🧪 <b>Токсик-Чек</b> — кто токсик в переписке\n"
        "😎 <b>Кент-Чек</b> — что скажет твой кент\n"
        "🔮 <b>Гадалка</b> — предсказание\n"
        "😂 <b>Мем-Генератор</b> — мем из фото\n\n"
        f"⚡ Лимит: {config.DAILY_LIMIT} проверок/день\n"
        f"🎁 Приглашено друзей: <b>{ref_count}</b> (+1 проверка за каждого)\n\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>",
        reply_markup=_menu_kb(),
    )


@dp.callback_query(F.data == "check_sub")
async def check_subscription(cb: CallbackQuery, state: FSMContext):
    if await monetization.is_subscribed(bot, cb.from_user.id):
        await cb.message.edit_text("✅ Спасибо за подписку!\n\nТеперь выбери режим:", reply_markup=_menu_kb())
    else:
        await cb.answer("Ты ещё не подписался 🤔", show_alert=True)


@dp.callback_query(F.data.startswith("m_"))
async def choose_mode(cb: CallbackQuery, state: FSMContext):
    if not await monetization.is_subscribed(bot, cb.from_user.id):
        await cb.answer("Сначала подпишись на канал!", show_alert=True)
        return

    mode = cb.data.split("_", 1)[1]
    if mode not in MODE_INFO:
        await cb.answer("Неизвестный режим")
        return

    await state.set_state(getattr(Mode, mode))
    await cb.message.edit_text(f"<b>{MODE_INFO[mode]}</b>\n\nСкинь фото 👇")
    await cb.answer()


@dp.message(Command("toxic"))
async def cmd_toxic(m: Message, state: FSMContext):
    await state.set_state(Mode.toxic)
    await m.answer("🧪 Скинь скрин переписки 👇")


@dp.message(Command("kent"))
async def cmd_kent(m: Message, state: FSMContext):
    await state.set_state(Mode.kent)
    await m.answer("😎 Скинь фото кента 👇")


@dp.message(Command("fortune"))
async def cmd_fortune(m: Message, state: FSMContext):
    await state.set_state(Mode.fortune)
    await m.answer("🔮 Скинь фото — погадаю 👇")


@dp.message(Command("meme"))
async def cmd_meme(m: Message, state: FSMContext):
    await state.set_state(Mode.meme)
    await m.answer("😂 Скинь фото — сделаю мем 👇")


@dp.message(Command("myref"))
async def cmd_myref(m: Message):
    ref_count = await database.get_referral_count(m.from_user.id)
    ref_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{m.from_user.id}"
    await m.answer(
        f"🎁 Приглашено: <b>{ref_count}</b> друзей\n\n"
        f"🔗 Твоя ссылка:\n<code>{ref_link}</code>\n\n"
        f"За каждого друга: +{config.REFERRAL_BONUS} проверки (до +{config.REFERRAL_DAILY_LIMIT}/день)"
    )


@dp.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    if not await monetization.is_subscribed(bot, message.from_user.id):
        await message.answer("👋 Сначала подпишись на канал.", reply_markup=monetization.subscribe_kb())
        return

    current = await state.get_state()
    mode = None
    for name in MODE_INFO:
        if current == getattr(Mode, name).state:
            mode = name
            break

    if not mode:
        await message.answer("Сначала выбери режим:", reply_markup=_menu_kb())
        return

    if not await database.can_make_request(message.from_user.id, config.DAILY_LIMIT):
        ref_link = f"https://t.me/{config.BOT_USERNAME}?start=ref_{message.from_user.id}"
        await message.answer(
            "🚫 Лимит на сегодня исчерпан.\n\n"
            f"🎁 Пригласи друга и получи +{config.REFERRAL_BONUS} проверку:\n"
            f"<code>{ref_link}</code>"
        )
        return

    tmp = None
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        fd, tmp = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        await bot.download_file(file.file_path, destination=tmp)
        with open(tmp, "rb") as f:
            image_bytes = f.read()
    except Exception as e:
        log.exception("Download error: %s", e)
        await message.answer("Не смог скачать фото.")
        if tmp and os.path.exists(tmp): os.remove(tmp)
        return

    wait = await message.answer("🔍 Анализирую…")

    result = await database.get_cached(image_bytes, mode)
    from_cache = result is not None

    if not from_cache:
        try:
            result = await llm_client.analyze(image_bytes, mode=mode)
            await database.save_cache(image_bytes, mode, result)
        except Exception as e:
            log.exception("LLM error: %s", e)
            await wait.edit_text("😴 Бот устал, попробуй через минуту.")
            if tmp and os.path.exists(tmp): os.remove(tmp)
            return

    try:
        card_bytes = card_generator.create_card(result, mode=mode)
    except Exception as e:
        log.exception("Card error: %s", e)
        await wait.edit_text("Не смог собрать карточку.")
        if tmp and os.path.exists(tmp): os.remove(tmp)
        return

    if mode == "toxic":
        caption = (f"🧪 <b>Токсик-Чек</b>\n\n"
                   f"🚩 Флаги: <b>{result['flags']}%</b>\n"
                   f"👤 Токсик: <b>{result['toxic']}</b>\n"
                   f"💔 Тип: <b>{result['type']}</b>\n\n"
                   f"💬 <b>Совет:</b> {result['advice']}\n\n"
                   f"📝 {result['verdict']}")
        score = int(result.get("flags", 0))
    elif mode == "kent":
        caption = (f"😎 <b>Кент-Чек</b>\n\n"
                   f"🔥 Уровень: <b>{result['kent_level']}%</b>\n"
                   f"💬 Вердикт: <b>«{result['verdict']}»</b>\n"
                   f"🧠 Характер: <b>{result['character']}</b>\n\n"
                   f"🔮 <b>Прогноз:</b> {result['prediction']}\n\n"
                   f"💡 <b>Совет:</b> {result['advice']}")
        score = int(result.get("kent_level", 0))
    elif mode == "fortune":
        caption = (f"🔮 <b>Гадалка</b>\n\n"
                   f"✨ Предсказание: <b>«{result['prediction']}»</b>\n"
                   f"🍀 Удача: <b>{result['luck']}%</b>\n\n"
                   f"💕 <b>Любовь:</b> {result['love']}\n"
                   f"💰 <b>Деньги:</b> {result['money']}\n\n"
                   f"✨ <b>Совет:</b> {result['advice']}")
        score = int(result.get("luck", 0))
    else:
        caption = (f"😂 <b>Мем-Генератор</b>\n\n"
                   f"⬆️ {result['top']}\n"
                   f"⬇️ {result['bottom']}\n\n"
                   f"#{result['hashtag']} • {result['genre']}")
        score = 0

    try:
        pf = BufferedInputFile(card_bytes, filename=f"{mode}.png")
        await message.answer_photo(photo=pf, caption=caption)
        await wait.delete()
    except TelegramAPIError as e:
        log.exception("Send error: %s", e)
        await wait.edit_text("Не смог отправить результат.")

    if not from_cache:
        try:
            await database.log_request(message.from_user.id, score, mode)
        except Exception as e:
            log.exception("DB log error: %s", e)

    if tmp and os.path.exists(tmp):
        try: os.remove(tmp)
        except OSError: pass


@dp.message(F.text)
async def handle_text(message: Message, state: FSMContext):
    await message.answer("Выбери режим:", reply_markup=_menu_kb())


async def main():
    await database.init_db()
    log.info("Mega bot started. Model=%s | Channel=%s",
             config.LLM_MODEL, config.REQUIRED_CHANNEL or "OFF")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped.")
