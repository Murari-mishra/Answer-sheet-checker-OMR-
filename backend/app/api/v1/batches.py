from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.batch import Batch
from app.models.batch_item import BatchItem
from app.models.exam import Exam
from app.schemas.batch import BatchItemOut, BatchOut, ManualItemCreate, ReviewSubmit
from app.services.exports import build_results_csv
from app.services.jobs import enqueue_item
from app.services.scoring import score_answers
from app.services.storage import upload_bytes
from app.services.uploads import UploadValidationError, quick_validate_upload

router = APIRouter(tags=["batches"])


def safe_upload_filename(filename: str | None) -> str | None:
    if not filename:
        return None
    return filename.replace("\\", "/").rsplit("/", 1)[-1] or None


def get_exam_or_404(exam_id: int, db: Session) -> Exam:
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    return exam


def get_batch_or_404(batch_id: int, db: Session) -> Batch:
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="Batch not found")
    return batch


def get_item_or_404(batch_id: int, item_id: int, db: Session) -> BatchItem:
    item = (
        db.query(BatchItem)
        .filter(BatchItem.batch_id == batch_id, BatchItem.id == item_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Batch item not found")
    return item


@router.post("/exams/{exam_id}/batches", response_model=BatchOut)
def create_batch(exam_id: int, db: Session = Depends(get_db)):
    get_exam_or_404(exam_id, db)
    batch = Batch(exam_id=exam_id, status="open")
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


@router.get("/batches/{batch_id}", response_model=BatchOut)
def get_batch(batch_id: int, db: Session = Depends(get_db)):
    return get_batch_or_404(batch_id, db)


@router.get("/batches/{batch_id}/items", response_model=list[BatchItemOut])
def list_batch_items(batch_id: int, db: Session = Depends(get_db)):
    get_batch_or_404(batch_id, db)
    return db.query(BatchItem).filter(BatchItem.batch_id == batch_id).order_by(BatchItem.id).all()


@router.get("/batches/{batch_id}/items/{item_id}", response_model=BatchItemOut)
def get_batch_item(batch_id: int, item_id: int, db: Session = Depends(get_db)):
    return get_item_or_404(batch_id, item_id, db)


@router.post("/batches/{batch_id}/items/manual", response_model=BatchItemOut)
def submit_manual_item(batch_id: int, payload: ManualItemCreate, db: Session = Depends(get_db)):
    batch = get_batch_or_404(batch_id, db)
    exam = batch.exam

    score = score_answers(
        confirmed_answers=payload.confirmed_answers,
        answer_key=exam.answer_key,
        scoring_policy=exam.scoring_policy,
    )

    item = BatchItem(
        batch_id=batch_id,
        student_identifier=payload.student_identifier,
        confirmed_answers=payload.confirmed_answers,
        status="completed",
        score=score,
    )
    db.add(item)
    batch.total_count += 1
    batch.succeeded_count += 1
    db.commit()
    db.refresh(item)
    return item


@router.post("/batches/{batch_id}/items", response_model=BatchItemOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_sheet_item(batch_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    batch = get_batch_or_404(batch_id, db)

    raw_bytes = await file.read()

    try:
        quick_validate_upload(raw_bytes, file.content_type)
    except UploadValidationError as e:
        item = BatchItem(
            batch_id=batch_id,
            filename=safe_upload_filename(file.filename),
            status="failed",
            error_code=e.code,
            error_message=str(e),
            confirmed_answers={},
        )
        db.add(item)
        batch.total_count += 1
        batch.failed_count += 1
        db.commit()
        db.refresh(item)
        return item

    storage_key = upload_bytes(raw_bytes, prefix="raw", extension="jpg", content_type=file.content_type)

    item = BatchItem(
        batch_id=batch_id,
        filename=safe_upload_filename(file.filename),
        storage_key=storage_key,
        status="queued",
        stage=None,
        progress=0,
        confirmed_answers={},
    )
    db.add(item)
    batch.total_count += 1  # counted exactly once, here, regardless of later retries
    db.commit()
    db.refresh(item)

    await enqueue_item(item.id)
    return item


@router.post(
    "/batches/{batch_id}/items/{item_id}/retry",
    response_model=BatchItemOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_item(
    batch_id: int, item_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    get_batch_or_404(batch_id, db)
    item = get_item_or_404(batch_id, item_id, db)

    if item.status != "failed":
        raise HTTPException(
            status_code=409, detail=f"Only failed items can be retried (status is {item.status!r})"
        )

    raw_bytes = await file.read()

    try:
        quick_validate_upload(raw_bytes, file.content_type)
    except UploadValidationError as e:
        item.error_code = e.code
        item.error_message = str(e)
        db.commit()
        db.refresh(item)
        return item  # still failed - stays in the failed bucket, no re-enqueue

    storage_key = upload_bytes(raw_bytes, prefix="raw", extension="jpg", content_type=file.content_type)

    batch = item.batch
    # remove from the failed bucket now that it's queued again; process_item_sync
    # will reclassify into completed/needs_review/failed once it actually resolves
    batch.failed_count -= 1

    item.storage_key = storage_key
    item.filename = safe_upload_filename(file.filename)
    item.status = "queued"
    item.stage = None
    item.progress = 0
    item.error_code = None
    item.error_message = None
    item.attempt += 1
    db.commit()
    db.refresh(item)

    await enqueue_item(item.id)
    return item


@router.post("/batches/{batch_id}/items/{item_id}/review", response_model=BatchItemOut)
def review_item(batch_id: int, item_id: int, payload: ReviewSubmit, db: Session = Depends(get_db)):
    batch = get_batch_or_404(batch_id, db)
    item = get_item_or_404(batch_id, item_id, db)
    exam = batch.exam

    if item.status not in ("needs_review", "completed"):
        raise HTTPException(
            status_code=409,
            detail=f"Item status is {item.status!r}; only needs_review or completed items can be reviewed",
        )

    was_review = item.status == "needs_review"

    item.confirmed_answers = payload.confirmed_answers
    if payload.student_identifier is not None:
        roll_number = payload.student_identifier.strip()
        if len(roll_number) != 5 or not roll_number.isdigit():
            raise HTTPException(
                status_code=422,
                detail="student_identifier must contain exactly 5 digits",
            )
        item.student_identifier = roll_number
    item.score = score_answers(payload.confirmed_answers, exam.answer_key, exam.scoring_policy)
    item.status = "completed"

    if was_review:
        batch.review_count -= 1
        batch.succeeded_count += 1

    db.commit()
    db.refresh(item)
    return item


@router.get("/batches/{batch_id}/results.csv")
def export_results_csv(batch_id: int, db: Session = Depends(get_db)):
    batch = get_batch_or_404(batch_id, db)
    exam = batch.exam
    items = db.query(BatchItem).filter(BatchItem.batch_id == batch_id).order_by(BatchItem.id).all()

    question_numbers = [entry["question"] for entry in exam.answer_key]
    csv_text = build_results_csv(items, question_numbers)

    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=batch_{batch_id}_results.csv"},
    )
