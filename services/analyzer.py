"""
Analyzer service: использует Instructor + OpenAI (или OpenRouter) для получения
структурированного GapAnalysisResult из текста AI Overview и текста веб-страницы.

Переменные окружения:
  OPENAI_API_KEY      — ключ OpenAI
  OPENROUTER_API_KEY  — ключ OpenRouter (альтернатива; берётся если OPENAI_API_KEY не задан)
  OPENAI_MODEL        — модель (по умолчанию gpt-4o-mini)
  OPENAI_BASE_URL     — переопределить base URL (например для OpenRouter: https://openrouter.ai/api/v1)
"""
from __future__ import annotations

import logging
import os

import instructor
from openai import AsyncOpenAI

from schemas import GapAnalysisResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")

# ---------------------------------------------------------------------------
# Построение клиента
# ---------------------------------------------------------------------------

def _build_client() -> instructor.AsyncInstructor:
    """
    Возвращает Instructor-клиент, обёрнутый поверх AsyncOpenAI.

    Логика выбора ключа и эндпоинта:
      1. Если задан OPENAI_API_KEY  → используем OpenAI напрямую.
      2. Если задан OPENROUTER_API_KEY → используем OpenRouter (openrouter.ai/api/v1).
      3. Иначе → поднимаем RuntimeError при старте, чтобы сразу было видно проблему.
    """
    if OPENAI_API_KEY:
        raw = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL or None,
        )
        logger.info("LLM-клиент: OpenAI, модель=%s", MODEL)
    elif OPENROUTER_API_KEY:
        raw = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENAI_BASE_URL or "https://openrouter.ai/api/v1",
        )
        logger.info("LLM-клиент: OpenRouter, модель=%s", MODEL)
    else:
        raise RuntimeError(
            "Не задан ни OPENAI_API_KEY, ни OPENROUTER_API_KEY. "
            "Укажите один из ключей в переменных окружения."
        )

    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


client: instructor.AsyncInstructor = _build_client()

# ---------------------------------------------------------------------------
# Промпты
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Ты — эксперт по SEO и анализу контента.
Тебе будут переданы два текста:
  1. AI Overview — краткое резюме, которое Google показывает над результатами поиска.
  2. Текст веб-страницы — основное содержимое анализируемой страницы.

Твоя задача:
  1. Извлечь все ключевые фактические утверждения из AI Overview (поле facts).
  2. Для каждого факта определить, раскрыт ли он на веб-странице (present_in_page).
  3. Составить список пробелов — тем из AI Overview, которые страница не покрывает (gaps).
  4. Дать конкретные рекомендации с приоритетом для устранения каждого пробела (recommendations).
  5. Написать краткое итоговое резюме (summary).

Верни ответ строго в формате JSON, соответствующем предоставленной схеме. Без лишнего текста.
"""


def _build_user_prompt(aio_text: str, page_text: str) -> str:
    return (
        f"## AI Overview\n{aio_text}\n\n"
        f"## Текст веб-страницы\n{page_text}"
    )


# ---------------------------------------------------------------------------
# Основная функция
# ---------------------------------------------------------------------------

async def run_gap_analysis(aio_text: str, page_text: str) -> GapAnalysisResult:
    """
    Обращается к LLM через Instructor и возвращает валидированный GapAnalysisResult.

    Args:
        aio_text:  текст AI Overview, полученный от Thordata.
        page_text: текст веб-страницы, извлечённый Trafilatura.

    Returns:
        Структурированный результат gap-анализа.
    """
    logger.info(
        "Запуск gap-анализа. AIO: %d симв., страница: %d симв.",
        len(aio_text), len(page_text),
    )

    result: GapAnalysisResult = await client.chat.completions.create(
        model=MODEL,
        response_model=GapAnalysisResult,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(aio_text, page_text)},
        ],
        temperature=0.2,
    )

    logger.info(
        "Gap-анализ завершён. Фактов: %d, пробелов: %d, рекомендаций: %d",
        len(result.facts), len(result.gaps), len(result.recommendations),
    )
    return result
