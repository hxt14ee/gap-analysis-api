import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, HttpUrl, Field


class AnalyzeRequest(BaseModel):
    query: str = Field(..., min_length=1)
    url: HttpUrl


class Fact(BaseModel):
    statement: str
    present_in_page: bool


class Gap(BaseModel):
    topic: str
    description: str


class Recommendation(BaseModel):
    action: str
    priority: str = Field("medium", pattern="^(high|medium|low)$")


class GapAnalysisResult(BaseModel):
    facts: List[Fact] = Field(default_factory=list)
    gaps: List[Gap] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    summary: str = ""


class AnalyzeResponse(BaseModel):
    id: uuid.UUID
    status: str
    query: str
    url: str
    timestamp: datetime
    ai_overview_text: Optional[str] = None
    page_text: Optional[str] = None
    analysis_result: Optional[GapAnalysisResult] = None

    model_config = {"from_attributes": True}
