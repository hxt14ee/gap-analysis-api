from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import init_db, get_db
from models import AnalysisRequest
from schemas import AnalyzeRequest, AnalyzeResponse, GapAnalysisResult
from services.aio_client import fetch_aio
from services.scraper import scrape_page
from services.analyzer import run_gap_analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("БД готова.")
    yield


app = FastAPI(
    title="Gap Analysis API",
    description="Gap-анализ между Google AI Overview и веб-страницей.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Meta"])
async def health_check():
    return {"status": "ok"}


@app.get(
    "/history",
    response_model=List[AnalyzeResponse],
    tags=["Analysis"],
    summary="Последние 10 анализов",
)
async def get_history(db: AsyncSession = Depends(get_db)) -> List[AnalyzeResponse]:
    result = await db.execute(
        select(AnalysisRequest)
        .order_by(desc(AnalysisRequest.timestamp))
        .limit(10)
    )
    records = result.scalars().all()
    return [
        AnalyzeResponse(
            id=r.id,
            status=r.status,
            query=r.query,
            url=r.url,
            timestamp=r.timestamp,
            ai_overview_text=r.ai_overview_text,
            page_text=r.page_text,
            analysis_result=GapAnalysisResult(**r.analysis_result)
            if r.analysis_result
            else None,
        )
        for r in records
    ]


@app.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Analysis"],
    summary="Запустить gap-анализ",
)
async def analyze(
    body: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    url_str = str(body.url)

    # Создаём запись сразу, чтобы id был доступен при любом исходе
    record = AnalysisRequest(query=body.query, url=url_str, status="pending")
    db.add(record)
    await db.commit()
    await db.refresh(record)

    try:
        # 1. AI Overview
        aio_text = await fetch_aio(body.query)
        if aio_text is None:
            record.status = "aio_not_found"
            await db.commit()
            await db.refresh(record)
            return AnalyzeResponse(
                id=record.id, status=record.status, query=record.query,
                url=record.url, timestamp=record.timestamp,
            )

        record.ai_overview_text = aio_text

        # 2. Scrape
        page_text = await scrape_page(url_str)
        if page_text is None:
            record.status = "scrape_failed"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Не удалось извлечь текст со страницы: {url_str}",
            )

        record.page_text = page_text

        # 3. LLM анализ
        analysis: GapAnalysisResult = await run_gap_analysis(aio_text, page_text)

        # 4. Сохранение
        record.analysis_result = analysis.model_dump()
        record.status = "completed"
        await db.commit()
        await db.refresh(record)

        return AnalyzeResponse(
            id=record.id, status=record.status, query=record.query,
            url=record.url, timestamp=record.timestamp,
            ai_overview_text=record.ai_overview_text,
            page_text=record.page_text,
            analysis_result=analysis,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Ошибка анализа: %s", exc)
        record.status = "error"
        try:
            await db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
