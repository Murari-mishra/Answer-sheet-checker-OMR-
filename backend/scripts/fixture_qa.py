import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.alignment import align_sheet
from app.services.bubble_reading import read_roll_number, read_sheet
from app.services.scoring import score_answers

DEFAULT_FIXTURES = BACKEND_DIR / "tests" / "fixtures" / "sheets"
DEFAULT_MANIFEST = DEFAULT_FIXTURES / "expected.json"
DEFAULT_REPORT = BACKEND_DIR / "generated" / "fixture_qa_report.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as manifest_file:
        return json.load(manifest_file)


def evaluate_fixture(image_path: Path, manifest: dict) -> dict:
    image_expectation = manifest.get("images", {}).get(image_path.name, {})
    result = {
        "image": image_path.name,
        "image_path": str(image_path.resolve()),
        "pipeline_status": "failed",
        "failed_stage": "decode",
        "error": None,
        "expected_roll_number": image_expectation.get("expected_roll_number"),
        "detected_roll_number": None,
        "roll_number_status": "unverified",
        "roll_uncertain": None,
        "questions_read": 0,
        "answer_review_required": None,
        "score": None,
        "expected_score": image_expectation.get("expected_score"),
        "score_status": "not_configured",
    }

    try:
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError("OpenCV could not decode this image")

        result["failed_stage"] = "alignment"
        warped, template = align_sheet(image, manifest.get("template_version", "ambition-guru-v1"))

        result["failed_stage"] = "answer_reading"
        answers = read_sheet(warped, template)
        result["questions_read"] = len(answers["answers"])
        result["answer_review_required"] = answers["needs_review"]

        result["failed_stage"] = "roll_reading"
        roll = read_roll_number(warped, template)
        if roll is not None:
            result["detected_roll_number"] = roll["roll_number"]
            result["roll_uncertain"] = roll["uncertain"]
            expected_roll = result["expected_roll_number"]
            if expected_roll is not None:
                result["roll_number_status"] = (
                    "pass"
                    if not roll["uncertain"] and roll["roll_number"] == expected_roll
                    else "fail"
                )

        result["failed_stage"] = "scoring"
        answer_key = manifest.get("answer_key")
        if answer_key:
            if answers["needs_review"] or (roll is not None and roll["uncertain"]):
                result["score_status"] = "not_scored_needs_review"
            else:
                result["score"] = score_answers(
                    answers["answers"],
                    answer_key,
                    manifest.get("scoring_policy", {}),
                )
                expected_score = result["expected_score"]
                result["score_status"] = (
                    "unverified"
                    if expected_score is None
                    else "pass"
                    if result["score"] == expected_score
                    else "fail"
                )

        result["pipeline_status"] = "passed"
        result["failed_stage"] = None
        if result["roll_number_status"] == "unverified" and roll is None:
            result["roll_number_status"] = "not_available"
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        if result["expected_roll_number"] is not None:
            result["roll_number_status"] = "not_checked"

    return result


def build_report(fixtures_dir: Path, manifest_path: Path) -> dict:
    manifest = load_manifest(manifest_path)
    files = sorted(
        path for path in fixtures_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    results = [evaluate_fixture(path, manifest) for path in files]

    summary = {
        "total_images": len(results),
        "pipeline_passed": sum(row["pipeline_status"] == "passed" for row in results),
        "pipeline_failed": sum(row["pipeline_status"] == "failed" for row in results),
        "roll_labeled": sum(row["expected_roll_number"] is not None for row in results),
        "roll_passed": sum(row["roll_number_status"] == "pass" for row in results),
        "roll_failed": sum(row["roll_number_status"] == "fail" for row in results),
        "roll_unverified": sum(row["roll_number_status"] == "unverified" for row in results),
        "score_calculated": sum(row["score"] is not None for row in results),
        "score_unverified": sum(row["score_status"] == "unverified" for row in results),
        "score_failed": sum(row["score_status"] == "fail" for row in results),
        "review_required": sum(
            row["answer_review_required"] is True or row["roll_uncertain"] is True
            for row in results
        ),
    }
    failed = summary["pipeline_failed"] + summary["roll_failed"] + summary["score_failed"]
    unverified = summary["roll_unverified"] + summary["score_unverified"]
    report_status = "FAIL" if failed else "INCOMPLETE" if unverified else "PASS"

    return {
        "suite": "omr-fixture-qa",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixtures_directory": str(fixtures_dir.resolve()),
        "manifest_path": str(manifest_path.resolve()),
        "status": report_status,
        "summary": summary,
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OMR pipeline against image fixtures.")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    report = build_report(args.fixtures, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2)
        report_file.write("\n")

    print(json.dumps({"status": report["status"], **report["summary"], "report": str(args.output)}))
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
