from datetime import datetime

from pydantic import BaseModel


class BatchCreate(BaseModel):
    pass


class BatchOut(BaseModel):
    id: int
    exam_id: int
    status: str
    total_count: int
    succeeded_count: int
    review_count: int
    failed_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ManualItemCreate(BaseModel):
    student_identifier: str
    confirmed_answers: dict[str, str]


class ReviewSubmit(BaseModel):
    confirmed_answers: dict[str, str]
    student_identifier: str | None = None


class BatchItemOut(BaseModel):
    id: int
    batch_id: int
    filename: str | None
    status: str
    stage: str | None
    progress: int
    attempt: int
    error_code: str | None
    error_message: str | None
    student_identifier: str | None
    raw_answers: dict | None
    confirmed_answers: dict
    score: float | None
    created_at: datetime

    model_config = {"from_attributes": True}
