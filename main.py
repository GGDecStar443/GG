# Точка входа и все хендлеры бота
import asyncio
import logging
import os
import tempfile
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.exceptions import TelegramAPIError

import config
import database
import gemini_client
import card_generator

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("toxic_check")

# Инициализация бота и диспетчера
bot = Bot(
    token=config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

# Inline-кнопка "Скинуть другу"
SHARE_URL = f"https://t.me/{config.BOT_USERNAME}"
share_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Скинуть другу", url=SHARE_URL)],
    ]
)


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Приветствие и инструкция."""
    text = (
        "🧪 <b>Токсик-Чек</b>\n\n"
        "Скинь мне скрин переписки — и я скажу, кто в ней токсик 👀\n\n"
        "📸 Просто отправь фото диалога, и получишь:\n"
        "• уровень красных флагов (%)\n"
        "• кто токсик\n"
        "• тип отношений\n"
        "• жёсткий совет\n\n"
        f"⚡ Дневной лимит: {config.DAILY_LIMIT} проверок в день.\n"
        "Погнали 👇"
    )
    await message.answer(text)


@dp.message(F.photo)
async def handle_photo(message: Message) -> None:
    """Основная логика: проверка лимита, анализ, генерация карточки."""
    user_id = message.from_user.id
    username = message.from_user.username

    # 1. Проверка лимита
    try:
        allowed = await database.can_make_request(user_id, config.DAILY_LIMIT)
    except Exception as e:
        log.exception("DB error in can_make_request: %s", e)
        await message.answer("Ошибка базы, попробуй позже.")
        return

    if not allowed:
        await message.answer(
            "🚫 Дневной лимит исчерпан.\n"
            "Возвращайся завтра — снова будет 5 проверок 💜"
        )
        return

    # 2. Скачиваем фото во временный файл
    tmp_path = None
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)

        fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)

        await bot.download_file(file.file_path, destination=tmp_path)

        with open(tmp_path, "rb") as f:
            image_bytes = f.read()

    except TelegramAPIError as e:
        log.exception("Telegram download error: %s", e)
        await message.answer("Не смог скачать фото, попробуй ещё раз.")
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        return
    except Exception as e:
        log.exception("Unexpected error on download: %s", e)
        await message.answer("Что-то пошло не так, попробуй ещё раз.")
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        return

    # 3. Плейсхолдер
    wait_msg = await message.answer("🔍 Анализирую переписку…")

    # 4. Анализ через Groq (Llama 3.2 Vision)
    try:
        result = await gemini_client.analyze(image_bytes)
    except Exception as e:
        log.exception("Groq error: %s", e)
        await wait_msg.edit_text("😴 Бот устал, попробуй через минуту.")
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        return

    # 5. Генерация карточки
    try:
        card_bytes = card_generator.create_card(result)
    except Exception as e:
        log.exception("Card generation error: %s", e)
        await wait_msg.edit_text("Не смог собрать карточку, попробуй ещё раз.")
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        return

    # 6. Текст вердикта
    flags = result["flags"]
    verdict_text = (
        f"🧪 <b>Токсик-Чек</b>\n\n"
        f"🚩 Флаги: <b>{flags}%</b>\n"
        f"👤 Токсик: <b>{result['toxic']}</b>\n"
        f"💔 Тип: <b>{result['type']}</b>\n\n"
        f"💬 <b>Совет:</b> {result['advice']}\n\n"
        f"📝 {result['verdict']}"
    )

    # 7. Отправляем карточку с текстом и кнопкой
    try:
        await message.answer_photo(
            photo=card_bytes,
            caption=verdict_text,
            reply_markup=share_kb,
        )
        await wait_msg.delete()
    except TelegramAPIError as e:
        log.exception("Send result error: %s", e)
        await wait_msg.edit_text("Не смог отправить результат, попробуй ещё раз.")

    # 8. Логирование в БД
    try:
        await database.log_request(
            user_id=user_id,
            username=username,
            flags=int(flags),
            toxic_who=str(result["toxic"]),
        )
    except Exception as e:
        log.exception("DB log error: %s", e)

    # 9. Логирование в канал
    if config.LOG_CHANNEL_ID:
        try:
            await bot.send_message(
                config.LOG_CHANNEL_ID,
                f"👤 @{username or user_id}\n🚩 {flags}%\n👤 {result['toxic']}",
            )
        except Exception as e:
            log.warning("Log channel error: %s", e)

    # 10. Удаление временного файла
    if tmp_path and os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@dp.message(F.text)
async def handle_text(message: Message) -> None:
    """Любой текст кроме /start."""
    await message.answer("Скинь мне скрин переписки, и я скажу, кто в ней токсик 👀")


@dp.callback_query()
async def handle_callback(callback: CallbackQuery) -> None:
    """Заглушка для коллбеков."""
    await callback.answer()


async def main() -> None:
    """Инициализация БД и запуск поллинга."""
    await database.init_db()
    log.info(
        "Bot started. Model=%s | Daily limit=%s",
        config.GROQ_MODEL, config.DAILY_LIMIT,
    )
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot stopped.")