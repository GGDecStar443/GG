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
GREY = (150, 150, 150)

_HERE = os.path.dirname(os.path.abspath(__file__))
FONT_REGULAR = os.path.join(_HERE, "fonts", "DejaVuSans.ttf")
FONT_BOLD = os.path.join(_HERE, "fonts", "DejaVuSans-Bold.ttf")

print(f"[FONT] regular = {FONT_REGULAR} → exists: {os.path.exists(FONT_REGULAR)}")
print(f"[FONT] bold    = {FONT_BOLD} → exists: {os.path.exists(FONT_BOLD)}")


def _find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Грузит шрифт с фиксированного пути."""
    primary = FONT_BOLD if bold else FONT_REGULAR
    candidates = [
        primary,
        os.path.join(_HERE, "fonts", "DejaVuSans-Bold.ttf"),
        os.path.join(_HERE, "fonts", "DejaVuSans.ttf"),
        "/app/fonts/DejaVuSans-Bold.ttf",
        "/app/fonts/DejaVuSans.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _gradient_background() -> Image.Image:
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


def _measure(draw, text, font):
    """Возвращает (width, height) текста."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_centered(draw, text, font, y, fill) -> int:
    """Рисует по центру. Возвращает Y следующей строки."""
    w, h = _measure(draw, text, font)
    draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)
    return y + h + 15


def _wrap_text(draw, text, font, max_width) -> list[str]:
    """Разбивает текст на строки по ширине (по словам)."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        test = (current + " " + word).strip()
        w, _ = _measure(draw, test, font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_text_to_area(draw, text, max_width, max_height, base_size, bold, min_size=24):
    """
    Подбирает шрифт так, чтобы текст влез в область max_width × max_height.
    Возвращает (font, lines).
    """
    size = base_size
    while size >= min_size:
        font = _find_font(size, bold=bold)
        lines = _wrap_text(draw, text, font, max_width)
        total_h = sum(_measure(draw, line, font)[1] + 10 for line in lines)
        if total_h <= max_height:
            return font, lines
        size -= 4
    # Если даже минимальный не влез — обрезаем по строкам
    font = _find_font(min_size, bold=bold)
    lines = _wrap_text(draw, text, font, max_width)
    max_lines = max(1, max_height // (min_size + 8))
    return font, lines[:max_lines]


def _truncate_to_words(text: str, max_chars: int) -> str:
    """Обрезает текст до max_chars по границе слова с добавлением «…»."""
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:!?") + "…"


def create_card(data: Dict[str, str | int]) -> bytes:
    img = _gradient_background()
    draw = ImageDraw.Draw(img)

    # --- Шрифты ---
    font_logo = _find_font(60, bold=True)
    font_percent = _find_font(180, bold=True)
    font_label = _find_font(50, bold=True)
    font_section = _find_font(30, bold=False)

    # --- Логотип ---
    _draw_centered(draw, "TOXIC CHECK", font_logo, 80, NEON)

    # --- Процент (жёстко на y=350) ---
    flags = int(data.get("flags", 0))
    flag_color = _color_for_flags(flags)
    percent_text = f"{flags}%"
    pw, ph = _measure(draw, percent_text, font_percent)
    draw.text(((WIDTH - pw) / 2, 350), percent_text, font=font_percent, fill=flag_color)

    # Подпись под процентом
    _draw_centered(draw, "КРАСНЫХ ФЛАГОВ", font_section, 350 + ph + 20, WHITE)

    # --- Токсик и Тип ---
    y = 780
    _draw_centered(draw, f"Токсик: {data.get('toxic', '—')}", font_label, y, WHITE)
    y += 90
    _draw_centered(draw, f"Тип: {data.get('type', '—')}", font_label, y, WHITE)

    # --- Совет (авторазмер под область) ---
    y = 1050
    _draw_centered(draw, "СОВЕТ", font_section, y, NEON)
    y += 50

    advice = _truncate_to_words(str(data.get("advice", "")), 130)
    # Область для совета: ширина 960, высота 200
    font_advice, advice_lines = _fit_text_to_area(
        draw, advice, WIDTH - 120, 200, base_size=44, bold=False, min_size=28
    )
    for line in advice_lines:
        y = _draw_centered(draw, line, font_advice, y, WHITE)
        if y > 1300:
            break

    # --- Вывод (авторазмер под область) ---
    y = 1380
    _draw_centered(draw, "ВЫВОД", font_section, y, NEON)
    y += 50

    verdict = _truncate_to_words(str(data.get("verdict", "")), 300)
    font_verdict, verdict_lines = _fit_text_to_area(
        draw, verdict, WIDTH - 120, 350, base_size=42, bold=False, min_size=26
    )
    for line in verdict_lines:
        y = _draw_centered(draw, line, font_verdict, y, WHITE)
        if y > 1780:
            break

    # --- Подпись бота ---
    font_small = _find_font(28)
    w, _ = _measure(draw, f"@{BOT_USERNAME}", font_small)
    draw.text(((WIDTH - w) / 2, HEIGHT - 70), f"@{BOT_USERNAME}", font=font_small, fill=GREY)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
