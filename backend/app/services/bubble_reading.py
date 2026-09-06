import cv2
import numpy as np

ABSOLUTE_THRESHOLD = 0.25   # fill ratio to count a bubble as "marked" at all
MULTIPLE_THRESHOLD = 0.40   # two+ options at/above this -> multiple marks
MARGIN = 0.15                # top1-top2 gap below this -> ambiguous (only checked
                              # once top1 already clears ABSOLUTE_THRESHOLD, since
                              # blank questions naturally have small gaps too)


def fill_ratio(gray: np.ndarray, x_px: float, y_px: float, radius_px: float) -> float:
    """Fraction of dark pixels (<150 intensity) inside a circular mask at (x, y)."""
    r = int(radius_px)
    x, y = int(x_px), int(y_px)
    y0, y1 = max(0, y - r), min(gray.shape[0], y + r)
    x0, x1 = max(0, x - r), min(gray.shape[1], x + r)
    roi = gray[y0:y1, x0:x1]
    if roi.size == 0:
        return 0.0
    mask = np.zeros(roi.shape, dtype=np.uint8)
    cv2.circle(mask, (x - x0, y - y0), r, 255, -1)
    masked_pixels = roi[mask == 255]
    if masked_pixels.size == 0:
        return 0.0
    return float((masked_pixels < 150).sum() / masked_pixels.size)


def classify_question(fills: dict[str, float]) -> tuple[str, str]:
    """
    fills: {"A": 0.1, "B": 0.82, "C": 0.09, "D": 0.14}
    Returns (outcome, selected) where outcome is one of
    single | blank | multiple | ambiguous, and selected matches the
    confirmed_answers format scoring.py expects ("" / "B" / "A,C").
    """
    sorted_opts = sorted(fills.items(), key=lambda kv: -kv[1])
    top1_opt, top1_fill = sorted_opts[0]
    top2_fill = sorted_opts[1][1]

    if top1_fill < ABSOLUTE_THRESHOLD:
        return "blank", ""

    multiple = [opt for opt, f in fills.items() if f >= MULTIPLE_THRESHOLD]
    if len(multiple) >= 2:
        return "multiple", ",".join(sorted(multiple))

    if (top1_fill - top2_fill) < MARGIN:
        return "ambiguous", top1_opt  # best guess, but caller should route to review

    return "single", top1_opt


def read_sheet(warped_bgr: np.ndarray, template: dict) -> dict:
    """
    Reads every bubble on an already-aligned canonical sheet.
    Returns {
      "answers": {"1": "C", "2": "", "3": "A,C", ...},   # raw detected, scoring-ready format
      "diagnostics": {"1": {"outcome": "single", "fills": {"A":0.1,...}}, ...},
      "needs_review": bool,
    }
    """
    canonical_w = template["canonical_width"]
    canonical_h = template["canonical_height"]
    gray = cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2GRAY)

    by_question: dict[int, dict[str, float]] = {}
    for b in template["bubbles"]:
        x_px = b["x"] * canonical_w
        y_px = b["y"] * canonical_h
        r_px = b["radius"] * canonical_w
        fr = fill_ratio(gray, x_px, y_px, r_px)
        by_question.setdefault(b["question"], {})[b["option"]] = fr

    answers: dict[str, str] = {}
    diagnostics: dict[str, dict] = {}
    needs_review = False

    for q_num in sorted(by_question):
        fills = by_question[q_num]
        outcome, selected = classify_question(fills)
        answers[str(q_num)] = selected
        diagnostics[str(q_num)] = {"outcome": outcome, "fills": fills}
        if outcome in ("multiple", "ambiguous"):
            needs_review = True

    return {"answers": answers, "diagnostics": diagnostics, "needs_review": needs_review}


def read_roll_number(warped_bgr: np.ndarray, template: dict) -> dict | None:
    """
    Reads the roll-number bubble grid, if the template defines one.
    A digit column is structurally identical to a question with 10 options
    instead of 4, so classify_question() is reused as-is with digit labels.
    Returns {"roll_number": str, "uncertain": bool, "diagnostics": [...]}
    or None if this template has no roll_number section.
    """
    if "roll_number" not in template:
        return None

    canonical_w = template["canonical_width"]
    canonical_h = template["canonical_height"]
    gray = cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2GRAY)

    by_position: dict[int, dict[str, float]] = {}
    for b in template["roll_number"]["bubbles"]:
        x_px = b["x"] * canonical_w
        y_px = b["y"] * canonical_h
        r_px = b["radius"] * canonical_w
        fr = fill_ratio(gray, x_px, y_px, r_px)
        by_position.setdefault(b["digit_position"], {})[str(b["digit_value"])] = fr

    digits = []
    uncertain = False
    diagnostics = []
    for pos in sorted(by_position):
        outcome, selected = classify_question(by_position[pos])
        diagnostics.append({"position": pos, "outcome": outcome, "fills": by_position[pos]})
        if outcome != "single":
            uncertain = True
            digits.append("?")
        else:
            digits.append(selected)

    return {"roll_number": "".join(digits), "uncertain": uncertain, "diagnostics": diagnostics}
