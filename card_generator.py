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

PADDING = 80                    # отступ по бокам
MAX_TEXT_WIDTH = WIDTH - PADDING * 2   # 920px

_HERE = os.path.dirname(os.path.abspath(__file__))
FONT_REGULAR = os.path.join(_HERE, "fonts", "DejaVuSans.ttf")
FONT_BOLD = os.path.join(_HERE, "fonts", "DejaVuSans-Bold.ttf")

print(f"[FONT] regular = {FONT_REGULAR} → exists: {os.path.exists(FONT_REGULAR)}")
print(f"[FONT] bold    = {FONT_BOLD} → exists: {os.path.exists(FONT_BOLD)}")


# ====================== ШРИФТЫ ======================
def _find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
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


# ====================== ГЕОМЕТРИЯ ======================
def _measure(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_centered(draw, text, font, y, fill) -> int:
    """Рисует по центру. Возвращает Y конца строки."""
    w, h = _measure(draw, text, font)
    draw.text(((WIDTH - w) / 2, y), text, font=font, fill=fill)
    return y + h


def _wrap_text(draw, text, font, max_width):
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


def _fit_to_width(draw, text, max_width, base_size, bold=False, min_size=20):
    """Подбирает размер шрифта, чтобы строка влезла в max_width."""
    size = base_size
    while size >= min_size:
        font = _find_font(size, bold=bold)
        w, _ = _measure(draw, text, font)
        if w <= max_width:
            return font
        size -= 2
    return _find_font(min_size, bold=bold)


def _fit_block(draw, text, max_width, max_height, base_size, bold=False, min_size=22):
    """
    Авто-подгонка многострочного текста в область max_width × max_height.
    Возвращает (font, lines) — гарантированно влезает по высоте,
    лишние строки отбрасываются.
    """
    size = base_size
    while size >= min_size:
        font = _find_font(size, bold=bold)
        lines = _wrap_text(draw, text, font, max_width)
        line_h = _measure(draw, "Ай", font)[1] + 8
        if len(lines) * line_h <= max_height:
            return font, lines
        size -= 2
    # Если даже минимальный не влез — обрезаем по строкам
    font = _find_font(min_size, bold=bold)
    lines = _wrap_text(draw, text, font, max_width)
    line_h = _measure(draw, "Ай", font)[1] + 8
    max_lines = max(1, max_height // line_h)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        # Добавляем «…» к последней строке
        if lines:
            lines[-1] = lines[-1].rstrip(".,;:!? ") + "…"
    return font, lines


def _truncate(text: str, max_chars: int) -> str:
    """Обрезка по границе слова с добавлением «…»."""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(".,;:!?") + "…"


# ====================== ФОН ======================
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


# ====================== СБОРКА КАРТОЧКИ ======================
def create_card(data: Dict[str, str | int]) -> bytes:
    img = _gradient_background()
    draw = ImageDraw.Draw(img)

    # ---------- 1. ЛОГОТИП (Y: 60–150) ----------
    font_logo = _find_font(64, bold=True)
    logo_w, logo_h = _measure(draw, "TOXIC CHECK", font_logo)
    draw.text(((WIDTH - logo_w) / 2, 60), "TOXIC CHECK", font=font_logo, fill=NEON)

    # ---------- 2. ПРОЦЕНТ (Y: 260) ----------
    flags = int(data.get("flags", 0))
    flag_color = _color_for_flags(flags)
    percent_text = f"{flags}%"
    font_percent = _find_font(200, bold=True)
    pw, ph = _measure(draw, percent_text, font_percent)

    percent_y = 260
    draw.text(((WIDTH - pw) / 2, percent_y), percent_text, font=font_percent, fill=flag_color)

    # ---------- 3. КРАСНЫХ ФЛАГОВ — строго ПОД цифрой ----------
    font_caption = _find_font(34)
    caption_y = percent_y + ph + 25   # +25px отступ от низа цифры
    _draw_centered(draw, "КРАСНЫХ ФЛАГОВ", font_caption, caption_y, WHITE)

    # ---------- 4. ТОКСИК (Y: 780) ----------
    y = 780
    toxic_text = f"Токсик: {data.get('toxic', '—')}"
    # Авто-размер по ширине
    font_label = _fit_to_width(draw, toxic_text, MAX_TEXT_WIDTH, base_size=58, bold=True, min_size=32)
    _draw_centered(draw, toxic_text, font_label, y, WHITE)
    y += 90

    # ---------- 5. ТИП (Y: 870) ----------
    type_text = f"Тип: {data.get('type', '—')}"
    # Авто-размер по ширине (важно — может быть длинным!)
    font_type = _fit_to_width(draw, type_text, MAX_TEXT_WIDTH, base_size=58, bold=True, min_size=28)
    _draw_centered(draw, type_text, font_type, y, WHITE)

    # ---------- 6. СОВЕТ (Y: 1050–1300) ----------
    y = 1060
    font_section = _find_font(30)
    _draw_centered(draw, "СОВЕТ", font_section, y, NEON)
    y += 50

    advice = _truncate(str(data.get("advice", "")), 140)
    font_advice, advice_lines = _fit_block(
        draw, advice,
        max_width=MAX_TEXT_WIDTH,
        max_height=200,
        base_size=42,
        bold=False,
        min_size=26,
    )
    line_h = _measure(draw, "Ай", font_advice)[1] + 12
    for line in advice_lines:
        _draw_centered(draw, line, font_advice, y, WHITE)
        y += line_h

    # ---------- 7. ВЫВОД (Y: 1400–1820) ----------
    y = 1400
    _draw_centered(draw, "ВЫВОД", font_section, y, NEON)
    y += 50

    verdict = _truncate(str(data.get("verdict", "")), 280)
    font_verdict, verdict_lines = _fit_block(
        draw, verdict,
        max_width=MAX_TEXT_WIDTH,
        max_height=380,
        base_size=40,
        bold=False,
        min_size=24,
    )
    line_h = _measure(draw, "Ай", font_verdict)[1] + 12
    for line in verdict_lines:
        _draw_centered(draw, line, font_verdict, y, WHITE)
        y += line_h

    # ---------- 8. ПОДПИСЬ БОТА (Y: 1850) ----------
    font_small = _find_font(28)
    _draw_centered(draw, f"@{BOT_USERNAME}", font_small, HEIGHT - 70, GREY)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
