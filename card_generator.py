# Генерация карточек: 13 режимов + автоподбор шрифтов + JPEG
import io
import os
from PIL import Image, ImageDraw, ImageFont
from config import BOT_USERNAME

WIDTH, HEIGHT = 1080, 1920
WHITE = (255, 255, 255)

_HERE = os.path.dirname(os.path.abspath(__file__))
_FONTS_DIR = os.path.join(_HERE, "fonts")


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for p in [
        os.path.join(_FONTS_DIR, name),
        os.path.join(_HERE, name),
        f"/usr/share/fonts/truetype/dejavu/{name}",
        f"C:/Windows/Fonts/{'arialbd.ttf' if bold else 'arial.ttf'}",
    ]:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except (OSError, IOError):
                continue
    return ImageFont.load_default()


def _fit_font(text: str, max_width: int, max_size: int, bold: bool = True, min_size: int = 40) -> ImageFont.FreeTypeFont:
    if not text.strip():
        return _font(max_size, bold=bold)
    for size in range(max_size, min_size - 1, -5):
        f = _font(size, bold=bold)
        bbox = f.getbbox(text)
        if bbox[2] - bbox[0] <= max_width:
            return f
    return _font(min_size, bold=bold)


def _gradient(top, bot) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), top)
    draw = ImageDraw.Draw(img)
    for y in range(HEIGHT):
        t = y / HEIGHT
        draw.line([(0, y), (WIDTH, y)], fill=(
            int(top[0] + (bot[0] - top[0]) * t),
            int(top[1] + (bot[1] - top[1]) * t),
            int(top[2] + (bot[2] - top[2]) * t),
        ))
    return img


def _wrap_lines(draw, text: str, font, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines if lines else [text]


def _center(draw, text, font, y, fill, max_w=None) -> int:
    if max_w:
        for ln in _wrap_lines(draw, text, font, max_w):
            bbox = draw.textbbox((0, 0), ln, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(((WIDTH - w) / 2, y), ln, font=font, fill=fill)
            y += h + 10
        return y
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)
    return y + h + 20


def _center_fit(draw, text, y_start: int, max_y: int, fill,
                max_w: int = WIDTH - 120, max_size: int = 50, min_size: int = 22) -> int:
    text = str(text).strip()
    if not text:
        return y_start

    best_size = min_size
    best_lines = [text]

    for size in range(max_size, min_size - 1, -2):
        font = _font(size)
        lines = _wrap_lines(draw, text, font, max_w)
        total_h = 0
        for ln in lines:
            bbox = draw.textbbox((0, 0), ln, font=font)
            total_h += (bbox[3] - bbox[1]) + 12
        if y_start + total_h <= max_y:
            best_size = size
            best_lines = lines
            break
        best_lines = lines

    font = _font(best_size)
    y = y_start
    for ln in best_lines:
        bbox = draw.textbbox((0, 0), ln, font=font)
        w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((WIDTH - w) / 2, y), ln, font=font, fill=fill)
        y += h + 12
    return y


def _pct_color(v: int):
    if v < 30:
        return (46, 204, 113)
    if v <= 70:
        return (241, 196, 15)
    return (231, 76, 60)


def _draw_big_pct(draw, value: int, y: int):
    pct = f"{value}%"
    f = _font(200, bold=True)
    bbox = draw.textbbox((0, 0), pct, font=f)
    pw, ph = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((WIDTH - pw) / 2, y), pct, font=f, fill=_pct_color(value))
    return y + ph + 20


def _save(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=False)
    return buf.getvalue()


def _signature(draw):
    _center(draw, f"@{BOT_USERNAME}", _font(32), HEIGHT - 90, (160, 160, 160))


