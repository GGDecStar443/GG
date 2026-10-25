import re

# ─────────────── 1. ТОКСИК ───────────────
TOXIC_PROMPT = """Ты — аналитик отношений. Проанализируй скрин переписки.
Ответь СТРОГО 5 строк:
ФЛАГИ: <0-100>%
ТОКСИК: <ты|он|она|оба|никто>
ТИП: <3-5 слов>
СОВЕТ: <до 15 слов>
ВЫВОД: <2-3 предложения>
Правила: только русский, без оскорблений, без диагнозов.
"""
def parse_toxic(t):
    r = {"flags": 0, "toxic": "никто", "type": "не определено", "advice": "будь собой", "verdict": "не разобрал"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ФЛАГИ"):
            m = re.search(r"(\d{1,3})", l)
            if m: r["flags"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("ТОКСИК"): r["toxic"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ТИП"): r["type"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ВЫВОД"): r["verdict"] = l.split(":", 1)[-1].strip()
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
    r = {"kent_level": 0, "verdict": "не человек", "character": "не определён", "prediction": "скинь фото", "advice": "будь осторожен"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ВЕРДИКТ"): r["verdict"] = l.split(":", 1)[-1].strip()
        elif u.startswith("УРОВЕНЬ КЕНТА"):
            m = re.search(r"(\d{1,3})", l)
            if m: r["kent_level"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("ХАРАКТЕР"): r["character"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ПРОГНОЗ"): r["prediction"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
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
    r = {"prediction": "тайна", "luck": 50, "love": "всё в твоих руках", "money": "скоро придёт", "advice": "слушай сердце"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ПРЕДСКАЗАНИЕ"): r["prediction"] = l.split(":", 1)[-1].strip()
        elif u.startswith("УДАЧА"):
            m = re.search(r"(\d{1,3})", l)
            if m: r["luck"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("ЛЮБОВЬ"): r["love"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ДЕНЬГИ"): r["money"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
    return r

# ─────────────── 4. МЕМ ───────────────
MEME_PROMPT = """Ты — мем-мейкер. Тебе скинули фото. Придумай текст для мема под это фото.
Ответь СТРОГО 4 строки:
ТЕКСТ СВЕРХУ: <до 6 слов>
ТЕКСТ СНИЗУ: <до 6 слов>
ЖАНР: <2-3 слова>
ХЕШТЕГ: <одно слово>
Правила: только русский, юмор без оскорблений.
"""
def parse_meme(t):
    r = {"top": "КОГДА", "bottom": "ВСЁ ПОШЛО НЕ ТАК", "genre": "жизненно", "hashtag": "мем"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ТЕКСТ СВЕРХУ"): r["top"] = l.split(":", 1)[-1].strip().upper()
        elif u.startswith("ТЕКСТ СНИЗУ"): r["bottom"] = l.split(":", 1)[-1].strip().upper()
        elif u.startswith("ЖАНР"): r["genre"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ХЕШТЕГ"): r["hashtag"] = l.split(":", 1)[-1].strip().lstrip("#")
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
    r = {"compat": 50, "type": "не определено", "leader": "никто", "forecast": "всё в ваших руках", "advice": "говорите друг с другом", "verdict": "не разобрал"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("СОВМЕСТИМОСТЬ"):
            m = re.search(r"(\d{1,3})", l)
            if m: r["compat"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("ТИП"): r["type"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ГЛАВНЫЙ"): r["leader"] = l.split(":", 1)[-1].strip().lower()
        elif u.startswith("ПРОГНОЗ"): r["forecast"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ВЫВОД"): r["verdict"] = l.split(":", 1)[-1].strip()
    return r

# ─────────────── 6. КРИНЖ ───────────────
CRINGE_PROMPT = """Ты — эксперт по кринжу. Тебе скинули фото. Оцени уровень кринжа (неловкости).
Ответь СТРОГО 4 строки:
КРИНЖ: <0-100>%
ПРИЧИНА: <2-3 слова>
ВЕРДИКТ: <1-2 предложения, почему это кринж>
СОВЕТ: <одно предложение, как исправить>
Правила: только русский, жёстко но не злобно, без оскорблений внешности.
"""
def parse_cringe(t):
    r = {"cringe": 0, "reason": "не понял", "verdict": "всё нормально", "advice": "будь собой"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("КРИНЖ"):
            m = re.search(r"(\d{1,3})", l)
            if m: r["cringe"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("ПРИЧИНА"): r["reason"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ВЕРДИКТ"): r["verdict"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
    return r

# ─────────────── 7. ФЛЕКС ───────────────
FLEX_PROMPT = """Ты — эксперт по соцсетям. Тебе скинули скрин поста/фото. Оцени уровень флекса (хвастовства).
Ответь СТРОГО 4 строки:
ФЛЕКС: <0-100>%
ТИП: <2-3 слова>
ВЕРДИКТ: <1-2 предложения, честно>
СОВЕТ: <одно предложение>
Правила: только русский, без оскорблений.
"""
def parse_flex(t):
    r = {"flex": 0, "type": "не понял", "verdict": "скромно", "advice": "будь собой"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ФЛЕКС"):
            m = re.search(r"(\d{1,3})", l)
            if m: r["flex"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("ТИП"): r["type"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ВЕРДИКТ"): r["verdict"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
    return r

# ─────────────── 8. ПСИХОПРОФИЛЬ ───────────────
PSYCHO_PROMPT = """Ты — психолог. Проанализируй селфи. Составь шутливый психологический портрет.
Ответь СТРОГО 4 строки:
ТИП: <2-3 слова, например: "Скрытый интроверт", "Душа компании">
ХАРАКТЕР: <2-3 предложения, точно про него>
ТАЙНА: <1 предложение, что он скрывает>
СОВЕТ: <1 предложение>
Правила: только русский, без оскорблений.
"""
def parse_psycho(t):
    r = {"type": "Загадка", "character": "Ты интересный человек", "secret": "У тебя есть секрет", "advice": "просто живи"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ТИП"): r["type"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ХАРАКТЕР"): r["character"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ТАЙНА"): r["secret"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
    return r

# ─────────────── 9. АУРА ───────────────
AURA_PROMPT = """Ты — экстрасенс. Проанализируй фото. Определи цвет ауры.
Ответь СТРОГО 4 строки:
ЦВЕТ: <название цвета, например: "Неоново-фиолетовый">
СМЫСЛ: <2-3 слова, что означает>
ОПИСАНИЕ: <2-3 предложения про характер>
СОВЕТ: <1 предложение>
Правила: только русский, мистика.
"""
def parse_aura(t):
    r = {"color": "Белый", "meaning": "Чистота", "desc": "Ты светлый человек", "advice": "слушай себя"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ЦВЕТ"): r["color"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СМЫСЛ"): r["meaning"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ОПИСАНИЕ"): r["desc"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
    return r

# ─────────────── 10. ГЛАВНЫЙ ───────────────
LEADER_PROMPT = """Ты — аналитик. Проанализируй скрин переписки. Определи, кто главный.
Ответь СТРОГО 4 строки:
ГЛАВНЫЙ: <он|она|оба|никто>
БАЛАНС: <0-100>% (0 - он главный, 100 - она главная)
ВЕРДИКТ: <1-2 предложения>
СОВЕТ: <1 предложение>
Правила: только русский.
"""
def parse_leader(t):
    r = {"leader": "оба", "balance": 50, "verdict": "Равноправие", "advice": "говорите"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ГЛАВНЫЙ"): r["leader"] = l.split(":", 1)[-1].strip().lower()
        elif u.startswith("БАЛАНС"):
            m = re.search(r"(\d{1,3})", l)
            if m: r["balance"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("ВЕРДИКТ"): r["verdict"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
    return r

# ─────────────── 11. ВОЗРАСТ ───────────────
AGE_PROMPT = """Ты — эксперт по лицам. Проанализируй селфи. Оцени возраст.
Ответь СТРОГО 4 строки:
ВОЗРАСТ: <число>
МЕНТАЛЬНЫЙ: <число>
ПРИЧИНА: <1-2 предложения, почему такая разница>
СОВЕТ: <1 предложение>
Правила: только русский, без оскорблений.
"""
def parse_age(t):
    r = {"age": 20, "mental": 25, "reason": "Ты выглядишь старше своих лет", "advice": "живи здесь и сейчас"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ВОЗРАСТ"):
            m = re.search(r"(\d{1,3})", l)
            if m: r["age"] = int(m.group(1))
        elif u.startswith("МЕНТАЛЬНЫЙ"):
            m = re.search(r"(\d{1,3})", l)
            if m: r["mental"] = int(m.group(1))
        elif u.startswith("ПРИЧИНА"): r["reason"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
    return r

# ─────────────── 12. ТИП КРАША ───────────────
CRUSH_PROMPT = """Ты — психолог. Проанализируй фото человека (это чей-то краш). 
Опиши его типаж и что он ищет в отношениях.
Ответь СТРОГО 4 строки:
ТИП: <2-3 слова>
ИЩЕТ: <1-2 предложения, что ему нужно>
ФЛАГИ: <1 предложение, красные флаги>
СОВЕТ: <1 предложение, как действовать>
Правила: только русский, без оскорблений.
"""
def parse_crush(t):
    r = {"type": "Загадочный", "seeks": "Ищет приключений", "flags": "Скрытный", "advice": "Будь собой"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ТИП"): r["type"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ИЩЕТ"): r["seeks"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ФЛАГИ"): r["flags"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
    return r

# ─────────────── 13. ОДИНОЧЕСТВО ───────────────
LONELY_PROMPT = """Ты — психолог. Проанализируй фото/селфи. Оцени уровень одиночества (с юмором).
Ответь СТРОГО 4 строки:
ОДИНОЧЕСТВО: <0-100>%
СТАТУС: <2-3 слова>
ОПИСАНИЕ: <1-2 предложения>
СОВЕТ: <1 предложение>
Правила: только русский, честно, но поддерживающе.
"""
def parse_lonely(t):
    r = {"lonely": 50, "status": "Сам по себе", "desc": "Иногда тебе грустно", "advice": "Напиши другу"}
    for l in t.splitlines():
        u = l.upper()
        if u.startswith("ОДИНОЧЕСТВО"):
            m = re.search(r"(\d{1,3})", l)
            if m: r["lonely"] = max(0, min(100, int(m.group(1))))
        elif u.startswith("СТАТУС"): r["status"] = l.split(":", 1)[-1].strip()
        elif u.startswith("ОПИСАНИЕ"): r["desc"] = l.split(":", 1)[-1].strip()
        elif u.startswith("СОВЕТ"): r["advice"] = l.split(":", 1)[-1].strip()
    return r

MODES = {
    "toxic": TOXIC_PROMPT, "kent": KENT_PROMPT, "fortune": FORTUNE_PROMPT,
    "meme": MEME_PROMPT, "relationship": RELATIONSHIP_PROMPT, "cringe": CRINGE_PROMPT,
    "flex": FLEX_PROMPT, "psycho": PSYCHO_PROMPT, "aura": AURA_PROMPT,
    "leader": LEADER_PROMPT, "age": AGE_PROMPT, "crush": CRUSH_PROMPT, "lonely": LONELY_PROMPT
}

PARSERS = {
    "toxic": parse_toxic, "kent": parse_kent, "fortune": parse_fortune,
    "meme": parse_meme, "relationship": parse_relationship, "cringe": parse_cringe,
    "flex": parse_flex, "psycho": parse_psycho, "aura": parse_aura,
    "leader": parse_leader, "age": parse_age, "crush": parse_crush, "lonely": parse_lonely
}
