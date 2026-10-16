# Генерация карточки 1080x1920 через Pillow
import io
import os
from typing import Dict
from PIL import Image, ImageDraw, ImageFont
from config import BOT_USERNAME

WIDTH, HEIGHT = 1080, 1920
BG_TOP = (10, 10, 10)
BG_BOTTOM = (26, 0, 51)
NEON = (0, 255, 204)
WHITE = (255, 255, 255)

# Ищем шрифты во всех возможных местах
_HERE = os.path.dirname(os.path.abspath(__file__))

_SEARCH_DIRS = [
    os.path.join(_HERE, "fonts"),
    os.path.join(_HERE, "fonts_src"),
    _HERE,
    "/app/fonts",
    "/app/fonts_src",
    "/app",
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
]

# Возможные имена для обычного и жирного шрифта
_REGULAR_NAMES = [
    "DejaVuSans.ttf",
    "Onest-Regular.ttf",
    "Manrope-Regular.ttf",
    "arial.ttf",
]
_BOLD_NAMES = [
    "DejaVuSans-Bold.ttf",
    "Onest-Bold.ttf",
    "Unbounded-Bold.ttf",
    "BebasNeue-Regular.ttf",
    "arialbd.ttf",
]

# Отладка при первом импорте
print(f"[FONT-INIT] _HERE={_HERE}")
for d in _SEARCH_DIRS:
    if os.path.exists(d):
        try:
            print(f"[FONT-INIT] {d} → {os.listdir(d)}")
        except Exception:
            pass


def _find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Ищет TTF с кириллицей. Перебирает все папки и все возможные имена."""
    names = _BOLD_NAMES if bold else _REGULAR_NAMES

    # 1. Сначала ищем во всех папках с ожидаемыми именами
    for dir_path in _SEARCH_DIRS:
        if not os.path.isdir(dir_path):
            continue
        for name in names:
            path = os.path.join(dir_path, name)
            if os.path.exists(path):
                try:
                    font = ImageFont.truetype(path, size=size)
                    print(f"[FONT] OK ({size}pt, bold={bold}): {path}")
                    return font
                except (OSError, IOError) as e:
                    print(f"[FONT] Fail {path}: {e}")

    # 2. Fallback: ищем ЛЮБОЙ .ttf в этих папках (первый попавшийся)
    for dir_path in _SEARCH_DIRS:
        if not os.path.isdir(dir_path):
            continue
        for f in os.listdir(dir_path):
            if f.lower().endswith(".ttf"):
                path = os.path.join(dir_path, f)
                try:
                    font = ImageFont.truetype(path, size=size)
                    print(f"[FONT] FALLBACK ({size}pt): {path}")
                    return font
                except (OSError, IOError):
                    continue

    print(f"[FONT] WARNING: No Cyrillic font found for size={size}, bold={bold}!")
    return ImageFont.load_default()


def _gradient_background() -> Image.Image:
    """Создаёт вертикальный градиент."""
    base = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    top_r, top_g, top_b = BG_TOP
    bot_r, bot_g, bot_b = BG_BOTTOM
    draw = ImageDraw.Draw(base)
    for y in range(HEIGHT):
        t = y / HEIGHT
        r = int(top_r + (bot_r - top_r) * t)
        g = int(top_g + (bot_g - top_g) * t)
        b = int(top_b + (bot_b - top_b) * t)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return base


def _color_for_flags(flags: int) -> tuple:
    if flags < 30:
        return (46, 204, 113)
    if flags <= 70:
        return (241, 196, 15)
    return (231, 76, 60)


def _draw_centered(draw: ImageDraw.ImageDraw, text: str, font, y: int, fill) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)
    return y + h + 20


def _wrap(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def create_card(data: Dict[str, str | int]) -> bytes:
    """Генерирует карточку 1080x1920 с вердиктом."""
    img = _gradient_background()
    draw = ImageDraw.Draw(img)

    font_logo = _find_font(70, bold=True)
    font_percent = _find_font(200, bold=True)
    font_label = _find_font(60, bold=True)
    font_text = _find_font(50, bold=False)
    font_small = _find_font(32, bold=False)

    _draw_centered(draw, "TOXIC CHECK", font_logo, 100, NEON)

    flags = int(data.get("flags", 0))
    flag_color = _color_for_flags(flags)
    percent_text = f"{flags}%"

    bbox = draw.textbbox((0, 0), percent_text, font=font_percent)
    ph = bbox[3] - bbox[1]
    pw = bbox[2] - bbox[0]
    draw.text(((WIDTH - pw) / 2, 480), percent_text, font=font_percent, fill=flag_color)

    _draw_centered(draw, "КРАСНЫХ ФЛАГОВ", font_small, 480 + ph + 20, WHITE)

    y = 900
    _draw_centered(draw, f"Токсик: {data.get('toxic', '—')}", font_label, y, WHITE)
    y += 100
    _draw_centered(draw, f"Тип: {data.get('type', '—')}", font_label, y, WHITE)

    y = 1200
    _draw_centered(draw, "СОВЕТ", font_small, y, NEON)
    y += 60
    advice = str(data.get("advice", ""))
    for line in _wrap(advice, font_text, WIDTH - 120, draw):
        _draw_centered(draw, line, font_text, y, WHITE)
        y += 70

    y = 1500
    _draw_centered(draw, "ВЫВОД", font_small, y, NEON)
    y += 60
    verdict = str(data.get("verdict", ""))
    for line in _wrap(verdict, font_text, WIDTH - 120, draw)[:4]:
        _draw_centered(draw, line, font_text, y, WHITE)
        y += 70

    _draw_centered(draw, f"@{BOT_USERNAME}", font_small, HEIGHT - 90, (150, 150, 150))

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
