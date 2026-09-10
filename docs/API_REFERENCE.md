# Ambition Guru OMR - REST API Specification

This document provides complete documentation of all HTTP endpoints exposed by the Ambition Guru OMR backend (`/api/v1`).

---

## General Configuration

- **Default Base URL**: `http://127.0.0.1:8000`
- **Prefix**: `/api/v1`
- **Default Content-Type**: `application/json` (except file upload endpoints which require `multipart/form-data`)
- **CORS Allowed Origins**: `http://localhost:5173`

---

## 📑 Endpoints Index

1. [Health Check](#1-health-check)
2. [Exam Management](#2-exam-management)
   - [Create Exam](#create-exam)
   - [List Exams](#list-exams)
   - [Get Exam Details](#get-exam-details)
   - [Delete Exam](#delete-exam)
3. [Batch Management](#3-batch-management)
   - [Create Batch](#create-batch)
   - [Get Batch Summary](#get-batch-summary)
   - [List Batch Items](#list-batch-items)
   - [Get Batch Item Details](#get-batch-item-details)
4. [Sheet Ingestion & Processing](#4-sheet-ingestion--processing)
   - [Upload Sheet Image (Async)](#upload-sheet-image-async)
   - [Retry Failed Sheet](#retry-failed-sheet)
   - [Submit Manual Answers](#submit-manual-answers)
5. [Review & Correction](#5-review--correction)
   - [Submit Proctor Review](#submit-proctor-review)
6. [Results & Export](#6-results--export)
   - [Export Results CSV](#export-results-csv)

---

## 1. Health Check

### Check Health Status
```http
GET /health
```

#### Response (`200 OK`)
```json
{
  "status": "ok"
}
```

---

## 2. Exam Management

### Create Exam
Creates an exam definition containing the master answer key, scoring policy, and template version.

```http
POST /api/v1/exams
Content-Type: application/json
```

#### Request Body
```json
{
  "title": "Ambition Guru Medical Mock 2026",
  "template_version": "ambition-guru-v1",
  "answer_key": [
    { "question": 1, "correct_option": "A" },
    { "question": 2, "correct_option": "C" },
    { "question": 3, "correct_option": "B" },
    { "question": 4, "correct_option": "D" }
  ],
  "scoring_policy": {
    "points_correct": 1.0,
    "points_incorrect": 0.0,
    "points_blank": 0.0,
    "points_multiple": 0.0,
    "negative_marking": 0.25,
    "rounding": "0.25"
  }
}
```

#### Response (`200 OK`)
```json
{
  "id": 1,
  "title": "Ambition Guru Medical Mock 2026",
  "template_version": "ambition-guru-v1",
  "answer_key": [
    { "question": 1, "correct_option": "A" },
    { "question": 2, "correct_option": "C" },
    { "question": 3, "correct_option": "B" },
    { "question": 4, "correct_option": "D" }
  ],
  "scoring_policy": {
    "points_correct": 1.0,
    "points_incorrect": 0.0,
    "points_blank": 0.0,
    "points_multiple": 0.0,
    "negative_marking": 0.25,
    "rounding": "0.25"
  },
  "created_at": "2026-09-10T08:30:00Z"
}
```

---

### List Exams
Retrieves all registered exams ordered by ID.

```http
GET /api/v1/exams
```

#### Response (`200 OK`)
```json
[
  {
    "id": 1,
    "title": "Ambition Guru Medical Mock 2026",
    "template_version": "ambition-guru-v1",
    "answer_key": [...],
    "scoring_policy": {...},
    "created_at": "2026-09-10T08:30:00Z"
  }
]
```

---

### Get Exam Details
```http
GET /api/v1/exams/{exam_id}
```

#### Response (`200 OK`)
Returns the `ExamOut` schema for the specified exam ID.

#### Error Responses
- `404 Not Found`: `{"detail": "Exam not found"}`

---

### Delete Exam
Removes an exam record and all its associated batches (via cascade).

```http
DELETE /api/v1/exams/{exam_id}
```

#### Response (`204 No Content`)

---

## 3. Batch Management

### Create Batch
Initializes a new batch container to hold scanned answer sheet items.

```http
POST /api/v1/exams/{exam_id}/batches
```

#### Response (`200 OK`)
```json
{
  "id": 101,
  "exam_id": 1,
  "status": "open",
  "total_count": 0,
  "succeeded_count": 0,
  "review_count": 0,
  "failed_count": 0,
  "created_at": "2026-09-10T08:35:00Z"
}
```

---

### Get Batch Summary
Fetches current batch statistics and counters.

```http
GET /api/v1/batches/{batch_id}
```

#### Response (`200 OK`)
```json
{
  "id": 101,
  "exam_id": 1,
  "status": "open",
  "total_count": 50,
  "succeeded_count": 46,
  "review_count": 3,
  "failed_count": 1,
  "created_at": "2026-09-10T08:35:00Z"
}
```

---

### List Batch Items
Lists all sheet records within a specific batch.

```http
GET /api/v1/batches/{batch_id}/items
```

#### Response (`200 OK`)
```json
[
  {
    "id": 501,
    "batch_id": 101,
    "status": "completed",
    "stage": null,
    "progress": 100,
    "attempt": 1,
    "error_code": null,
    "error_message": null,
    "student_identifier": "92518",
    "raw_answers": { "1": "A", "2": "C" },
    "confirmed_answers": { "1": "A", "2": "C" },
    "score": 2.0,
    "created_at": "2026-09-10T08:36:12Z"
  }
]
```

---

### Get Batch Item Details
```http
GET /api/v1/batches/{batch_id}/items/{item_id}
```

#### Response (`200 OK`)
Returns single `BatchItemOut` model.

---

## 4. Sheet Ingestion & Processing

### Upload Sheet Image (Async)
Uploads an OMR image for processing. Performs validation and stores to MinIO before enqueueing into the background pipeline.

```http
POST /api/v1/batches/{batch_id}/items
Content-Type: multipart/form-data
```

#### Form Parameters
- `file`: Binary file data (`image/jpeg` or `image/png`, max 10MB).

#### Response (`202 Accepted`)
```json
{
  "id": 502,
  "batch_id": 101,
  "status": "queued",
  "stage": null,
  "progress": 0,
  "attempt": 1,
  "error_code": null,
  "error_message": null,
  "student_identifier": null,
  "raw_answers": null,
  "confirmed_answers": {},
  "score": null,
  "created_at": "2026-09-10T08:37:00Z"
}
```

*(Note: If initial validation fails immediately, e.g. file size exceeded or unsupported format, the endpoint returns `200 OK` with `status: "failed"` and corresponding `error_code`).*

---

### Retry Failed Sheet
Replaces the image of a previously failed item and re-enqueues it for background processing. Only items with `status == "failed"` can be retried.

```http
POST /api/v1/batches/{batch_id}/items/{item_id}/retry
Content-Type: multipart/form-data
```

#### Form Parameters
- `file`: Replacement image file (`image/jpeg` or `image/png`).

#### Response (`202 Accepted`)
```json
{
  "id": 502,
  "batch_id": 101,
  "status": "queued",
  "stage": null,
  "progress": 0,
  "attempt": 2,
  "error_code": null,
  "error_message": null,
  "student_identifier": null,
  "raw_answers": null,
  "confirmed_answers": {},
  "score": null,
  "created_at": "2026-09-10T08:37:00Z"
}
```

#### Error Responses
- `409 Conflict`: `{"detail": "Only failed items can be retried (status is 'completed')"}`

---

### Submit Manual Answers
Inserts a batch item with answers confirmed directly without image processing.

```http
POST /api/v1/batches/{batch_id}/items/manual
Content-Type: application/json
```

#### Request Body
```json
{
  "student_identifier": "84721",
  "confirmed_answers": {
    "1": "A",
    "2": "B",
    "3": "C",
    "4": "D"
  }
}
```

#### Response (`200 OK`)
Returns `BatchItemOut` with `status: "completed"` and calculated `score`.

---

## 5. Review & Correction

### Submit Proctor Review
Used by exam administrators to verify or correct answers and roll numbers for sheets flagged as `needs_review` (or to adjust `completed` sheets). Automatically recalculates the final score and marks the item as `completed`.

```http
POST /api/v1/batches/{batch_id}/items/{item_id}/review
Content-Type: application/json
```

#### Request Body
```json
{
  "student_identifier": "92518",
  "confirmed_answers": {
    "1": "A",
    "2": "B",
    "3": "C",
    "4": "A"
  }
}
```

#### Validation Constraints
- `student_identifier` (optional): If provided, must be **exactly 5 digits**.
- Item status must be either `needs_review` or `completed`.

#### Response (`200 OK`)
```json
{
  "id": 502,
  "batch_id": 101,
  "status": "completed",
  "stage": null,
  "progress": 100,
  "attempt": 1,
  "error_code": null,
  "error_message": null,
  "student_identifier": "92518",
  "raw_answers": { "1": "A", "2": "B", "3": "A,C", "4": "A" },
  "confirmed_answers": { "1": "A", "2": "B", "3": "C", "4": "A" },
  "score": 3.75,
  "created_at": "2026-09-10T08:37:00Z"
}
```

---

## 6. Results & Export

### Export Results CSV
Streams a CSV file containing all items in the batch with their scores and confirmed answers for every question in the answer key. Formulas are sanitized to prevent spreadsheet injection.

```http
GET /api/v1/batches/{batch_id}/results.csv
```

#### Response Headers
```http
Content-Type: text/csv; charset=utf-8
Content-Disposition: attachment; filename=batch_101_results.csv
```

#### Sample CSV Output
```csv
item_id,student_identifier,status,score,q1,q2,q3,q4
501,92518,completed,3.75,A,B,C,A
502,90695,completed,4.0,A,C,B,D
503,11402,needs_review,,A,B,,D
```

---

## 7. Error Code Catalogue

When an item fails during validation, alignment, or execution, the `error_code` field contains one of the following deterministic codes:

| Error Code | Stage | Cause | Solution |
|---|---|---|---|
| `unsupported_content_type` | Ingestion | File is not JPEG or PNG | Upload `.jpg` or `.png` format |
| `empty_file` | Ingestion | Zero-byte payload uploaded | Reselect image and upload again |
| `file_too_large` | Ingestion | Payload exceeds 10 MB | Compress image below 10 MB |
| `invalid_image` | Validating | OpenCV unable to decode image buffer | Check file for corruption |
| `image_too_small` | Validating | Height or width < 200 pixels | Upload scan of at least 300 DPI |
| `image_too_large` | Validating | Height or width > 6000 pixels | Downscale image below 6000px |
| `markers_not_found` | Aligning | Failed to find 4 bullseye markers | Ensure all 4 corner markers are visible |
| `markers_ambiguous` | Aligning | Multiple marker clusters in same quadrant | Remove dark stamps near sheet edges |
| `alignment_failed` | Aligning | Warped sheet deviates > 25px from template | Straighten sheet scan; avoid extreme folds |
| `internal_error` | Pipeline | Unhandled runtime exception | Check backend logs for trace |
