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
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _signature(draw):
    _center(draw, f"@{BOT_USERNAME}", _font(32), HEIGHT - 90, (160, 160, 160))


# ─────────── ТОКСИК ───────────
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


# ─────────── КЕНТ ───────────
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


# ─────────── ГАДАЛКА ───────────
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


# ─────────── МЕМ (Fallback без фото) ───────────
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

    # Жёлтый смайл в центре
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


# ─────────── МЕМ С ФОТО (Новый) ───────────
def create_meme_with_photo(image_bytes: bytes, data: dict) -> bytes:
    """Создает мем: фото юзера + текст сверху и снизу."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return _meme(data)

    # Масштабируем под 1080x1920 (cover)
    src_w, src_h = img.size
    target_ratio = WIDTH / HEIGHT
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        new_h = HEIGHT
        new_w = int(src_w * (HEIGHT / src_h))
        img = img.resize((new_w, HEIGHT), Image.LANCZOS)
        left = (new_w - WIDTH) // 2
        img = img.crop((left, 0, left + WIDTH, HEIGHT))
    else:
        new_w = WIDTH
        new_h = int(src_h * (WIDTH / src_w))
        img = img.resize((WIDTH, new_h), Image.LANCZOS)
        top = (new_h - HEIGHT) // 2
        img = img.crop((0, top, WIDTH, top + HEIGHT))

    d = ImageDraw.Draw(img)
    top = str(data.get("top", "")).upper()
    bottom = str(data.get("bottom", "")).upper()
    max_text_width = WIDTH - 60

    # Верхний текст
    font_top = _fit_font(top, max_text_width, max_size=110, bold=True)
    lines = []
    words = top.split()
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

    # Нижний текст
    font_bot = _fit_font(bottom, max_text_width, max_size=110, bold=True)
    lines_bot = []
    words_bot = bottom.split()
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

    # Водяной знак
    _center(d, f"@{BOT_USERNAME}", _font(28), HEIGHT - 35, (200, 200, 200))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90, optimize=True)
    return buf.getvalue()


def create_card(data: dict, mode: str) -> bytes:
    return {
        "toxic": _toxic,
        "kent": _kent,
        "fortune": _fortune,
        "meme": _meme,
    }[mode](data)
