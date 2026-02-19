import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class AnalysisRequest(Base):
    __tablename__ = "analysis_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="pending")
    ai_overview_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    analysis_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
