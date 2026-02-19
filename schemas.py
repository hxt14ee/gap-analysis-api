import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field


# ---------------------------------------------------------------------------
# API request / response schemas
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1, description="The search query to analyse")
    url: HttpUrl = Field(..., description="The page URL to compare against the AIO")


class AnalyzeResponse(BaseModel):
    id: uuid.UUID
    status: str
    query: str
    url: str
    timestamp: datetime
    ai_overview_text: Optional[str] = None
    page_text: Optional[str] = None
    analysis_result: Optional["GapAnalysisResult"] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Structured LLM output schema (enforced by Instructor)
# ---------------------------------------------------------------------------

class Fact(BaseModel):
    statement: str = Field(..., description="A factual claim extracted from the AIO")
    present_in_page: bool = Field(
        ..., description="Whether this fact is covered by the page content"
    )


class Gap(BaseModel):
    topic: str = Field(..., description="The topic or theme that is missing from the page")
    description: str = Field(..., description="Why this is a gap and what the AIO says about it")


class Recommendation(BaseModel):
    action: str = Field(..., description="A concrete action to address the gap")
    priority: str = Field(
        "medium",
        description="Priority level: high | medium | low",
        pattern="^(high|medium|low)$",
    )


class GapAnalysisResult(BaseModel):
    facts: List[Fact] = Field(default_factory=list, description="Facts extracted from the AIO")
    gaps: List[Gap] = Field(default_factory=list, description="Topics in AIO missing from the page")
    recommendations: List[Recommendation] = Field(
        default_factory=list, description="Actions to close the gaps"
    )
    summary: str = Field("", description="One-paragraph overall summary of the gap analysis")


# Keep the forward-ref resolved
AnalyzeResponse.model_rebuild()