# ═══════════════════════════════════════════
# 1. ТОКСИК (адаптивный)
# ═══════════════════════════════════════════
def _toxic(data: dict) -> bytes:
    img = _gradient((10, 10, 10), (26, 0, 51))
    d = ImageDraw.Draw(img)
    neon = (0, 255, 204)
    
    _center(d, "TOXIC CHECK", _font(70, True), 100, neon)
    
    y = _draw_big_pct(d, int(data.get("flags", 0)), 440)
    _center(d, "КРАСНЫХ ФЛАГОВ", _font(32), y, WHITE)

    # Токсик и Тип — адаптивные
    y = 850
    _center_fit(d, f"Токсик: {data.get('toxic', '—')}", y_start=y, max_y=940, fill=WHITE, max_size=55, min_size=35)
    _center_fit(d, f"Тип: {data.get('type', '—')}", y_start=960, max_y=1080, fill=WHITE, max_size=55, min_size=30)

    # СОВЕТ — адаптивный
    y = 1130
    _center(d, "СОВЕТ", _font(32), y, neon)
    _center_fit(d, data.get("advice", ""), y_start=y + 55, max_y=1420, fill=WHITE, max_size=48, min_size=25)

    # ВЫВОД — адаптивный
    y = 1470
    _center(d, "ВЫВОД", _font(32), y, neon)
    _center_fit(d, data.get("verdict", ""), y_start=y + 55, max_y=HEIGHT - 100, fill=WHITE, max_size=42, min_size=22)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 2. КЕНТ
# ═══════════════════════════════════════════
def _kent(data: dict) -> bytes:
    img = _gradient((15, 5, 0), (40, 10, 0))
    d = ImageDraw.Draw(img)
    acc = (255, 140, 0)
    _center(d, "KENT CHECK", _font(80, True), 100, acc)
    y = _draw_big_pct(d, int(data.get("kent_level", 0)), 380)
    _center(d, "УРОВЕНЬ КЕНТА", _font(32), y, WHITE)

    y = 850
    _center(d, "ВЕРДИКТ", _font(32), y, acc)
    _center_fit(d, f"«{data.get('verdict', '—')}»", y_start=y + 60, max_y=1030, fill=WHITE, max_size=50)

    _center(d, "ХАРАКТЕР", _font(32), 1100, acc)
    _center_fit(d, data.get("character", ""), y_start=1160, max_y=1290, fill=WHITE, max_size=45)

    _center(d, "ПРОГНОЗ", _font(32), 1300, acc)
    _center_fit(d, data.get("prediction", ""), y_start=1360, max_y=1520, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(32), 1550, acc)
    _center_fit(d, data.get("advice", ""), y_start=1610, max_y=HEIGHT - 120, fill=WHITE, max_size=45)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 3. ГАДАЛКА
# ═══════════════════════════════════════════
def _fortune(data: dict) -> bytes:
    img = _gradient((5, 0, 20), (30, 10, 60))
    d = ImageDraw.Draw(img)
    gold = (255, 215, 0)
    purple = (186, 85, 211)

    _center(d, "FORTUNE", _font(80, True), 100, gold)
    _center(d, "ТВОЁ ПРЕДСКАЗАНИЕ", _font(32), 220, purple)

    _center_fit(d, f"«{data.get('prediction', '—')}»", y_start=380, max_y=650, fill=WHITE, max_size=70, min_size=40)

    _center(d, "УДАЧА", _font(32), 700, gold)
    y = _draw_big_pct(d, int(data.get("luck", 0)), 760)

    _center(d, "ЛЮБОВЬ", _font(40, True), 1100, purple)
    _center_fit(d, data.get("love", ""), y_start=1170, max_y=1320, fill=WHITE, max_size=45)

    _center(d, "ДЕНЬГИ", _font(40, True), 1340, purple)
    _center_fit(d, data.get("money", ""), y_start=1410, max_y=1560, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(40, True), 1580, gold)
    _center_fit(d, data.get("advice", ""), y_start=1650, max_y=HEIGHT - 120, fill=WHITE, max_size=45)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 4. МЕМ (fallback без фото)
