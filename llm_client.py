# LLM-клиент: сжатие по режимам, семафор, стабильная температура
import base64
import io
import asyncio
import httpx
from PIL import Image
from config import LLM_API_KEY, LLM_API_URL, LLM_MODEL
from prompts import MODES, PARSERS

_api_semaphore = asyncio.Semaphore(20)


def _compress_sync(image_bytes: bytes, mode: str = "toxic") -> bytes:
    """
    Сжимает картинку:
    - Переписки/посты (toxic, leader, flex) → 600px (текст читается)
    - Селфи и мемы → 512px (можно агрессивнее)
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        if mode in ("toxic", "leader", "flex"):
            max_side = 600
            quality = 70
        else:
            max_side = 512
            quality = 70
        
        img.thumbnail((max_side, max_side), Image.BILINEAR)
        
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=False)
        return buf.getvalue()
    except Exception:
        return image_bytes


async def analyze(image_bytes: bytes, mode: str) -> dict:
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")

    prompt = MODES[mode]
    parser = PARSERS[mode]

    # Сжатие в потоке с учётом режима
    image_bytes = await asyncio.to_thread(_compress_sync, image_bytes, mode)
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
        "max_tokens": 300,
        "temperature": 0.4,
    }
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    async with _api_semaphore:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(LLM_API_URL, json=payload, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"LLM API {resp.status_code}: {resp.text[:300]}")
            data = resp.json()

    raw = data["choices"][0]["message"]["content"] or ""
    return parser(raw.strip())
