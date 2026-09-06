from types import SimpleNamespace

from app.services.exports import build_results_csv


def make_item(id_, student_id, status, score, answers):
    return SimpleNamespace(
        id=id_, student_identifier=student_id, status=status, score=score, confirmed_answers=answers
    )


def test_basic_row_output():
    items = [make_item(1, "STU-001", "completed", 1.75, {"1": "B", "2": "X"})]
    csv_text = build_results_csv(items, [1, 2])
    lines = csv_text.strip().splitlines()
    assert lines[0] == "item_id,student_identifier,status,score,q1,q2"
    assert lines[1] == "1,STU-001,completed,1.75,B,X"


def test_formula_injection_prefixes_are_neutralized():
    items = [make_item(1, "=SUM(A1)", "completed", 1, {"1": "+HYPERLINK(1)"})]
    csv_text = build_results_csv(items, [1])
    lines = csv_text.strip().splitlines()
    assert lines[1].startswith("1,'=SUM(A1)")
    assert "'+HYPERLINK(1)" in lines[1]


def test_at_and_minus_prefixes_are_neutralized():
    items = [make_item(1, "@user", "completed", 1, {"1": "-1"})]
    csv_text = build_results_csv(items, [1])
    lines = csv_text.strip().splitlines()
    assert "'@user" in lines[1]
    assert "'-1" in lines[1]


def test_blank_and_none_values_render_as_empty():
    items = [make_item(1, None, "completed", None, {"1": ""})]
    csv_text = build_results_csv(items, [1])
    lines = csv_text.strip().splitlines()
    assert lines[1] == "1,,completed,,"