# ═══════════════════════════════════════════
def _meme(data: dict) -> bytes:
    img = _gradient((0, 0, 0), (20, 20, 20))
    d = ImageDraw.Draw(img)
    top = str(data.get("top", "")).upper()
    bottom = str(data.get("bottom", "")).upper()
    max_text_width = WIDTH - 60

    font_top = _fit_font(top, max_text_width, max_size=110, bold=True)
    y = 150
    for line in _wrap_lines(d, top, font_top, max_text_width):
        bbox = d.textbbox((0, 0), line, font=font_top)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (WIDTH - tw) / 2
        for dx in (-4, 0, 4):
            for dy in (-4, 0, 4):
                d.text((x + dx, y + dy), line, font=font_top, fill=(0, 0, 0))
        d.text((x, y), line, font=font_top, fill=WHITE)
        y += th + 15

    cx, cy = WIDTH // 2, HEIGHT // 2
    r = 250
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 220, 0))
    d.ellipse([cx - 120, cy - 100, cx - 40, cy - 20], fill=(0, 0, 0))
    d.ellipse([cx + 40, cy - 100, cx + 120, cy - 20], fill=(0, 0, 0))
    d.arc([cx - 160, cy - 40, cx + 160, cy + 180], start=20, end=160, fill=(0, 0, 0), width=25)

    font_bot = _fit_font(bottom, max_text_width, max_size=110, bold=True)
    lines_bot = _wrap_lines(d, bottom, font_bot, max_text_width)
    total_h = sum(d.textbbox((0, 0), ln, font=font_bot)[3] + 15 for ln in lines_bot)
    y_bot = HEIGHT - total_h - 40
    for line in lines_bot:
        bbox = d.textbbox((0, 0), line, font=font_bot)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (WIDTH - tw) / 2
        for dx in (-4, 0, 4):
            for dy in (-4, 0, 4):
                d.text((x + dx, y_bot + dy), line, font=font_bot, fill=(0, 0, 0))
        d.text((x, y_bot), line, font=font_bot, fill=WHITE)
        y_bot += th + 15

    _center(d, f"#{data.get('hashtag', 'мем')} • {data.get('genre', '')}",
            _font(36), 1650, (180, 180, 180))
    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 5. ОТНОШЕНИЯ
# ═══════════════════════════════════════════
def _relationship(data: dict) -> bytes:
    img = _gradient((15, 0, 10), (50, 0, 30))
    d = ImageDraw.Draw(img)
    pink = (255, 50, 130)
    heart = (255, 100, 150)
    gold = (255, 215, 0)

    _center(d, "RELATIONSHIP CHECK", _font(60, True), 100, pink)
    _center(d, "АНАЛИЗ ПАРЫ", _font(32), 200, heart)

    compat = int(data.get("compat", 0))
    pct_color = (46, 204, 113) if compat >= 70 else ((241, 196, 15) if compat >= 40 else (231, 76, 60))
    pct = f"{compat}%"
    f = _font(200, bold=True)
    bbox = d.textbbox((0, 0), pct, font=f)
    pw, ph = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((WIDTH - pw) / 2, 350), pct, font=f, fill=pct_color)
    _center(d, "СОВМЕСТИМОСТЬ", _font(32), 350 + ph + 10, WHITE)

    _center(d, "ТИП ОТНОШЕНИЙ", _font(32), 900, pink)
    _center_fit(d, f"«{data.get('type', '—')}»", y_start=960, max_y=1100, fill=WHITE, max_size=55)

    _center(d, "КТО ГЛАВНЫЙ", _font(32), 1120, pink)
    _center(d, str(data.get("leader", "—")).capitalize(), _font(50, True), 1180, heart)

    _center(d, "ПРОГНОЗ", _font(32), 1300, pink)
    _center_fit(d, data.get("forecast", ""), y_start=1360, max_y=1500, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(32), 1520, gold)
    _center_fit(d, data.get("advice", ""), y_start=1580, max_y=1700, fill=WHITE, max_size=45)

    _center_fit(d, data.get("verdict", ""), y_start=1710, max_y=HEIGHT - 100,
                fill=(200, 200, 200), max_size=36)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 6. КРИНЖ
