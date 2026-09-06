from app.services.scoring import score_answers

ANSWER_KEY = [
    {"question": 1, "correct_option": "B"},
    {"question": 2, "correct_option": "A"},
    {"question": 3, "correct_option": "D"},
    {"question": 4, "correct_option": "C"},
]

POLICY_SIMPLE = {
    "points_correct": 1,
    "points_incorrect": 0,
    "points_blank": 0,
    "points_multiple": 0,
    "negative_marking": 0,
    "rounding": "none",
}


def test_all_correct():
    answers = {"1": "B", "2": "A", "3": "D", "4": "C"}
    assert score_answers(answers, ANSWER_KEY, POLICY_SIMPLE) == 4


def test_mixed_correct_incorrect():
    answers = {"1": "B", "2": "X", "3": "D", "4": "A"}
    assert score_answers(answers, ANSWER_KEY, POLICY_SIMPLE) == 2


def test_blank_scores_blank_points_not_incorrect():
    answers = {"1": "B", "2": "", "3": "D", "4": "C"}
    assert score_answers(answers, ANSWER_KEY, POLICY_SIMPLE) == 3


def test_missing_question_key_treated_as_blank():
    answers = {"1": "B", "3": "D", "4": "C"}  # question 2 missing entirely
    assert score_answers(answers, ANSWER_KEY, POLICY_SIMPLE) == 3


def test_multiple_marks_use_multiple_points_not_incorrect():
    answers = {"1": "B,C", "2": "A", "3": "D", "4": "C"}
    assert score_answers(answers, ANSWER_KEY, POLICY_SIMPLE) == 3


def test_negative_marking_applied_to_wrong_answers_only():
    policy = {**POLICY_SIMPLE, "negative_marking": 0.25}
    answers = {"1": "A", "2": "A", "3": "D", "4": "C"}  # Q1 wrong, rest correct
    assert score_answers(answers, ANSWER_KEY, policy) == 3 - 0.25


def test_negative_marking_not_applied_to_blank():
    policy = {**POLICY_SIMPLE, "negative_marking": 0.25}
    answers = {"1": "", "2": "A", "3": "D", "4": "C"}  # Q1 blank, not wrong
    assert score_answers(answers, ANSWER_KEY, policy) == 3


def test_rounding_to_quarter_point():
    policy = {**POLICY_SIMPLE, "negative_marking": 0.25, "rounding": "0.25"}
    answers = {"1": "X", "2": "X", "3": "D", "4": "C"}  # 2 correct, 2 wrong
    # raw = 2 - 0.5 = 1.5, already on a 0.25 step
    assert score_answers(answers, ANSWER_KEY, policy) == 1.5


def test_all_blank_scores_zero_with_default_policy():
    answers = {"1": "", "2": "", "3": "", "4": ""}
    assert score_answers(answers, ANSWER_KEY, POLICY_SIMPLE) == 0
