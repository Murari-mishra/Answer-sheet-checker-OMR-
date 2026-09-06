from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BatchItem(Base):
    __tablename__ = "batch_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("batches.id"), nullable=False)

    filename: Mapped[str | None] = mapped_column(String, nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String, nullable=True)

    # uploading | queued | processing | needs_review | completed | failed
    status: Mapped[str] = mapped_column(String, default="completed")
    stage: Mapped[str | None] = mapped_column(String, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=100)

    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    student_identifier: Mapped[str | None] = mapped_column(String, nullable=True)

    raw_answers: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confirmed_answers: Mapped[dict | None] = mapped_column(JSON, nullable=False)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)

    attempt: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    batch = relationship("Batch", back_populates="items")

    def __repr__(self) -> str:
        return f"<BatchItem id={self.id} batch_id={self.batch_id} status={self.status!r}>"