# ═══════════════════════════════════════════
def _cringe(data: dict) -> bytes:
    img = _gradient((10, 0, 30), (30, 5, 60))
    d = ImageDraw.Draw(img)
    neon = (255, 0, 200)
    green = (0, 255, 100)

    _center(d, "CRINGE CHECK", _font(70, True), 100, neon)
    _center(d, "УРОВЕНЬ КРИНЖА", _font(32), 200, green)

    cringe = int(data.get("cringe", 0))
    pct_color = (46, 204, 113) if cringe < 30 else ((241, 196, 15) if cringe < 70 else (231, 76, 60))
    pct = f"{cringe}%"
    f = _font(200, bold=True)
    bbox = d.textbbox((0, 0), pct, font=f)
    pw, ph = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((WIDTH - pw) / 2, 350), pct, font=f, fill=pct_color)

    _center(d, "ПРИЧИНА", _font(32), 800, neon)
    _center_fit(d, f"«{data.get('reason', '—')}»", y_start=860, max_y=1050, fill=WHITE, max_size=50)

    _center(d, "ВЕРДИКТ", _font(32), 1100, neon)
    _center_fit(d, data.get("verdict", ""), y_start=1160, max_y=1450, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(32), 1500, green)
    _center_fit(d, data.get("advice", ""), y_start=1560, max_y=HEIGHT - 120, fill=WHITE, max_size=45)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 7. ФЛЕКС
# ═══════════════════════════════════════════
def _flex(data: dict) -> bytes:
    img = _gradient((20, 0, 0), (60, 20, 0))
    d = ImageDraw.Draw(img)
    gold = (255, 215, 0)
    red = (255, 80, 80)

    _center(d, "FLEX CHECK", _font(70, True), 100, gold)
    _center(d, "ОЦЕНКА ФЛЕКСА", _font(32), 200, red)

    flex = int(data.get("flex", 0))
    pct = f"{flex}%"
    f = _font(200, bold=True)
    bbox = d.textbbox((0, 0), pct, font=f)
    pw, ph = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pct_color = (46, 204, 113) if flex < 30 else ((241, 196, 15) if flex < 70 else (231, 76, 60))
    d.text(((WIDTH - pw) / 2, 350), pct, font=f, fill=pct_color)

    _center(d, "ТИП", _font(32), 800, gold)
    _center_fit(d, f"«{data.get('type', '—')}»", y_start=860, max_y=1050, fill=WHITE, max_size=55)

    _center(d, "ВЕРДИКТ", _font(32), 1100, gold)
    _center_fit(d, data.get("verdict", ""), y_start=1160, max_y=1450, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(32), 1500, red)
    _center_fit(d, data.get("advice", ""), y_start=1560, max_y=HEIGHT - 120, fill=WHITE, max_size=45)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 8. ПСИХОПРОФИЛЬ
# ═══════════════════════════════════════════
def _psycho(data: dict) -> bytes:
    img = _gradient((0, 10, 30), (0, 30, 80))
    d = ImageDraw.Draw(img)
    blue = (0, 200, 255)
    purple = (180, 100, 255)

    _center(d, "PSYCHO PROFILE", _font(70, True), 100, blue)
    _center(d, "ТВОЙ ПСИХОТИП", _font(32), 200, purple)

    _center(d, "ТИП", _font(32), 400, blue)
    _center_fit(d, f"«{data.get('type', '—')}»", y_start=470, max_y=650, fill=WHITE, max_size=70, min_size=40)

    _center(d, "ХАРАКТЕР", _font(32), 800, blue)
    _center_fit(d, data.get("character", ""), y_start=860, max_y=1150, fill=WHITE, max_size=45)

    _center(d, "ТАЙНА", _font(32), 1200, purple)
    _center_fit(d, data.get("secret", ""), y_start=1260, max_y=1470, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(32), 1520, blue)
    _center_fit(d, data.get("advice", ""), y_start=1580, max_y=HEIGHT - 120, fill=WHITE, max_size=45)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 9. АУРА
# ═══════════════════════════════════════════
def _aura(data: dict) -> bytes:
    img = _gradient((20, 0, 40), (50, 0, 80))
    d = ImageDraw.Draw(img)
    neon = (255, 100, 255)

    _center(d, "AURA CHECK", _font(70, True), 100, neon)
    _center(d, "ЦВЕТ ТВОЕЙ АУРЫ", _font(32), 200, (200, 200, 255))

    _center_fit(d, str(data.get("color", "—")).upper(), y_start=400, max_y=650,
                fill=neon, max_size=90, min_size=50)

    _center_fit(d, f"«{data.get('meaning', '—')}»", y_start=700, max_y=900,
                fill=(255, 255, 100), max_size=50)

    _center(d, "ОПИСАНИЕ", _font(32), 950, (200, 200, 255))
    _center_fit(d, data.get("desc", ""), y_start=1010, max_y=1350, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(32), 1400, neon)
    _center_fit(d, data.get("advice", ""), y_start=1460, max_y=HEIGHT - 120, fill=WHITE, max_size=45)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 10. КТО ГЛАВНЫЙ
