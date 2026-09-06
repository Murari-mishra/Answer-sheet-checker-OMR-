import csv
import io

from app.models.batch_item import BatchItem

DANGEROUS_PREFIXES = ("=", "+", "-", "@")


def _sanitize_cell(value) -> str:
    text = "" if value is None else str(value)
    if text.startswith(DANGEROUS_PREFIXES):
        return "'" + text  # neutralize formula interpretation
    return text


def build_results_csv(items: list[BatchItem], question_numbers: list[int]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    header = ["item_id", "student_identifier", "status", "score"] + [
        f"q{n}" for n in question_numbers
    ]
    writer.writerow(header)

    for item in items:
        answers = item.confirmed_answers or {}
        row = [
            item.id,
            _sanitize_cell(item.student_identifier),
            item.status,
            item.score if item.score is not None else "",
        ]
        for q in question_numbers:
            row.append(_sanitize_cell(answers.get(str(q), "")))
        writer.writerow(row)

    return output.getvalue()
