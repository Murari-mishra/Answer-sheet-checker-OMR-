from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)

    template_version: Mapped[str] = mapped_column(String, nullable=False)

    # list of {"question": 1, "correct_option": "B"}
    answer_key: Mapped[list] = mapped_column(JSON, nullable=False)

    # scoring policy, e.g.
    # {"points_correct": 1, "points_blank": 0, "points_multiple": 0,
    #  "negative_marking": 0, "rounding": "none"}
    scoring_policy: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<Exam id={self.id} title={self.title!r}>"