# ═══════════════════════════════════════════
def _leader(data: dict) -> bytes:
    img = _gradient((10, 10, 10), (50, 50, 50))
    d = ImageDraw.Draw(img)
    gold = (255, 215, 0)

    _center(d, "POWER BALANCE", _font(70, True), 100, gold)
    _center(d, "КТО ГЛАВНЫЙ", _font(32), 200, WHITE)

    _center(d, "ГЛАВНЫЙ", _font(32), 400, gold)
    _center(d, str(data.get("leader", "—")).capitalize(), _font(100, True), 470, WHITE)

    balance = int(data.get("balance", 50))
    _center(d, "БАЛАНС СИЛ", _font(32), 700, gold)
    _center(d, f"ОН {100 - balance}%  ← →  ОНА {balance}%", _font(50, True), 770, WHITE)

    _center(d, "ВЕРДИКТ", _font(32), 1000, gold)
    _center_fit(d, data.get("verdict", ""), y_start=1060, max_y=1400, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(32), 1450, gold)
    _center_fit(d, data.get("advice", ""), y_start=1510, max_y=HEIGHT - 120, fill=WHITE, max_size=45)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 11. ВОЗРАСТ
# ═══════════════════════════════════════════
def _age(data: dict) -> bytes:
    img = _gradient((0, 10, 20), (0, 30, 60))
    d = ImageDraw.Draw(img)
    cyan = (0, 255, 255)

    _center(d, "AGE SCAN", _font(70, True), 100, cyan)
    _center(d, "ВОЗРАСТ ПО ЛИЦУ", _font(32), 200, WHITE)

    _center(d, "ПО ЛИЦУ", _font(32), 400, cyan)
    _center(d, f"{data.get('age', 0)} лет", _font(150, True), 460, WHITE)

    _center(d, "ПО ВАЙБУ", _font(32), 800, cyan)
    _center(d, f"{data.get('mental', 0)} лет", _font(150, True), 860, WHITE)

    _center(d, "ПРИЧИНА", _font(32), 1200, cyan)
    _center_fit(d, data.get("reason", ""), y_start=1260, max_y=1450, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(32), 1500, cyan)
    _center_fit(d, data.get("advice", ""), y_start=1560, max_y=HEIGHT - 120, fill=WHITE, max_size=45)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 12. ТИП КРАША
# ═══════════════════════════════════════════
def _crush(data: dict) -> bytes:
    img = _gradient((30, 0, 20), (70, 0, 40))
    d = ImageDraw.Draw(img)
    pink = (255, 100, 180)
    gold = (255, 200, 50)

    _center(d, "CRUSH CHECK", _font(70, True), 100, pink)
    _center(d, "ТИП ТВОЕГО КРАША", _font(32), 200, gold)

    _center(d, "ТИП", _font(32), 400, pink)
    _center_fit(d, f"«{data.get('type', '—')}»", y_start=470, max_y=650, fill=WHITE, max_size=60)

    _center(d, "ИЩЕТ", _font(32), 700, pink)
    _center_fit(d, data.get("seeks", ""), y_start=760, max_y=1000, fill=WHITE, max_size=45)

    _center(d, "КРАСНЫЕ ФЛАГИ", _font(32), 1020, (255, 100, 100))
    _center_fit(d, data.get("flags", ""), y_start=1080, max_y=1380, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(32), 1400, gold)
    _center_fit(d, data.get("advice", ""), y_start=1460, max_y=HEIGHT - 120, fill=WHITE, max_size=45)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 13. ОДИНОЧЕСТВО
