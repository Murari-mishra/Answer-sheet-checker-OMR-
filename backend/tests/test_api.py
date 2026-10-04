import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def create_exam(client: TestClient) -> int:
    response = client.post(
        "/api/v1/exams",
        json={
            "title": "API test exam",
            "template_version": "test-v1",
            "answer_key": [
                {"question": 1, "correct_option": "A"},
                {"question": 2, "correct_option": "C"},
            ],
            "scoring_policy": {
                "points_correct": 1,
                "points_incorrect": 0,
                "points_blank": 0,
                "points_multiple": 0,
                "negative_marking": 0.25,
                "rounding": "none",
            },
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


def test_health_endpoint(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_exam_create_list_get_and_missing_exam(client: TestClient):
    exam_id = create_exam(client)

    listed = client.get("/api/v1/exams")
    fetched = client.get(f"/api/v1/exams/{exam_id}")
    missing = client.get("/api/v1/exams/9999")

    assert listed.status_code == 200
    assert [exam["id"] for exam in listed.json()] == [exam_id]
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "API test exam"
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Exam not found"


def test_manual_submission_scores_item_updates_batch_and_exports_csv(client: TestClient):
    exam_id = create_exam(client)
    batch_response = client.post(f"/api/v1/exams/{exam_id}/batches")
    assert batch_response.status_code == 200
    batch_id = batch_response.json()["id"]

    item_response = client.post(
        f"/api/v1/batches/{batch_id}/items/manual",
        json={
            "student_identifier": "12345",
            "confirmed_answers": {"1": "A", "2": "B"},
        },
    )
    assert item_response.status_code == 200
    item = item_response.json()
    assert item["status"] == "completed"
    assert item["score"] == 0.75

    batch = client.get(f"/api/v1/batches/{batch_id}").json()
    assert batch["total_count"] == 1
    assert batch["succeeded_count"] == 1
    assert batch["failed_count"] == 0

    items = client.get(f"/api/v1/batches/{batch_id}/items")
    assert items.status_code == 200
    assert [entry["id"] for entry in items.json()] == [item["id"]]

    csv_response = client.get(f"/api/v1/batches/{batch_id}/results.csv")
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert "12345,completed,0.75,A,B" in csv_response.text


def test_upload_rejects_unsupported_content_type_and_counts_failure(client: TestClient):
    exam_id = create_exam(client)
    batch_id = client.post(f"/api/v1/exams/{exam_id}/batches").json()["id"]

    response = client.post(
        f"/api/v1/batches/{batch_id}/items",
        files={"file": ("answer.pdf", b"not an image", "application/pdf")},
    )

    assert response.status_code == 202
    item = response.json()
    assert item["status"] == "failed"
    assert item["error_code"] == "unsupported_content_type"
    assert item["filename"] == "answer.pdf"

    batch = client.get(f"/api/v1/batches/{batch_id}").json()
    assert batch["total_count"] == 1
    assert batch["failed_count"] == 1
    assert batch["succeeded_count"] == 0