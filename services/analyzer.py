"""
Analyzer service: uses Instructor + a mock OpenAI-compatible client to produce
a structured GapAnalysisResult from the AIO text and the scraped page text.

The mock client avoids any real API call so the MVP runs without credentials.
In production, replace `_build_mock_client()` with a real OpenAI / Anthropic
client and point `MODEL` at the desired model name.
"""
from __future__ import annotations

import os
import json
from typing import Any
import instructor
from openai import AsyncOpenAI

from schemas import GapAnalysisResult, Fact, Gap, Recommendation

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ---------------------------------------------------------------------------
# Mock client – returns deterministic structured output without network calls
# ---------------------------------------------------------------------------

class _MockOpenAIClient:
    """Minimal duck-type of AsyncOpenAI for offline / CI use."""

    class chat:
        class completions:
            @staticmethod
            async def create(**kwargs: Any) -> Any:
                # Build a deterministic GapAnalysisResult from the prompt
                messages = kwargs.get("messages", [])
                user_content = ""
                for m in messages:
                    if m.get("role") == "user":
                        user_content = m.get("content", "")
                        break

                # Extract a short snippet from the prompt to vary the output
                snippet = (user_content[:120] if user_content else "general topic").strip()

                result = GapAnalysisResult(
                    facts=[
                        Fact(
                            statement="The AIO mentions that the topic has multiple well-established sub-categories.",
                            present_in_page=True,
                        ),
                        Fact(
                            statement="The AIO references third-party tools commonly used in the industry.",
                            present_in_page=False,
                        ),
                        Fact(
                            statement="The AIO highlights performance as a primary differentiator.",
                            present_in_page=False,
                        ),
                    ],
                    gaps=[
                        Gap(
                            topic="Third-party tool ecosystem",
                            description="The AIO mentions specific tools used by practitioners, but the page does not cover or compare them.",
                        ),
                        Gap(
                            topic="Performance benchmarks",
                            description="The AIO emphasises performance advantages; the page lacks any quantitative comparison.",
                        ),
                    ],
                    recommendations=[
                        Recommendation(
                            action="Add a dedicated section listing and briefly describing the popular third-party tools referenced in the AIO.",
                            priority="high",
                        ),
                        Recommendation(
                            action="Include a performance benchmark table or chart comparing this topic against alternatives.",
                            priority="high",
                        ),
                        Recommendation(
                            action="Expand the introduction to explicitly state the key differentiators highlighted by Google's AI Overview.",
                            priority="medium",
                        ),
                    ],
                    summary=(
                        f"The analysed page covers the foundational concepts well but is missing "
                        f"coverage of the tool ecosystem and performance data that Google's AI Overview "
                        f"emphasises. Addressing these gaps would improve topical authority and "
                        f"alignment with what Google surfaces for this query."
                    ),
                )

                # Instructor expects a response object with choices; we return the
                # model directly because instructor's `from_response` path is bypassed
                # when we patch at the patch level.  Instead we rely on the
                # `response_model` kwarg that instructor injects – we just need to
                # return something that the patched client can deserialise.
                # The cleanest way: return a fake ChatCompletion whose message
                # content is the JSON of our result.
                class _FakeMessage:
                    content = result.model_dump_json()
                    tool_calls = None

                class _FakeChoice:
                    message = _FakeMessage()
                    finish_reason = "stop"

                class _FakeCompletion:
                    choices = [_FakeChoice()]
                    model = MODEL
                    usage = None

                return _FakeCompletion()


def _build_client() -> Any:
    """Return a real or mock OpenAI async client depending on env vars."""
    if OPENAI_API_KEY and OPENAI_API_KEY not in ("", "mock", "MOCK"):
        return AsyncOpenAI(api_key=OPENAI_API_KEY)
    return _MockOpenAIClient()


_raw_client = _build_client()

# Patch with Instructor so it enforces the Pydantic response_model.
# When using the mock client the patching is a no-op structurally but keeps
# the call-site identical to the real path.
try:
    client = instructor.from_openai(_raw_client, mode=instructor.Mode.JSON)
except Exception:
    # Fallback: use mock directly if patching fails (e.g. incompatible versions)
    client = _raw_client  # type: ignore[assignment]


SYSTEM_PROMPT = """\
You are an expert SEO content analyst.
Given an AI Overview text and the main text of a web page, you must:
1. Extract the key factual claims made in the AI Overview.
2. Identify which facts are NOT covered adequately by the web page (gaps).
3. Produce concrete, prioritised recommendations to close those gaps.
Return your answer as valid JSON conforming exactly to the schema provided.
"""


def _build_user_prompt(aio_text: str, page_text: str) -> str:
    return (
        f"## AI Overview\n{aio_text}\n\n"
        f"## Web Page Content\n{page_text}"
    )


async def run_gap_analysis(aio_text: str, page_text: str) -> GapAnalysisResult:
    """
    Call the LLM (or mock) and return a validated GapAnalysisResult.
    """
    if hasattr(client, "chat"):
        # Real instructor-patched client
        result: GapAnalysisResult = await client.chat.completions.create(
            model=MODEL,
            response_model=GapAnalysisResult,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(aio_text, page_text)},
            ],
            temperature=0.2,
        )
        return result
    else:
        # Pure mock fallback
        raw = await _MockOpenAIClient.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(aio_text, page_text)},
            ],
        )
        return GapAnalysisResult.model_validate_json(raw.choices[0].message.content)
