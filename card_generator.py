# Генерация карточки 1080x1920 через Pillow (с точным позиционированием)
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

PADDING = 80
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
    """Возвращает (ширина, высота) текста."""
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_centered(draw, text, font, y, fill, anchor="mt"):
    """
    Рисует текст по центру по горизонтали.
    anchor:
      "mt" — точка (WIDTH/2, y) = середина по X, ВЕРХ глифов по Y
      "ms" — точка (WIDTH/2, y) = середина по X, BASELINE по Y
      "mm" — точка (WIDTH/2, y) = середина по X, СЕРЕДИНА глифов по Y
    """
    draw.text((WIDTH / 2, y), text, font=font, fill=fill, anchor=anchor)


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
    """Подбирает размер шрифта, чтобы СТРОКА влезла в max_width."""
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
    Возвращает (font, lines), обрезает лишние строки с «…».
    """
    size = base_size
    while size >= min_size:
        font = _find_font(size, bold=bold)
        lines = _wrap_text(draw, text, font, max_width)
        _, line_h = _measure(draw, "Ай", font)
        line_h += 12   # межстрочный отступ
        if len(lines) * line_h <= max_height:
            return font, lines
        size -= 2
    # Минимальный не влез — обрезаем строки
    font = _find_font(min_size, bold=bold)
    lines = _wrap_text(draw, text, font, max_width)
    _, line_h = _measure(draw, "Ай", font)
    line_h += 12
    max_lines = max(1, max_height // line_h)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if lines:
            lines[-1] = lines[-1].rstrip(".,;:!? ") + "…"
    return font, lines


def _truncate(text: str, max_chars: int) -> str:
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


# ====================== СБОРКА ======================
def create_card(data: Dict[str, str | int]) -> bytes:
    img = _gradient_background()
    draw = ImageDraw.Draw(img)

    # ---------- 1. ЛОГОТИП ----------
    font_logo = _find_font(64, bold=True)
    _draw_centered(draw, "TOXIC CHECK", font_logo, 70, NEON, anchor="mt")

    # ---------- 2. ПРОЦЕНТ (baseline фиксирован) ----------
    flags = int(data.get("flags", 0))
    flag_color = _color_for_flags(flags)
    percent_text = f"{flags}%"
    font_percent = _find_font(200, bold=True)

    percent_baseline = 520     # baseline цифр
    _draw_centered(draw, percent_text, font_percent, percent_baseline, flag_color, anchor="ms")

    # ---------- 3. КРАСНЫХ ФЛАГОВ — на 30px НИЖЕ baseline ----------
    font_caption = _find_font(34)
    caption_baseline = percent_baseline + 40
    _draw_centered(draw, "КРАСНЫХ ФЛАГОВ", font_caption, caption_baseline, WHITE, anchor="ms")

    # ---------- 4. ТОКСИК ----------
    toxic_text = f"Токсик: {data.get('toxic', '—')}"
    font_label = _fit_to_width(draw, toxic_text, MAX_TEXT_WIDTH, base_size=56, bold=True, min_size=32)
    _draw_centered(draw, toxic_text, font_label, 780, WHITE, anchor="mt")

    # ---------- 5. ТИП ----------
    type_text = f"Тип: {data.get('type', '—')}"
    font_type = _fit_to_width(draw, type_text, MAX_TEXT_WIDTH, base_size=56, bold=True, min_size=28)
    _draw_centered(draw, type_text, font_type, 870, WHITE, anchor="mt")

    # ---------- 6. СОВЕТ ----------
    font_section = _find_font(30)
    _draw_centered(draw, "СОВЕТ", font_section, 1070, NEON, anchor="mt")

    advice = _truncate(str(data.get("advice", "")), 140)
    font_advice, advice_lines = _fit_block(
        draw, advice,
        max_width=MAX_TEXT_WIDTH,
        max_height=200,
        base_size=42,
        bold=False,
        min_size=26,
    )
    _, advice_line_h = _measure(draw, "Ай", font_advice)
    advice_line_h += 12
    y = 1130
    for line in advice_lines:
        _draw_centered(draw, line, font_advice, y, WHITE, anchor="mt")
        y += advice_line_h

    # ---------- 7. ВЫВОД ----------
    _draw_centered(draw, "ВЫВОД", font_section, 1400, NEON, anchor="mt")

    verdict = _truncate(str(data.get("verdict", "")), 280)
    font_verdict, verdict_lines = _fit_block(
        draw, verdict,
        max_width=MAX_TEXT_WIDTH,
        max_height=380,
        base_size=40,
        bold=False,
        min_size=24,
    )
    _, verdict_line_h = _measure(draw, "Ай", font_verdict)
    verdict_line_h += 12
    y = 1460
    for line in verdict_lines:
        _draw_centered(draw, line, font_verdict, y, WHITE, anchor="mt")
        y += verdict_line_h

    # ---------- 8. ПОДПИСЬ БОТА ----------
    font_small = _find_font(28)
    _draw_centered(draw, f"@{BOT_USERNAME}", font_small, HEIGHT - 70, GREY, anchor="mt")

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
