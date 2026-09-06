class ScoringError(Exception):
    pass


def _classify(selected: str) -> str:
    if selected == "" or selected is None:
        return "blank"
    if "," in selected:
        return "multiple"
    return "single"


def score_answers(
    confirmed_answers: dict[str, str],
    answer_key: list[dict],
    scoring_policy: dict,
) -> float:
    """
    confirmed_answers: {"1": "B", "2": "", "3": "A,C"}
    answer_key: [{"question": 1, "correct_option": "B"}, ...]
    scoring_policy: {
        "points_correct": 1,
        "points_incorrect": 0,
        "points_blank": 0,
        "points_multiple": 0,
        "negative_marking": 0,   # positive number subtracted per wrong answer
        "rounding": "none",      # "none" | "0.25" | "0.5" | "1"
    }
    """
    points_correct = scoring_policy.get("points_correct", 1)
    points_incorrect = scoring_policy.get("points_incorrect", 0)
    points_blank = scoring_policy.get("points_blank", 0)
    points_multiple = scoring_policy.get("points_multiple", 0)
    negative_marking = scoring_policy.get("negative_marking", 0)
    rounding = scoring_policy.get("rounding", "none")

    total = 0.0

    for entry in answer_key:
        q_num = str(entry["question"])
        correct_option = entry["correct_option"]
        selected = confirmed_answers.get(q_num, "")

        kind = _classify(selected)

        if kind == "blank":
            total += points_blank
        elif kind == "multiple":
            total += points_multiple
        elif selected == correct_option:
            total += points_correct
        else:
            total += points_incorrect - negative_marking

    return _apply_rounding(total, rounding)


def _apply_rounding(value: float, rounding: str) -> float:
    if rounding == "none":
        return value
    step = float(rounding)
    return round(value / step) * step
