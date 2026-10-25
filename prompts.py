import re

TOXIC_PROMPT = """Ты — аналитик отношений. Проанализируй скрин переписки.
Ответь СТРОГО 5 строк:
ФЛАГИ: <0-100>%
ТОКСИК: <ты|он|она|оба|никто>
ТИП: <3-5 слов>
СОВЕТ: <до 15 слов>
ВЫВОД: <2-3 предложения>
Правила: только русский, без оскорблений, без диагнозов.
"""

def parse_toxic(text: str) -> dict:
    r = {"flags": 0, "toxic": "никто", "type": "не определено",
         "advice": "будь собой", "verdict": "не разобрал"}
    for line in text.splitlines():
        line = line.strip(); u = line.upper()
        if u.startswith("ФЛАГИ"):
            m = re.search(r"(\d{1,3})", line)
            if m: r["flags"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("ТОКСИК"):
            r["toxic"] = line.split(":", 1)[-1].strip() or "никто"
        elif u.startswith("ТИП"):
            r["type"] = line.split(":", 1)[-1].strip() or "не определено"
        elif u.startswith("СОВЕТ"):
            r["advice"] = line.split(":", 1)[-1].strip() or "будь собой"
        elif u.startswith("ВЫВОД"):
            r["verdict"] = line.split(":", 1)[-1].strip()
    return r


KENT_PROMPT = """Ты — кент (лучший друг). Тебе скинули фото человека.
Выдай жёсткий, но ржачный приговор.
Ответь СТРОГО 5 строк:
ВЕРДИКТ: <2-3 слова>
УРОВЕНЬ КЕНТА: <0-100>%
ХАРАКТЕР: <3-4 слова>
ПРОГНОЗ: <одно жёсткое предложение>
СОВЕТ: <одно предложение>
Правила: только русский, без оскорблений по внешности/нации.
"""

def parse_kent(text: str) -> dict:
    r = {"kent_level": 0, "verdict": "не человек", "character": "не определён",
         "prediction": "скинь фото", "advice": "будь осторожен"}
    for line in text.splitlines():
        line = line.strip(); u = line.upper()
        if u.startswith("ВЕРДИКТ"):
            r["verdict"] = line.split(":", 1)[-1].strip() or "без вердикта"
        elif u.startswith("УРОВЕНЬ КЕНТА"):
            m = re.search(r"(\d{1,3})", line)
            if m: r["kent_level"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("ХАРАКТЕР"):
            r["character"] = line.split(":", 1)[-1].strip() or "не определён"
        elif u.startswith("ПРОГНОЗ"):
            r["prediction"] = line.split(":", 1)[-1].strip() or "не предсказать"
        elif u.startswith("СОВЕТ"):
            r["advice"] = line.split(":", 1)[-1].strip() or "будь осторожен"
    return r


FORTUNE_PROMPT = """Ты — мистическая гадалка. Тебе скинули фото. Сделай шутливое предсказание.
Ответь СТРОГО 5 строк:
ПРЕДСКАЗАНИЕ: <2-3 слова>
УДАЧА: <0-100>%
ЛЮБОВЬ: <одно предложение>
ДЕНЬГИ: <одно предложение>
СОВЕТ: <одно предложение>
Правила: только русский, мистический тон, без обещаний смерти/болезней.
"""

def parse_fortune(text: str) -> dict:
    r = {"prediction": "тайна", "luck": 50, "love": "всё в твоих руках",
         "money": "скоро придёт", "advice": "слушай сердце"}
    for line in text.splitlines():
        line = line.strip(); u = line.upper()
        if u.startswith("ПРЕДСКАЗАНИЕ"):
            r["prediction"] = line.split(":", 1)[-1].strip() or "тайна"
        elif u.startswith("УДАЧА"):
            m = re.search(r"(\d{1,3})", line)
            if m: r["luck"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("ЛЮБОВЬ"):
            r["love"] = line.split(":", 1)[-1].strip() or "всё в твоих руках"
        elif u.startswith("ДЕНЬГИ"):
            r["money"] = line.split(":", 1)[-1].strip() or "скоро придёт"
        elif u.startswith("СОВЕТ"):
            r["advice"] = line.split(":", 1)[-1].strip() or "слушай сердце"
    return r


MEME_PROMPT = """Ты — профессиональный мем-мейкер. Тебе скинули фото. 
Придумай ИДЕАЛЬНЫЙ мем под это фото.

Посмотри на фото: что там? какое настроение? что происходит? 
Придумай текст, который РАССМЕШИТ и подойдёт именно к этому фото.

Ответь СТРОГО 4 строки:
ТЕКСТ СВЕРХУ: <до 6 слов, короткая завязка>
ТЕКСТ СНИЗУ: <до 6 слов, смешная развязка>
ЖАНР: <2-3 слова>
ХЕШТЕГ: <одно слово>

ПРАВИЛА:
- Только русский
- Не оскорбляй людей по внешности/нации
- Юмор должен подходить под фото (если человек грустный — не пиши "радость")
- Будь креативным, добавь мемный сленг
"""

def parse_meme(text: str) -> dict:
    r = {"top": "КОГДА", "bottom": "ВСЁ ПОШЛО НЕ ТАК",
         "genre": "жизненно", "hashtag": "мем"}
    for line in text.splitlines():
        line = line.strip(); u = line.upper()
        if u.startswith("ТЕКСТ СВЕРХУ"):
            r["top"] = line.split(":", 1)[-1].strip().upper() or "КОГДА"
        elif u.startswith("ТЕКСТ СНИЗУ"):
            r["bottom"] = line.split(":", 1)[-1].strip().upper() or "ВСЁ ПОШЛО НЕ ТАК"
        elif u.startswith("ЖАНР"):
            r["genre"] = line.split(":", 1)[-1].strip() or "жизненно"
        elif u.startswith("ХЕШТЕГ"):
            r["hashtag"] = line.split(":", 1)[-1].strip().lstrip("#") or "мем"
    return r


MODES = {
    "toxic":   {"prompt": TOXIC_PROMPT,   "parser": parse_toxic},
    "kent":    {"prompt": KENT_PROMPT,    "parser": parse_kent},
    "fortune": {"prompt": FORTUNE_PROMPT, "parser": parse_fortune},
    "meme":    {"prompt": MEME_PROMPT,    "parser": parse_meme},
}