# ═══════════════════════════════════════════
def _lonely(data: dict) -> bytes:
    img = _gradient((0, 0, 0), (20, 20, 40))
    d = ImageDraw.Draw(img)
    gray = (150, 150, 200)
    blue = (100, 150, 255)

    _center(d, "LONELINESS CHECK", _font(60, True), 100, gray)
    _center(d, "УРОВЕНЬ ОДИНОЧЕСТВА", _font(32), 200, blue)

    lonely = int(data.get("lonely", 0))
    pct = f"{lonely}%"
    f = _font(200, bold=True)
    bbox = d.textbbox((0, 0), pct, font=f)
    pw, ph = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pct_color = (46, 204, 113) if lonely < 30 else ((241, 196, 15) if lonely < 70 else (231, 76, 60))
    d.text(((WIDTH - pw) / 2, 350), pct, font=f, fill=pct_color)

    _center(d, "СТАТУС", _font(32), 800, blue)
    _center_fit(d, f"«{data.get('status', '—')}»", y_start=860, max_y=1050, fill=WHITE, max_size=55)

    _center(d, "ОПИСАНИЕ", _font(32), 1100, blue)
    _center_fit(d, data.get("desc", ""), y_start=1160, max_y=1450, fill=WHITE, max_size=45)

    _center(d, "СОВЕТ", _font(32), 1500, blue)
    _center_fit(d, data.get("advice", ""), y_start=1560, max_y=HEIGHT - 120, fill=WHITE, max_size=45)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# МЕМ С ФОТО
# ═══════════════════════════════════════════
def create_meme_with_photo(image_bytes: bytes, data: dict) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return _meme(data)

    src_w, src_h = img.size
    target_ratio = WIDTH / HEIGHT
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        new_h = HEIGHT
        new_w = int(src_w * (HEIGHT / src_h))
        img = img.resize((new_w, HEIGHT), Image.BILINEAR)
        left = (new_w - WIDTH) // 2
        img = img.crop((left, 0, left + WIDTH, HEIGHT))
    else:
        new_w = WIDTH
        new_h = int(src_h * (WIDTH / src_w))
        img = img.resize((WIDTH, new_h), Image.BILINEAR)
        top = (new_h - HEIGHT) // 2
        img = img.crop((0, top, WIDTH, top + HEIGHT))

    d = ImageDraw.Draw(img)
    top_text = str(data.get("top", "")).upper()
    bottom_text = str(data.get("bottom", "")).upper()
    max_text_width = WIDTH - 60

    font_top = _fit_font(top_text, max_text_width, max_size=110, bold=True)
    y = 40
    for line in _wrap_lines(d, top_text, font_top, max_text_width):
        bbox = d.textbbox((0, 0), line, font=font_top)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (WIDTH - tw) / 2
        for dx in (-5, -3, 0, 3, 5):
            for dy in (-5, -3, 0, 3, 5):
                d.text((x + dx, y + dy), line, font=font_top, fill=(0, 0, 0))
        d.text((x, y), line, font=font_top, fill=WHITE)
        y += th + 15

    font_bot = _fit_font(bottom_text, max_text_width, max_size=110, bold=True)
    lines_bot = _wrap_lines(d, bottom_text, font_bot, max_text_width)
    total_h = sum(d.textbbox((0, 0), ln, font=font_bot)[3] + 15 for ln in lines_bot)
    y_bot = HEIGHT - total_h - 40
    for line in lines_bot:
        bbox = d.textbbox((0, 0), line, font=font_bot)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (WIDTH - tw) / 2
        for dx in (-5, -3, 0, 3, 5):
            for dy in (-5, -3, 0, 3, 5):
                d.text((x + dx, y_bot + dy), line, font=font_bot, fill=(0, 0, 0))
        d.text((x, y_bot), line, font=font_bot, fill=WHITE)
        y_bot += th + 15

    _center(d, f"@{BOT_USERNAME}", _font(28), HEIGHT - 35, (200, 200, 200))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=False)
    return buf.getvalue()


# ═══════════════════════════════════════════
# РОУТЕР
# ═══════════════════════════════════════════
def create_card(data: dict, mode: str) -> bytes:
    return {
        "toxic": _toxic,
        "kent": _kent,
        "fortune": _fortune,
        "meme": _meme,
        "relationship": _relationship,
        "cringe": _cringe,
        "flex": _flex,
        "psycho": _psycho,
        "aura": _aura,
        "leader": _leader,
        "age": _age,
        "crush": _crush,
        "lonely": _lonely,
    }[mode](data)
