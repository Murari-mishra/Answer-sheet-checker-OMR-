from datetime import datetime

from pydantic import BaseModel


class AnswerKeyEntry(BaseModel):
    question: int
    correct_option: str


class ScoringPolicy(BaseModel):
    points_correct: float = 1
    points_incorrect: float = 0
    points_blank: float = 0
    points_multiple: float = 0
    negative_marking: float = 0
    rounding: str = "none"


class ExamCreate(BaseModel):
    title: str
    template_version: str
    answer_key: list[AnswerKeyEntry]
    scoring_policy: ScoringPolicy


class ExamOut(BaseModel):
    id: int
    title: str
    template_version: str
    answer_key: list[AnswerKeyEntry]
    scoring_policy: ScoringPolicy
    created_at: datetime

    model_config = {"from_attributes": True}
