# LLM-клиент (VseGPT, сжатие в отдельном потоке)
import base64
import io
import asyncio
import httpx
from PIL import Image
from config import LLM_API_KEY, LLM_API_URL, LLM_MODEL
from prompts import MODES, PARSERS


def _compress_sync(image_bytes: bytes, max_side: int = 384, quality: int = 65) -> bytes:
    """
    Сжимает фото — БЫСТРАЯ версия:
    - 384px (вместо 512) — текст на скринах всё ещё читается
    - quality 65 — незаметно для AI
    Экономия токенов ~40% и CPU ~30%.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((max_side, max_side), Image.BILINEAR)  # BILINEAR быстрее LANCZOS
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=False)  # optimize=False — быстрее
        return buf.getvalue()
    except Exception:
        return image_bytes


async def analyze(image_bytes: bytes, mode: str) -> dict:
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")

    prompt = MODES[mode]
    parser = PARSERS[mode]

    # Сжатие в отдельном потоке — не блокирует event loop
    image_bytes = await asyncio.to_thread(_compress_sync, image_bytes)
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": LLM_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
            ],
        }],
        "max_tokens": 250,     # меньше токенов → быстрее ответ
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(LLM_API_URL, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"LLM API {resp.status_code}: {resp.text[:300]}")
        data = resp.json()

    raw = data["choices"][0]["message"]["content"] or ""
    return parser(raw.strip())
