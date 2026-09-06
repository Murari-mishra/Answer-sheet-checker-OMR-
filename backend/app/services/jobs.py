import asyncio
import logging

from app.db.session import SessionLocal
from app.models.batch_item import BatchItem
from app.services.alignment import AlignmentError, align_sheet
from app.services.bubble_reading import read_roll_number, read_sheet
from app.services.scoring import score_answers
from app.services.storage import download_bytes
from app.services.uploads import UploadValidationError, decode_and_validate_dimensions

logger = logging.getLogger("omr.jobs")

JOB_QUEUE: "asyncio.Queue[int]" = asyncio.Queue(maxsize=200)

_COUNTED_STATUSES = {"failed", "needs_review", "completed"}


def _reclassify(batch, item, new_status: str) -> None:
    """Move an item's batch-aggregate bucket from its old status to a new
    one, decrementing the old bucket only if it was actually counted there."""
    old_status = item.status
    if old_status in _COUNTED_STATUSES:
        if old_status == "failed":
            batch.failed_count -= 1
        elif old_status == "needs_review":
            batch.review_count -= 1
        elif old_status == "completed":
            batch.succeeded_count -= 1

    if new_status == "failed":
        batch.failed_count += 1
    elif new_status == "needs_review":
        batch.review_count += 1
    elif new_status == "completed":
        batch.succeeded_count += 1

    item.status = new_status


async def enqueue_item(item_id: int) -> None:
    await JOB_QUEUE.put(item_id)


def _set_stage(db, item, stage: str, progress: int) -> None:
    item.stage = stage
    item.progress = progress
    db.commit()


def _fail_item(db, batch, item, code: str, message: str) -> None:
    _reclassify(batch, item, "failed")
    item.error_code = code
    item.error_message = message
    item.stage = None
    item.progress = 100
    db.commit()


def process_item_sync(item_id: int) -> None:
    """Runs in a worker thread via asyncio.to_thread - opens its own session."""
    db = SessionLocal()
    try:
        item = db.query(BatchItem).filter(BatchItem.id == item_id).first()
        if item is None:
            logger.warning("job: item %s not found", item_id)
            return
        if item.status not in ("queued", "processing"):
            return  # already handled - avoid double-processing on a re-enqueue

        item.status = "processing"
        item.error_code = None
        item.error_message = None
        _set_stage(db, item, "validating", 10)
        batch = item.batch
        exam = batch.exam

        try:
            raw_bytes = download_bytes(item.storage_key)
            img = decode_and_validate_dimensions(raw_bytes)
        except UploadValidationError as e:
            _fail_item(db, batch, item, e.code, str(e))
            return

        _set_stage(db, item, "aligning", 35)
        try:
            warped, template = align_sheet(img, exam.template_version)
        except AlignmentError as e:
            _fail_item(db, batch, item, e.code, str(e))
            return

        _set_stage(db, item, "thresholding", 50)
        result = read_sheet(warped, template)

        roll = read_roll_number(warped, template)
        if roll is not None:
            item.student_identifier = roll["roll_number"]
            if roll["uncertain"]:
                result["needs_review"] = True  # don't publish an uncertain roll number silently
        _set_stage(db, item, "reading_bubbles", 85)

        item.raw_answers = result["answers"]
        _set_stage(db, item, "scoring", 90)

        if result["needs_review"]:
            _reclassify(batch, item, "needs_review")
        else:
            item.confirmed_answers = result["answers"]
            item.score = score_answers(result["answers"], exam.answer_key, exam.scoring_policy)
            _reclassify(batch, item, "completed")

        _set_stage(db, item, "saving", 95)
        item.progress = 100
        item.stage = None
        db.commit()

    except Exception:
        logger.exception("job: unexpected error processing item %s", item_id)
        db.rollback()
        item = db.query(BatchItem).filter(BatchItem.id == item_id).first()
        if item is not None:
            batch = item.batch
            _reclassify(batch, item, "failed")
            item.error_code = "internal_error"
            item.error_message = "Unexpected error during processing"
            item.stage = None
            db.commit()
    finally:
        db.close()


async def worker_loop() -> None:
    while True:
        item_id = await JOB_QUEUE.get()
        try:
            await asyncio.to_thread(process_item_sync, item_id)
        except Exception:
            logger.exception("worker: failed processing item %s", item_id)
        finally:
            JOB_QUEUE.task_done()


async def requeue_stale_items() -> None:
    """Startup recovery: anything left queued/processing from before a
    crash/restart gets reset and re-enqueued."""
    db = SessionLocal()
    try:
        stale = (
            db.query(BatchItem)
            .filter(BatchItem.status.in_(["queued", "processing"]))
            .all()
        )
        for item in stale:
            item.status = "queued"
            item.stage = None
            item.progress = 0
        db.commit()
        ids = [item.id for item in stale]
    finally:
        db.close()

    for item_id in ids:
        await enqueue_item(item_id)
    if ids:
        logger.info("requeued %d stale item(s) on startup", len(ids))
