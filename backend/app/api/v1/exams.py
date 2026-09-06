from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.exam import Exam
from app.schemas.exam import ExamCreate, ExamOut

router = APIRouter(prefix="/exams", tags=["exams"])


@router.post("", response_model=ExamOut)
def create_exam(payload: ExamCreate, db: Session = Depends(get_db)):
    exam = Exam(
        title=payload.title,
        template_version=payload.template_version,
        answer_key=[entry.model_dump() for entry in payload.answer_key],
        scoring_policy=payload.scoring_policy.model_dump(),
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


@router.get("", response_model=list[ExamOut])
def list_exams(db: Session = Depends(get_db)):
    return db.query(Exam).order_by(Exam.id).all()


@router.get("/{exam_id}", response_model=ExamOut)
def get_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if exam is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


@router.delete("/{exam_id}", status_code=204)
def delete_exam(exam_id: int, db: Session = Depends(get_db)):
    exam = get_exam(exam_id, db)  # reuses existing 404 handling
    db.delete(exam)
    db.commit()
