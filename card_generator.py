# Генерация карточек: 13 режимов + JPEG (быстрое сохранение)
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
            try: return ImageFont.truetype(p, size=size)
            except (OSError, IOError): continue
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
    """Быстрый градиент через numpy-подобный подход (по полоскам)."""
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


def _center(draw, text, font, y, fill, max_w=None):
    if max_w:
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = (cur + " " + w).strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_w:
                cur = test
            else:
                if cur: lines.append(cur)
                cur = w
        if cur: lines.append(cur)
        for ln in lines:
            bbox = draw.textbbox((0, 0), ln, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(((WIDTH - w) / 2, y), ln, font=font, fill=fill)
            y += h + 10
        return y
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)
    return y + h + 20


def _pct_color(v: int):
    if v < 30: return (46, 204, 113)
    if v <= 70: return (241, 196, 15)
    return (231, 76, 60)


def _draw_big_pct(draw, value: int, y: int):
    pct = f"{value}%"
    f = _font(200, bold=True)
    bbox = draw.textbbox((0, 0), pct, font=f)
    pw, ph = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((WIDTH - pw) / 2, y), pct, font=f, fill=_pct_color(value))
    return y + ph + 20


def _save(img) -> bytes:
    """JPEG для быстрой загрузки (300 KB вместо 1.5 MB PNG)."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=False)
    return buf.getvalue()


def _signature(draw):
    _center(draw, f"@{BOT_USERNAME}", _font(32), HEIGHT - 90, (160, 160, 160))


# ═══════════════════════════════════════════
# 1. ТОКСИК
# ═══════════════════════════════════════════
def _toxic(data: dict) -> bytes:
    img = _gradient((10, 10, 10), (26, 0, 51))
    d = ImageDraw.Draw(img)
    neon = (0, 255, 204)
    _center(d, "TOXIC CHECK", _font(70, True), 100, neon)
    y = _draw_big_pct(d, int(data.get("flags", 0)), 480)
    _center(d, "КРАСНЫХ ФЛАГОВ", _font(32), y, WHITE)

    y = 900
    _center(d, f"Токсик: {data.get('toxic', '—')}", _font(60, True), y, WHITE)
    y += 100
    _center(d, f"Тип: {data.get('type', '—')}", _font(60, True), y, WHITE)

    y = 1200
    _center(d, "СОВЕТ", _font(32), y, neon)
    _center(d, str(data.get("advice", "")), _font(50), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1550
    _center(d, "ВЫВОД", _font(32), y, neon)
    _center(d, str(data.get("verdict", "")), _font(50), y + 60, WHITE, max_w=WIDTH - 120)

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
    _center(d, f"«{data.get('verdict', '—')}»", _font(50, True), y + 60, WHITE, max_w=WIDTH - 100)

    y = 1100
    _center(d, "ХАРАКТЕР", _font(32), y, acc)
    _center(d, str(data.get("character", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 100)

    y = 1300
    _center(d, "ПРОГНОЗ", _font(32), y, acc)
    _center(d, str(data.get("prediction", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 100)

    y = 1550
    _center(d, "СОВЕТ", _font(32), y, acc)
    _center(d, str(data.get("advice", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 100)

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

    y = 380
    _center(d, f"«{data.get('prediction', '—')}»", _font(70, True), y, WHITE, max_w=WIDTH - 100)

    y = 700
    _center(d, "УДАЧА", _font(32), y, gold)
    y = _draw_big_pct(d, int(data.get("luck", 0)), y + 60)

    y = 1100
    _center(d, "ЛЮБОВЬ", _font(40, True), y, purple)
    _center(d, str(data.get("love", "")), _font(45), y + 70, WHITE, max_w=WIDTH - 120)

    y = 1350
    _center(d, "ДЕНЬГИ", _font(40, True), y, purple)
    _center(d, str(data.get("money", "")), _font(45), y + 70, WHITE, max_w=WIDTH - 120)

    y = 1600
    _center(d, "СОВЕТ", _font(40, True), y, gold)
    _center(d, str(data.get("advice", "")), _font(45), y + 70, WHITE, max_w=WIDTH - 120)

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
    bbox = d.textbbox((0, 0), top, font=font_top)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (WIDTH - tw) / 2
    for dx in (-4, 0, 4):
        for dy in (-4, 0, 4):
            d.text((x + dx, y + dy), top, font=font_top, fill=(0, 0, 0))
    d.text((x, y), top, font=font_top, fill=WHITE)

    cx, cy = WIDTH // 2, HEIGHT // 2
    r = 250
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 220, 0))
    d.ellipse([cx - 120, cy - 100, cx - 40, cy - 20], fill=(0, 0, 0))
    d.ellipse([cx + 40, cy - 100, cx + 120, cy - 20], fill=(0, 0, 0))
    d.arc([cx - 160, cy - 40, cx + 160, cy + 180], start=20, end=160, fill=(0, 0, 0), width=25)

    font_bot = _fit_font(bottom, max_text_width, max_size=110, bold=True)
    bbox = d.textbbox((0, 0), bottom, font=font_bot)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (WIDTH - tw) / 2
    y_bot = HEIGHT - 350
    for dx in (-4, 0, 4):
        for dy in (-4, 0, 4):
            d.text((x + dx, y_bot + dy), bottom, font=font_bot, fill=(0, 0, 0))
    d.text((x, y_bot), bottom, font=font_bot, fill=WHITE)

    _center(d, f"#{data.get('hashtag', 'мем')} • {data.get('genre', '')}", _font(36), 1650, (180, 180, 180))
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

    y = 900
    _center(d, "ТИП ОТНОШЕНИЙ", _font(32), y, pink)
    _center(d, f"«{data.get('type', '—')}»", _font(55, True), y + 55, WHITE, max_w=WIDTH - 100)

    y = 1100
    _center(d, "КТО ГЛАВНЫЙ", _font(32), y, pink)
    _center(d, str(data.get("leader", "—")).capitalize(), _font(50, True), y + 55, heart)

    y = 1300
    _center(d, "ПРОГНОЗ", _font(32), y, pink)
    _center(d, str(data.get("forecast", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1500
    _center(d, "СОВЕТ", _font(32), y, gold)
    _center(d, str(data.get("advice", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1680
    _center(d, str(data.get("verdict", "")), _font(36), y, (200, 200, 200), max_w=WIDTH - 120)

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

    y = 800
    _center(d, "ПРИЧИНА", _font(32), y, neon)
    _center(d, f"«{data.get('reason', '—')}»", _font(50, True), y + 60, WHITE, max_w=WIDTH - 100)

    y = 1100
    _center(d, "ВЕРДИКТ", _font(32), y, neon)
    _center(d, str(data.get("verdict", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1500
    _center(d, "СОВЕТ", _font(32), y, green)
    _center(d, str(data.get("advice", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

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

    y = 800
    _center(d, "ТИП", _font(32), y, gold)
    _center(d, f"«{data.get('type', '—')}»", _font(55, True), y + 55, WHITE, max_w=WIDTH - 100)

    y = 1100
    _center(d, "ВЕРДИКТ", _font(32), y, gold)
    _center(d, str(data.get("verdict", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1500
    _center(d, "СОВЕТ", _font(32), y, red)
    _center(d, str(data.get("advice", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

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

    y = 400
    _center(d, "ТИП", _font(32), y, blue)
    _center(d, f"«{data.get('type', '—')}»", _font(70, True), y + 60, WHITE, max_w=WIDTH - 100)

    y = 800
    _center(d, "ХАРАКТЕР", _font(32), y, blue)
    _center(d, str(data.get("character", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1200
    _center(d, "ТАЙНА", _font(32), y, purple)
    _center(d, str(data.get("secret", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1550
    _center(d, "СОВЕТ", _font(32), y, blue)
    _center(d, str(data.get("advice", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 9. АУРА
# ═══════════════════════════════════════════
def _aura(data: dict) -> bytes:
    img = _gradient((20, 0, 40), (50, 0, 80))
    d = ImageDraw.Draw(img)
    rainbow = [(255, 0, 0), (255, 165, 0), (255, 255, 0), (0, 255, 0), (0, 150, 255), (150, 0, 255)]

    _center(d, "AURA CHECK", _font(70, True), 100, (255, 100, 255))
    _center(d, "ЦВЕТ ТВОЕЙ АУРЫ", _font(32), 200, (200, 200, 255))

    y = 400
    color_text = str(data.get("color", "—"))
    _center(d, color_text.upper(), _font(90, True), y, (255, 100, 255), max_w=WIDTH - 100)

    y = 600
    _center(d, f"«{data.get('meaning', '—')}»", _font(50, True), y, (255, 255, 100))

    y = 900
    _center(d, "ОПИСАНИЕ", _font(32), y, (200, 200, 255))
    _center(d, str(data.get("desc", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1400
    _center(d, "СОВЕТ", _font(32), y, (255, 100, 255))
    _center(d, str(data.get("advice", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# 10. ГЛАВНЫЙ
# ═══════════════════════════════════════════
def _leader(data: dict) -> bytes:
    img = _gradient((10, 10, 10), (50, 50, 50))
    d = ImageDraw.Draw(img)
    gold = (255, 215, 0)

    _center(d, "POWER BALANCE", _font(70, True), 100, gold)
    _center(d, "КТО ГЛАВНЫЙ", _font(32), 200, WHITE)

    y = 400
    _center(d, "ГЛАВНЫЙ", _font(32), y, gold)
    _center(d, str(data.get("leader", "—")).capitalize(), _font(100, True), y + 60, WHITE)

    y = 700
    balance = int(data.get("balance", 50))
    _center(d, "БАЛАНС СИЛ", _font(32), y, gold)
    y += 60
    _center(d, f"ОН {100 - balance}%  ← →  ОНА {balance}%", _font(50, True), y, WHITE)

    y = 1000
    _center(d, "ВЕРДИКТ", _font(32), y, gold)
    _center(d, str(data.get("verdict", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1450
    _center(d, "СОВЕТ", _font(32), y, gold)
    _center(d, str(data.get("advice", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

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

    y = 400
    _center(d, "ПО ЛИЦУ", _font(32), y, cyan)
    _center(d, f"{data.get('age', 0)} лет", _font(150, True), y + 50, WHITE)

    y = 800
    _center(d, "ПО ВАЙБУ", _font(32), y, cyan)
    _center(d, f"{data.get('mental', 0)} лет", _font(150, True), y + 50, WHITE)

    y = 1200
    _center(d, "ПРИЧИНА", _font(32), y, cyan)
    _center(d, str(data.get("reason", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1550
    _center(d, "СОВЕТ", _font(32), y, cyan)
    _center(d, str(data.get("advice", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

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

    y = 400
    _center(d, "ТИП", _font(32), y, pink)
    _center(d, f"«{data.get('type', '—')}»", _font(60, True), y + 60, WHITE, max_w=WIDTH - 100)

    y = 700
    _center(d, "ИЩЕТ", _font(32), y, pink)
    _center(d, str(data.get("seeks", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1000
    _center(d, "КРАСНЫЕ ФЛАГИ", _font(32), y, (255, 100, 100))
    _center(d, str(data.get("flags", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1400
    _center(d, "СОВЕТ", _font(32), y, gold)
    _center(d, str(data.get("advice", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

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

    y = 800
    _center(d, "СТАТУС", _font(32), y, blue)
    _center(d, f"«{data.get('status', '—')}»", _font(55, True), y + 55, WHITE, max_w=WIDTH - 100)

    y = 1100
    _center(d, "ОПИСАНИЕ", _font(32), y, blue)
    _center(d, str(data.get("desc", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    y = 1500
    _center(d, "СОВЕТ", _font(32), y, blue)
    _center(d, str(data.get("advice", "")), _font(45), y + 60, WHITE, max_w=WIDTH - 120)

    _signature(d)
    return _save(img)


# ═══════════════════════════════════════════
# МЕМ С ФОТО (классический мем)
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
    lines = []
    words = top_text.split()
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=font_top)[2] <= max_text_width:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)

    y = 40
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font_top)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (WIDTH - tw) / 2
        for dx in (-5, -3, 0, 3, 5):
            for dy in (-5, -3, 0, 3, 5):
                d.text((x + dx, y + dy), line, font=font_top, fill=(0, 0, 0))
        d.text((x, y), line, font=font_top, fill=WHITE)
        y += th + 15

    font_bot = _fit_font(bottom_text, max_text_width, max_size=110, bold=True)
    lines_bot = []
    words_bot = bottom_text.split()
    cur = ""
    for w in words_bot:
        test = (cur + " " + w).strip()
        if d.textbbox((0, 0), test, font=font_bot)[2] <= max_text_width:
            cur = test
        else:
            if cur: lines_bot.append(cur)
            cur = w
    if cur: lines_bot.append(cur)

    total_h = sum(d.textbbox((0, 0), l, font=font_bot)[3] + 15 for l in lines_bot)
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
