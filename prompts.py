import re

# ─────────────── 1. ТОКСИК ───────────────
TOXIC_PROMPT = """Ты — аналитик отношений. Посмотри на скрин переписки 
и дай честный вердикт.

КРИТИЧЕСКИ ВАЖНО: ответ строго из 5 строк, каждая с новой строки.
Никакого вступления, объяснений, markdown, звёздочек. Только эти 5 строк:

ФЛАГИ: <число от 0 до 100>%
ТОКСИК: <ты|он|она|оба|никто>
ТИП: <3-5 слов, например: "Страсть + хаос", "Односторонняя любовь">
СОВЕТ: <одно предложение, до 15 слов>
ВЫВОД: <2-3 предложения честного разбора>

ПРАВИЛА:
- Только русский язык
- Если на фото не переписка → ФЛАГИ: 0% | ТОКСИК: никто | ТИП: не переписка | СОВЕТ: скинь скрин переписки | ВЫВОД: я не вижу тут диалога.
- Будь прямым и жёстким, но без оскорблений
- Не ставь диагнозы
- Если есть конфликт/манипуляции/давление — ФЛАГИ ВЫСОКИЕ (60-100%), НЕ ставь 0%!
"""

def parse_toxic(t):
    r = {"flags": 0, "toxic": "никто", "type": "не определено",
         "advice": "будь собой", "verdict": "не разобрал"}
    # Regex по всему тексту (ловит даже в одной строке)
    m = re.search(r"ФЛАГИ\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
    if m:
        r["flags"] = max(0, min(100, int(m.group(1))))

    m = re.search(r"ТОКСИК\s*[:\-]?\s*(ты|он|она|оба|никто)", t, re.IGNORECASE)
    if m:
        r["toxic"] = m.group(1).lower()

    m = re.search(r"ТИП\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m:
        r["type"] = m.group(1).strip()

    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m:
        r["advice"] = m.group(1).strip()

    m = re.search(r"ВЫВОД\s*[:\-]\s*(.+)", t, re.IGNORECASE | re.DOTALL)
    if m:
        verdict = m.group(1).strip()
        sentences = re.split(r"(?<=[.!?])\s+", verdict)
        r["verdict"] = " ".join(sentences[:3]).strip()

    return r


# ─────────────── 2. КЕНТ ───────────────
KENT_PROMPT = """Ты — кент (лучший друг). Тебе скинули фото человека. Выдай жёсткий, но ржачный приговор.
Ответь СТРОГО 5 строк:
ВЕРДИКТ: <2-3 слова>
УРОВЕНЬ КЕНТА: <0-100>%
ХАРАКТЕР: <3-4 слова>
ПРОГНОЗ: <одно жёсткое предложение>
СОВЕТ: <одно предложение>
Правила: только русский, без оскорблений по внешности/нации.
"""
def parse_kent(t):
    r = {"kent_level": 0, "verdict": "не человек", "character": "не определён",
         "prediction": "скинь фото", "advice": "будь осторожен"}
    m = re.search(r"ВЕРДИКТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["verdict"] = m.group(1).strip()
    m = re.search(r"УРОВЕНЬ КЕНТА\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
    if m: r["kent_level"] = max(0, min(100, int(m.group(1))))
    m = re.search(r"ХАРАКТЕР\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["character"] = m.group(1).strip()
    m = re.search(r"ПРОГНОЗ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["prediction"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    return r


# ─────────────── 3. ГАДАЛКА ───────────────
FORTUNE_PROMPT = """Ты — мистическая гадалка. Тебе скинули фото. Сделай шутливое предсказание.
Ответь СТРОГО 5 строк:
ПРЕДСКАЗАНИЕ: <2-3 слова>
УДАЧА: <0-100>%
ЛЮБОВЬ: <одно предложение>
ДЕНЬГИ: <одно предложение>
СОВЕТ: <одно предложение>
Правила: только русский, мистический тон, без обещаний смерти/болезней.
"""
def parse_fortune(t):
    r = {"prediction": "тайна", "luck": 50, "love": "всё в твоих руках",
         "money": "скоро придёт", "advice": "слушай сердце"}
    m = re.search(r"ПРЕДСКАЗАНИЕ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["prediction"] = m.group(1).strip()
    m = re.search(r"УДАЧА\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
    if m: r["luck"] = max(0, min(100, int(m.group(1))))
    m = re.search(r"ЛЮБОВЬ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["love"] = m.group(1).strip()
    m = re.search(r"ДЕНЬГИ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["money"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    return r


# ─────────────── 4. МЕМ ───────────────
MEME_PROMPT = """Ты — мем-мейкер. Тебе скинули фото. Придумай текст для мема.
Ответь СТРОГО 4 строки:
ТЕКСТ СВЕРХУ: <до 6 слов>
ТЕКСТ СНИЗУ: <до 6 слов>
ЖАНР: <2-3 слова>
ХЕШТЕГ: <одно слово>
Правила: только русский, юмор без оскорблений.
"""
def parse_meme(t):
    r = {"top": "КОГДА", "bottom": "ВСЁ ПОШЛО НЕ ТАК",
         "genre": "жизненно", "hashtag": "мем"}
    m = re.search(r"ТЕКСТ СВЕРХУ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["top"] = m.group(1).strip().upper()
    m = re.search(r"ТЕКСТ СНИЗУ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["bottom"] = m.group(1).strip().upper()
    m = re.search(r"ЖАНР\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["genre"] = m.group(1).strip()
    m = re.search(r"ХЕШТЕГ\s*[:\-]?\s*#?([^\n]+)", t, re.IGNORECASE)
    if m: r["hashtag"] = m.group(1).strip().lstrip("#")
    return r


# ─────────────── 5. ОТНОШЕНИЯ ───────────────
RELATIONSHIP_PROMPT = """Ты — психолог. Проанализируй фото пары. Оцени язык тела и динамику.
Ответь СТРОГО 6 строк:
СОВМЕСТИМОСТЬ: <0-100>%
ТИП: <2-3 слова>
ГЛАВНЫЙ: <он|она|оба|никто>
ПРОГНОЗ: <одно предложение>
СОВЕТ: <одно предложение>
ВЫВОД: <2-3 предложения>
Правила: только русский, честно, без оскорблений.
"""
def parse_relationship(t):
    r = {"compat": 50, "type": "не определено", "leader": "никто",
         "forecast": "всё в ваших руках", "advice": "говорите друг с другом",
         "verdict": "не разобрал"}
    m = re.search(r"СОВМЕСТИМОСТЬ\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
    if m: r["compat"] = max(0, min(100, int(m.group(1))))
    m = re.search(r"ТИП\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["type"] = m.group(1).strip()
    m = re.search(r"ГЛАВНЫЙ\s*[:\-]\s*(он|она|оба|никто)", t, re.IGNORECASE)
    if m: r["leader"] = m.group(1).lower()
    m = re.search(r"ПРОГНОЗ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["forecast"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    m = re.search(r"ВЫВОД\s*[:\-]\s*(.+)", t, re.IGNORECASE | re.DOTALL)
    if m:
        v = m.group(1).strip()
        sentences = re.split(r"(?<=[.!?])\s+", v)
        r["verdict"] = " ".join(sentences[:3]).strip()
    return r


# ─────────────── 6. КРИНЖ ───────────────
CRINGE_PROMPT = """Ты — эксперт по кринжу. Тебе скинули фото. Оцени уровень кринжа (неловкости).
Ответь СТРОГО 4 строки:
КРИНЖ: <0-100>%
ПРИЧИНА: <2-3 слова>
ВЕРДИКТ: <1-2 предложения>
СОВЕТ: <одно предложение>
Правила: только русский, жёстко но не злобно, без оскорблений внешности.
"""
def parse_cringe(t):
    r = {"cringe": 0, "reason": "не понял", "verdict": "всё нормально", "advice": "будь собой"}
    m = re.search(r"КРИНЖ\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
    if m: r["cringe"] = max(0, min(100, int(m.group(1))))
    m = re.search(r"ПРИЧИНА\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["reason"] = m.group(1).strip()
    m = re.search(r"ВЕРДИКТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["verdict"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    return r


# ─────────────── 7. ФЛЕКС ───────────────
FLEX_PROMPT = """Ты — эксперт по соцсетям. Тебе скинули скрин поста. Оцени уровень флекса (хвастовства).
Ответь СТРОГО 4 строки:
ФЛЕКС: <0-100>%
ТИП: <2-3 слова>
ВЕРДИКТ: <1-2 предложения>
СОВЕТ: <одно предложение>
Правила: только русский, без оскорблений.
"""
def parse_flex(t):
    r = {"flex": 0, "type": "не понял", "verdict": "скромно", "advice": "будь собой"}
    m = re.search(r"ФЛЕКС\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
    if m: r["flex"] = max(0, min(100, int(m.group(1))))
    m = re.search(r"ТИП\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["type"] = m.group(1).strip()
    m = re.search(r"ВЕРДИКТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["verdict"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    return r


# ─────────────── 8. ПСИХОПРОФИЛЬ ───────────────
PSYCHO_PROMPT = """Ты — психолог. Проанализируй селфи. Составь шутливый психологический портрет.
Ответь СТРОГО 4 строки:
ТИП: <2-3 слова>
ХАРАКТЕР: <2-3 предложения>
ТАЙНА: <1 предложение>
СОВЕТ: <1 предложение>
Правила: только русский, без оскорблений.
"""
def parse_psycho(t):
    r = {"type": "Загадка", "character": "Ты интересный человек",
         "secret": "У тебя есть секрет", "advice": "просто живи"}
    m = re.search(r"ТИП\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["type"] = m.group(1).strip()
    m = re.search(r"ХАРАКТЕР\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["character"] = m.group(1).strip()
    m = re.search(r"ТАЙНА\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["secret"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    return r


# ─────────────── 9. АУРА ───────────────
AURA_PROMPT = """Ты — экстрасенс. Проанализируй фото. Определи цвет ауры.
Ответь СТРОГО 4 строки:
ЦВЕТ: <название цвета>
СМЫСЛ: <2-3 слова>
ОПИСАНИЕ: <2-3 предложения>
СОВЕТ: <1 предложение>
Правила: только русский, мистика.
"""
def parse_aura(t):
    r = {"color": "Белый", "meaning": "Чистота",
         "desc": "Ты светлый человек", "advice": "слушай себя"}
    m = re.search(r"ЦВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["color"] = m.group(1).strip()
    m = re.search(r"СМЫСЛ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["meaning"] = m.group(1).strip()
    m = re.search(r"ОПИСАНИЕ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["desc"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    return r


# ─────────────── 10. ГЛАВНЫЙ ───────────────
LEADER_PROMPT = """Ты — аналитик. Проанализируй скрин переписки. Определи, кто главный.
Ответь СТРОГО 4 строки:
ГЛАВНЫЙ: <он|она|оба|никто>
БАЛАНС: <0-100>%
ВЕРДИКТ: <1-2 предложения>
СОВЕТ: <1 предложение>
Правила: только русский.
"""
def parse_leader(t):
    r = {"leader": "оба", "balance": 50, "verdict": "Равноправие", "advice": "говорите"}
    m = re.search(r"ГЛАВНЫЙ\s*[:\-]\s*(он|она|оба|никто)", t, re.IGNORECASE)
    if m: r["leader"] = m.group(1).lower()
    m = re.search(r"БАЛАНС\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
    if m: r["balance"] = max(0, min(100, int(m.group(1))))
    m = re.search(r"ВЕРДИКТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["verdict"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    return r


# ─────────────── 11. ВОЗРАСТ ───────────────
AGE_PROMPT = """Ты — эксперт по лицам. Проанализируй селфи. Оцени возраст.
Ответь СТРОГО 4 строки:
ВОЗРАСТ: <число>
МЕНТАЛЬНЫЙ: <число>
ПРИЧИНА: <1-2 предложения>
СОВЕТ: <1 предложение>
Правила: только русский, без оскорблений.
"""
def parse_age(t):
    r = {"age": 20, "mental": 25, "reason": "Ты выглядишь старше своих лет", "advice": "живи здесь и сейчас"}
    m = re.search(r"ВОЗРАСТ\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
    if m: r["age"] = int(m.group(1))
    m = re.search(r"МЕНТАЛЬНЫЙ\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
    if m: r["mental"] = int(m.group(1))
    m = re.search(r"ПРИЧИНА\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["reason"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    return r


# ─────────────── 12. ТИП КРАША (усилено) ───────────────
CRUSH_PROMPT = """Ты — эксперт по отношениям. Тебе скинули фото человека. 
Проанализируй его: выражение лица, стиль, взгляд, позу. 
Опиши типаж ИМЕННО ЭТОГО человека (не общий!).

КРИТИЧЕСКИ ВАЖНО: ответ строго 4 строки, каждая с новой.
Никаких вступлений, объяснений, скобок. Только эти 4 строки:

ТИП: <2-3 слова, ОПРЕДЕЛЁННЫЙ типаж, например: "Мачо-романтик", "Уставший интеллектуал", "Спортивный задира">
ИЩЕТ: <1-2 предложения, что он ищет в отношениях>
ФЛАГИ: <одно честное предложение, какие красные флаги>
СОВЕТ: <одно короткое предложение>

ПРАВИЛА:
- Только русский
- Опирайся на ВНЕШНОСТЬ и ВАЙБ на фото (не выдумывай)
- Не пиши общие фразы типа "Загадочный" или "Интересный"
- Будь честным и конкретным
- Без оскорблений
"""

def parse_crush(t):
    r = {"type": "не определён", "seeks": "не понял",
         "flags": "не нашёл", "advice": "будь собой"}
    m = re.search(r"ТИП\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["type"] = m.group(1).strip()
    m = re.search(r"ИЩЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["seeks"] = m.group(1).strip()
    m = re.search(r"ФЛАГИ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["flags"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    return r


# ─────────────── 13. ОДИНОЧЕСТВО ───────────────
LONELY_PROMPT = """Ты — психолог. Проанализируй фото. Оцени уровень одиночества (с юмором).
Ответь СТРОГО 4 строки:
ОДИНОЧЕСТВО: <0-100>%
СТАТУС: <2-3 слова>
ОПИСАНИЕ: <1-2 предложения>
СОВЕТ: <1 предложение>
Правила: только русский, честно, но поддерживающе.
"""
def parse_lonely(t):
    r = {"lonely": 50, "status": "Сам по себе",
         "desc": "Иногда тебе грустно", "advice": "Напиши другу"}
    m = re.search(r"ОДИНОЧЕСТВО\s*[:\-]?\s*(\d{1,3})", t, re.IGNORECASE)
    if m: r["lonely"] = max(0, min(100, int(m.group(1))))
    m = re.search(r"СТАТУС\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["status"] = m.group(1).strip()
    m = re.search(r"ОПИСАНИЕ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["desc"] = m.group(1).strip()
    m = re.search(r"СОВЕТ\s*[:\-]\s*([^\n]+)", t, re.IGNORECASE)
    if m: r["advice"] = m.group(1).strip()
    return r


MODES = {
    "toxic": TOXIC_PROMPT, "kent": KENT_PROMPT, "fortune": FORTUNE_PROMPT,
    "meme": MEME_PROMPT, "relationship": RELATIONSHIP_PROMPT, "cringe": CRINGE_PROMPT,
    "flex": FLEX_PROMPT, "psycho": PSYCHO_PROMPT, "aura": AURA_PROMPT,
    "leader": LEADER_PROMPT, "age": AGE_PROMPT, "crush": CRUSH_PROMPT, "lonely": LONELY_PROMPT,
}

PARSERS = {
    "toxic": parse_toxic, "kent": parse_kent, "fortune": parse_fortune,
    "meme": parse_meme, "relationship": parse_relationship, "cringe": parse_cringe,
    "flex": parse_flex, "psycho": parse_psycho, "aura": parse_aura,
    "leader": parse_leader, "age": parse_age, "crush": parse_crush, "lonely": parse_lonely,
}
