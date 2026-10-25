# LLM-клиент со сжатием изображений
import base64
import io
import httpx
from PIL import Image
from config import LLM_API_KEY, LLM_API_URL, LLM_MODEL
from prompts import MODES


def _compress(image_bytes: bytes, max_side: int = 720, quality: int = 75) -> bytes:
    """Сжимает картинку — экономия токенов в 2.5-4 раза."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.thumbnail((max_side, max_side), Image.LANCZOS)
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()
    except Exception:
        return image_bytes


async def analyze(image_bytes: bytes, mode: str) -> dict:
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")

    prompt = MODES[mode]["prompt"]
    parser = MODES[mode]["parser"]

    # Сжимаем картинку ПЕРЕД отправкой — экономия токенов
    image_bytes = _compress(image_bytes)
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
        "max_tokens": 400,
        "temperature": 0.8,
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(LLM_API_URL, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"LLM API {resp.status_code}: {resp.text[:300]}")
        data = resp.json()

    raw = data["choices"][0]["message"]["content"] or ""
    return parser(raw.strip())
