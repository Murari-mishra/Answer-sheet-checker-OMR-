import json
from pathlib import Path

import cv2
import numpy as np

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


class AlignmentError(Exception):
    """Raised when markers can't be found or a warped sheet fails verification."""
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def load_template(template_version: str) -> dict:
    path = TEMPLATE_DIR / f"template_{template_version.replace('-', '_')}.json"
    if not path.exists():
        # fall back to direct filename match, e.g. "ambition-guru-v1" -> template_ambition_guru_v1.json
        path = TEMPLATE_DIR / "template_ambition_guru_v1.json"
    with open(path) as f:
        return json.load(f)


def find_registration_markers(gray: np.ndarray) -> dict[str, tuple[float, float]]:
    """
    Detects the 4 bullseye markers by finding clusters of concentric circular
    contours. A real marker produces 3-4 nested rings at nearly the same
    center (fill_ratio > 0.85); noise, text, and bubbles produce at most one
    circular contour, and rarely above ~0.75 fill ratio.
    """
    _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    circles = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < 200 or area > 20000:
            continue
        (x, y), radius = cv2.minEnclosingCircle(c)
        circle_area = np.pi * radius * radius
        if circle_area == 0:
            continue
        if area / circle_area > 0.85:
            circles.append((x, y, radius))

    clusters: list[list[tuple[float, float, float]]] = []
    used = [False] * len(circles)
    for i, (x, y, r) in enumerate(circles):
        if used[i]:
            continue
        cluster = [(x, y, r)]
        used[i] = True
        for j in range(i + 1, len(circles)):
            if used[j]:
                continue
            x2, y2, _ = circles[j]
            if abs(x2 - x) < 15 and abs(y2 - y) < 15:
                cluster.append(circles[j])
                used[j] = True
        clusters.append(cluster)

    marker_clusters = [c for c in clusters if len(c) >= 3]
    if len(marker_clusters) != 4:
        raise AlignmentError(
            "markers_not_found",
            f"Expected 4 registration markers, found {len(marker_clusters)}",
        )

    h, w = gray.shape
    result: dict[str, tuple[float, float]] = {}
    for cluster in marker_clusters:
        cx = float(np.mean([p[0] for p in cluster]))
        cy = float(np.mean([p[1] for p in cluster]))
        key = ("top" if cy < h / 2 else "bottom") + "_" + ("left" if cx < w / 2 else "right")
        if key in result:
            raise AlignmentError("markers_ambiguous", f"Two marker clusters resolved to {key}")
        result[key] = (cx, cy)

    if len(result) != 4:
        raise AlignmentError("markers_ambiguous", "Markers did not resolve to 4 distinct corners")

    return result


def warp_to_canonical(img: np.ndarray, markers: dict, template: dict) -> np.ndarray:
    canonical_w = template["canonical_width"]
    canonical_h = template["canonical_height"]
    m = template["markers"]

    src_pts = np.array([
        markers["top_left"], markers["top_right"],
        markers["bottom_right"], markers["bottom_left"],
    ], dtype=np.float32)

    dst_pts = np.array([
        [m["top_left"][0] * canonical_w, m["top_left"][1] * canonical_h],
        [m["top_right"][0] * canonical_w, m["top_right"][1] * canonical_h],
        [m["bottom_right"][0] * canonical_w, m["bottom_right"][1] * canonical_h],
        [m["bottom_left"][0] * canonical_w, m["bottom_left"][1] * canonical_h],
    ], dtype=np.float32)

    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return cv2.warpPerspective(img, matrix, (canonical_w, canonical_h))


def verify_alignment(warped_gray: np.ndarray, template: dict, tolerance_px: int = 25) -> None:
    """
    Re-detects markers on the WARPED image and checks they land within
    tolerance of where the template says they should be. This catches a
    warp that "ran" but produced a distorted or mis-cornered result.
    """
    canonical_w = template["canonical_width"]
    canonical_h = template["canonical_height"]
    expected = {
        key: (val[0] * canonical_w, val[1] * canonical_h)
        for key, val in template["markers"].items()
    }
    try:
        detected = find_registration_markers(warped_gray)
    except AlignmentError:
        raise AlignmentError("alignment_failed", "Markers not re-detectable after warp")

    for key, (ex, ey) in expected.items():
        if key not in detected:
            raise AlignmentError("alignment_failed", f"Marker {key} missing after warp")
        dx, dy = detected[key]
        if abs(dx - ex) > tolerance_px or abs(dy - ey) > tolerance_px:
            raise AlignmentError(
                "alignment_failed",
                f"Marker {key} off by ({dx - ex:.1f}, {dy - ey:.1f})px, tolerance {tolerance_px}px",
            )


def align_sheet(img: np.ndarray, template_version: str) -> tuple[np.ndarray, dict]:
    """Full pipeline: detect markers -> warp -> verify. Returns (warped_bgr, template)."""
    template = load_template(template_version)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    markers = find_registration_markers(gray)
    warped = warp_to_canonical(img, markers, template)

    warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    verify_alignment(warped_gray, template)

    return warped, template
