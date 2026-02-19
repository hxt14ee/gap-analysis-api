"""
Analyzer service: Instructor + OpenRouter (по умолчанию) или OpenAI.

Приоритет выбора клиента:
  1. OPENROUTER_API_KEY → OpenRouter (https://openrouter.ai/api/v1)
  2. OPENAI_API_KEY     → OpenAI напрямую
  Если ни одного ключа нет — RuntimeError при старте.

Переменные окружения:
  OPENROUTER_API_KEY  — ключ OpenRouter (приоритетный)
  OPENAI_API_KEY      — ключ OpenAI (резервный)
  OPENAI_MODEL        — модель (по умолчанию openai/gpt-4o-mini для OpenRouter)
  OPENAI_BASE_URL     — переопределение base URL (опционально)
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

OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")

# Имя модели: по умолчанию openai/gpt-4o-mini через OpenRouter.
# При переключении на OpenAI напрямую смените на "gpt-4o-mini".
MODEL: str = os.getenv("OPENAI_MODEL", "openai/gpt-4o-mini")


# ---------------------------------------------------------------------------
# Построение клиента
# ---------------------------------------------------------------------------

def _build_client() -> instructor.AsyncInstructor:
    """
    Возвращает Instructor-клиент поверх AsyncOpenAI.

    OpenRouter — приоритет (задаётся OPENROUTER_API_KEY).
    OpenAI    — резерв    (задаётся OPENAI_API_KEY).
    """
    if OPENROUTER_API_KEY:
        raw = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url=OPENAI_BASE_URL or "https://openrouter.ai/api/v1",
        )
        logger.info("LLM-клиент: OpenRouter, модель=%s", MODEL)
    elif OPENAI_API_KEY:
        raw = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL or None,
        )
        logger.info("LLM-клиент: OpenAI, модель=%s", MODEL)
    else:
        raise RuntimeError(
            "Не задан ни OPENROUTER_API_KEY, ни OPENAI_API_KEY. "
            "Укажите один из ключей в файле .env."
        )

    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


client: instructor.AsyncInstructor = _build_client()


# ---------------------------------------------------------------------------
# Промпты
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Ты — эксперт по SEO и GEO-оптимизации контента.
Тебе передаётся два текста:
  1. AI Overview — краткое резюме, которое Google показывает над результатами поиска.
  2. Текст веб-страницы — основное содержимое анализируемой страницы.

Твоя задача:
  1. Извлечь все ключевые фактические утверждения из AI Overview (поле facts).
  2. Для каждого факта определить, раскрыт ли он на странице (present_in_page: true/false).
  3. Составить список пробелов — тем из AI Overview, которые страница не покрывает (gaps).
  4. Дать конкретные рекомендации с приоритетом для устранения каждого пробела (recommendations).
  5. Написать краткое итоговое резюме (summary).

Верни ответ строго в формате JSON согласно предоставленной схеме. Без пояснений вне JSON.
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
