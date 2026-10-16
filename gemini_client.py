# LLM-клиент под Groq (Llama 4 Vision, OpenAI-совместимый API)
import base64
import re
from typing import Dict

import httpx

from config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL

# Промт для анализа
PROMPT = """Ты — аналитик отношений. Проанализируй скрин переписки.

КРИТИЧЕСКИ ВАЖНО: ответ должен содержать РОВНО 5 строк, каждая с новой строки.
Никаких вступлений, объяснений, markdown, звёздочек. Только эти 5 строк:

ФЛАГИ: <число 0-100>%
ТОКСИК: <ты|он|она|оба|никто>
ТИП: <3-5 слов>
СОВЕТ: <одно предложение, до 15 слов>
ВЫВОД: <2-3 предложения>

ПРАВИЛА:
- Пиши ТОЛЬКО на русском языке. Даже если переписка на английском.
- Токсик — тот, кто манипулирует, обесценивает, давит, унижает.
- Не ставь диагнозы. Не оскорбляй.
- Если на фото нет переписки — ТИП: не переписка.
"""


def _parse_response(text: str) -> Dict[str, str | int]:
    """Парсит ответ модели. Устойчив к лишнему тексту перед полями."""
    result = {
        "flags": 0,
        "toxic": "никто",
        "type": "не определено",
        "advice": "будь собой",
        "verdict": "Не удалось разобрать ответ модели.",
    }

    for line in text.splitlines():
        line = line.strip()
        upper = line.upper()
        if upper.startswith("ФЛАГИ"):
            m = re.search(r"(\d{1,3})", line)
            if m:
                result["flags"] = max(0, min(100, int(m.group(1))))
        elif upper.startswith("ТОКСИК"):
            result["toxic"] = line.split(":", 1)[-1].strip() or "никто"
        elif upper.startswith("ТИП"):
            result["type"] = line.split(":", 1)[-1].strip() or "не определено"
        elif upper.startswith("СОВЕТ"):
            result["advice"] = line.split(":", 1)[-1].strip() or "будь собой"
        elif upper.startswith("ВЫВОД"):
            result["verdict"] = line.split(":", 1)[-1].strip()

    if "ВЫВОД" in text.upper():
        parts = re.split(r"ВЫВОД\s*:", text, flags=re.IGNORECASE)
        if len(parts) > 1:
            sentences = re.split(r"(?<=[.!?])\s+", parts[1].strip())
            result["verdict"] = " ".join(sentences[:3]).strip()

    # Защита от английского
    lang_map = {
        "he": "он", "she": "она", "both": "оба",
        "nobody": "никто", "you": "ты", "they": "оба",
    }
    toxic_low = str(result["toxic"]).lower()
    if toxic_low in lang_map:
        result["toxic"] = lang_map[toxic_low]

    return result


async def analyze(image_bytes: bytes) -> Dict[str, str | int]:
    """Отправляет изображение в Groq (Llama 4 Vision)."""
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 500,
        "temperature": 0.6,
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(GROQ_API_URL, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Groq API {resp.status_code}: {resp.text[:300]}")
        data = resp.json()

    try:
        raw = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Unexpected Groq response: {data}") from e

    return _parse_response(raw.strip())
