"""
Gap Analysis REST API
=====================
POST /analyze  – Run the full gap analysis pipeline.
GET  /health   – Simple health check.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import init_db, get_db
from models import AnalysisRequest
from schemas import AnalyzeRequest, AnalyzeResponse, GapAnalysisResult
from services.aio_client import fetch_aio
from services.scraper import scrape_page
from services.analyzer import run_gap_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: create tables on startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database tables …")
    await init_db()
    logger.info("Database ready.")
    yield
    logger.info("Shutting down …")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Gap Analysis API",
    description=(
        "Compares a web page against Google AI Overview text to identify "
        "content gaps and generate SEO recommendations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Meta"])
async def health_check():
    return {"status": "ok"}


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Analysis"],
    summary="Run a gap analysis between an AI Overview and a web page",
)
async def analyze(
    body: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """
    **Pipeline**

    1. Fetch the AI Overview for *query* (mock).
    2. Scrape *url* with trafilatura.
    3. Run LLM gap analysis (mock or real depending on env vars).
    4. Persist everything to PostgreSQL and return the result.
    """
    url_str = str(body.url)

    # Create a pending record immediately so we have an id to return on error
    record = AnalysisRequest(
        query=body.query,
        url=url_str,
        status="pending",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    try:
        # ------------------------------------------------------------------ #
        # Step 1 – AI Overview
        # ------------------------------------------------------------------ #
        logger.info("Fetching AIO for query: %r", body.query)
        aio_text = await fetch_aio(body.query)

        if aio_text is None:
            record.status = "aio_not_found"
            await db.commit()
            await db.refresh(record)
            return AnalyzeResponse(
                id=record.id,
                status=record.status,
                query=record.query,
                url=record.url,
                timestamp=record.timestamp,
                ai_overview_text=None,
                page_text=None,
                analysis_result=None,
            )

        record.ai_overview_text = aio_text

        # ------------------------------------------------------------------ #
        # Step 2 – Scrape page
        # ------------------------------------------------------------------ #
        logger.info("Scraping URL: %s", url_str)
        page_text = await scrape_page(url_str)

        if page_text is None:
            record.status = "scrape_failed"
            await db.commit()
            await db.refresh(record)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not extract text content from URL: {url_str}",
            )

        record.page_text = page_text

        # ------------------------------------------------------------------ #
        # Step 3 – LLM gap analysis
        # ------------------------------------------------------------------ #
        logger.info("Running gap analysis …")
        analysis: GapAnalysisResult = await run_gap_analysis(aio_text, page_text)

        # ------------------------------------------------------------------ #
        # Step 4 – Persist result
        # ------------------------------------------------------------------ #
        record.analysis_result = analysis.model_dump()
        record.status = "completed"
        await db.commit()
        await db.refresh(record)

        logger.info("Analysis completed. id=%s", record.id)
        return AnalyzeResponse(
            id=record.id,
            status=record.status,
            query=record.query,
            url=record.url,
            timestamp=record.timestamp,
            ai_overview_text=record.ai_overview_text,
            page_text=record.page_text,
            analysis_result=analysis,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unhandled error during analysis: %s", exc)
        record.status = "error"
        try:
            await db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {exc}",
        )
