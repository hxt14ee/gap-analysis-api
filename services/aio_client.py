"""
AIO Client — получение текста Google AI Overview через шлюз Thordata (SerpApi-совместимый).

Переменные окружения:
  SERPAPI_KEY  — ваш API-ключ Thordata
  SERPAPI_URL  — URL шлюза Thordata (например https://api.thordata.com/serp или аналогичный)

Возвращает:
  str  — текст AI Overview / Answer Box, если блок найден в ответе
  None — если блок отсутствует (статус "aio_not_found")
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
SERPAPI_URL: str = os.getenv("SERPAPI_URL", "https://serpapi.com/search")

# Тайм-аут ожидания ответа от Thordata (секунды)
_REQUEST_TIMEOUT = 30


def _extract_aio_text(data: dict) -> str | None:
    """
    Извлекает текст AI Overview или Answer Box из JSON-ответа SerpApi / Thordata.

    Порядок приоритетов:
      1. ai_overview.text_blocks  (новый формат Google AI Overview)
      2. ai_overview.page_context (альтернативный ключ)
      3. answer_box.answer        (Featured Snippet / Direct Answer)
      4. answer_box.snippet
    """
    # --- AI Overview (основной блок) ---
    aio = data.get("ai_overview")
    if isinstance(aio, dict):
        # Новый формат: список текстовых блоков
        blocks = aio.get("text_blocks") or aio.get("blocks") or []
        texts = []
        for block in blocks:
            if isinstance(block, dict):
                snippet = block.get("snippet") or block.get("text") or ""
                if snippet:
                    texts.append(snippet.strip())
        if texts:
            return "\n\n".join(texts)

        # Запасной ключ
        context = aio.get("page_context") or aio.get("answer") or ""
        if context:
            return context.strip()

    # --- Answer Box (Featured Snippet) ---
    answer_box = data.get("answer_box")
    if isinstance(answer_box, dict):
        for key in ("answer", "snippet", "result"):
            value = answer_box.get(key)
            if value and isinstance(value, str):
                return value.strip()

    return None


async def fetch_aio(query: str) -> str | None:
    """
    Выполняет запрос к Thordata (SerpApi-шлюз) и возвращает текст AI Overview.

    Args:
        query: поисковый запрос.

    Returns:
        Строку с текстом AI Overview/Answer Box, или None если блок не найден.

    Raises:
        RuntimeError: при сетевой ошибке или некорректном ответе от API.
    """
    if not SERPAPI_KEY:
        raise RuntimeError(
            "SERPAPI_KEY не задан. Укажите ключ Thordata в переменной окружения SERPAPI_KEY."
        )

    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "hl": "ru",
        "gl": "ru",
        "num": "10",
    }

    logger.info("Запрос к Thordata SerpApi: q=%r, url=%s", query, SERPAPI_URL)

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        try:
            response = await client.get(SERPAPI_URL, params=params)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Thordata вернула HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Ошибка соединения с Thordata: {exc}") from exc

    try:
        data: dict = response.json()
    except Exception as exc:
        raise RuntimeError(f"Не удалось распарсить JSON-ответ от Thordata: {exc}") from exc

    # Проверяем ошибки на уровне API
    if "error" in data:
        raise RuntimeError(f"Ошибка Thordata API: {data['error']}")

    text = _extract_aio_text(data)
    if text is None:
        logger.info("AI Overview / Answer Box не найден для запроса: %r", query)
    else:
        logger.info("AI Overview получен (%d символов)", len(text))

    return text
