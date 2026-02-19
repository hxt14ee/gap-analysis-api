"""
AIO Client — получение Google AI Overview через Thordata ScraperAPI.

Формат запроса (из документации Thordata):
  POST https://scraperapi.thordata.com/request
  Authorization: Bearer <SERPAPI_KEY>
  Content-Type: application/x-www-form-urlencoded
  Body: engine=google&q=<query>&json=1&ai_overview=true

Переменные окружения:
  SERPAPI_KEY  — ваш API-ключ Thordata (передаётся в заголовке Authorization)
  SERPAPI_URL  — URL эндпоинта (по умолчанию https://scraperapi.thordata.com/request)

Возвращает:
  str  — текст AI Overview / Answer Box
  None — если Google не показывает AI Overview для данного запроса
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

SERPAPI_KEY: str = os.getenv("SERPAPI_KEY", "")
SERPAPI_URL: str = os.getenv(
    "SERPAPI_URL",
    "https://scraperapi.thordata.com/request",
)

_REQUEST_TIMEOUT = 30  # секунды


def _extract_aio_text(data: dict) -> str | None:
    """
    Извлекает текст AI Overview или Answer Box из JSON-ответа Thordata.

    Порядок приоритетов:
      1. ai_overview.text_blocks  (массив текстовых блоков)
      2. ai_overview.snippet / answer / page_context
      3. answer_box.answer / snippet / result
    """
    aio = data.get("ai_overview")
    if isinstance(aio, dict):
        blocks: list = aio.get("text_blocks") or aio.get("blocks") or []
        texts = []
        for block in blocks:
            if isinstance(block, dict):
                text = block.get("snippet") or block.get("text") or ""
                if text:
                    texts.append(text.strip())
        if texts:
            return "\n\n".join(texts)

        for key in ("snippet", "answer", "page_context"):
            value = aio.get(key)
            if value and isinstance(value, str):
                return value.strip()

    answer_box = data.get("answer_box")
    if isinstance(answer_box, dict):
        for key in ("answer", "snippet", "result"):
            value = answer_box.get(key)
            if value and isinstance(value, str):
                return value.strip()

    return None


async def fetch_aio(query: str) -> str | None:
    """
    Выполняет POST-запрос к Thordata ScraperAPI и возвращает текст AI Overview.

    Args:
        query: поисковый запрос.

    Returns:
        Строку с текстом AI Overview/Answer Box, или None если блок не найден.

    Raises:
        RuntimeError: при ошибке конфигурации, сети или API.
    """
    if not SERPAPI_KEY:
        raise RuntimeError(
            "SERPAPI_KEY не задан. Укажите ключ Thordata в переменной окружения SERPAPI_KEY."
        )

    headers = {
        "Authorization": f"Bearer {SERPAPI_KEY}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    # Thordata принимает параметры как form-encoded тело POST-запроса
    data = {
        "engine": "google",
        "q": query,
        "json": "1",
        "ai_overview": "true",
    }

    logger.info("Запрос к Thordata ScraperAPI: q=%r url=%s", query, SERPAPI_URL)

    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        try:
            response = await client.post(SERPAPI_URL, headers=headers, data=data)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Thordata вернула HTTP {exc.response.status_code}: {exc.response.text[:300]}"
            ) from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Ошибка соединения с Thordata: {exc}") from exc

    try:
        result: dict = response.json()
    except Exception as exc:
        raise RuntimeError(f"Не удалось распарсить JSON-ответ от Thordata: {exc}") from exc

    if "error" in result:
        raise RuntimeError(f"Ошибка Thordata API: {result['error']}")

    text = _extract_aio_text(result)
    if text is None:
        logger.info("AI Overview не найден для запроса: %r", query)
    else:
        logger.info("AI Overview получен (%d символов)", len(text))

    return text
