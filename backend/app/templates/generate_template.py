import json
import sys
from pathlib import Path

import cv2
import numpy as np
from sklearn.cluster import KMeans

SAMPLE_SHEET_PATH = "/home/murari/snap/viber/1/Downloads/omr/omr/Page0001.jpg"

CANONICAL_WIDTH = 1700
CANONICAL_HEIGHT = 2350
MARGIN = 60
BUBBLE_RADIUS_PX = 13
ROLL_BUBBLE_RADIUS_PX = 11

COLUMN_X = [
    [168.2, 248.7, 322.1, 392.3],
    [565.4, 638.2, 713.1, 780.6],
    [952.5, 1029.4, 1102.1, 1169.4],
    [1342.7, 1418.1, 1492.3, 1562.6],
]
START_QUESTION = [1, 51, 101, 151]
OPTIONS = ["A", "B", "C", "D"]


def find_registration_markers(gray):
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

    clusters = []
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
        raise ValueError(f"Expected 4 markers, found {len(marker_clusters)}")

    h, w = gray.shape
    result = {}
    for cluster in marker_clusters:
        cx = float(np.mean([p[0] for p in cluster]))
        cy = float(np.mean([p[1] for p in cluster]))
        key = ("top" if cy < h / 2 else "bottom") + "_" + ("left" if cx < w / 2 else "right")
        result[key] = (cx, cy)
    return result


def warp_to_canonical(img, markers):
    src_pts = np.array([markers["top_left"], markers["top_right"],
                         markers["bottom_right"], markers["bottom_left"]], dtype=np.float32)
    dst_pts = np.array([
        [MARGIN, MARGIN], [CANONICAL_WIDTH - MARGIN, MARGIN],
        [CANONICAL_WIDTH - MARGIN, CANONICAL_HEIGHT - MARGIN], [MARGIN, CANONICAL_HEIGHT - MARGIN],
    ], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
    return cv2.warpPerspective(img, matrix, (CANONICAL_WIDTH, CANONICAL_HEIGHT))


def cluster(ys, gap=15):
    ys = sorted(ys)
    clusters = [[ys[0]]]
    for y in ys[1:]:
        if y - clusters[-1][-1] < gap:
            clusters[-1].append(y)
        else:
            clusters.append([y])
    return [float(np.mean(c)) for c in clusters]


def resolve_rows(centers, n_expected=50):
    centers = sorted(centers)
    gaps = np.diff(centers)
    ref_spacing = float(np.median(gaps))

    while len(centers) > n_expected and (centers[1] - centers[0]) > ref_spacing * 1.6:
        centers = centers[1:]
    while len(centers) > n_expected and (centers[-1] - centers[-2]) > ref_spacing * 1.6:
        centers = centers[:-1]

    merged = [centers[0]]
    for y in centers[1:]:
        if y - merged[-1] < ref_spacing * 0.55:
            merged[-1] = (merged[-1] + y) / 2
        else:
            merged.append(y)
    centers = merged

    fixed = [centers[0]]
    for y in centers[1:]:
        gap = y - fixed[-1]
        n_missing = round(gap / ref_spacing) - 1
        if n_missing > 0:
            start = fixed[-1]
            for k in range(1, n_missing + 1):
                fixed.append(start + k * (y - start) / (n_missing + 1))
        fixed.append(y)

    if len(fixed) != n_expected:
        raise ValueError(f"resolved to {len(fixed)} rows, expected {n_expected} - inspect manually")
    return fixed


def build_roll_number_section(warped):
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    roi = gray[280:660, 0:400]
    circles = cv2.HoughCircles(
        roi, cv2.HOUGH_GRADIENT, dp=1, minDist=15,
        param1=80, param2=15, minRadius=8, maxRadius=15,
    )
    if circles is None:
        raise SystemExit("No roll-number circles detected - check sample sheet quality")
    circles = circles[0]
    circles[:, 1] += 280

    xs = circles[:, 0].reshape(-1, 1)
    km = KMeans(n_clusters=5, n_init=10, random_state=0).fit(xs)
    col_x = sorted(float(c) for c in km.cluster_centers_.flatten())

    col_ys = [[] for _ in range(5)]
    for cx, cy, _cr in circles:
        best_col, best_dist = None, 999
        for ci, ox in enumerate(col_x):
            d = abs(cx - ox)
            if d < best_dist:
                best_dist = d
                best_col = ci
        if best_dist < 10:
            col_ys[best_col].append(float(cy))

    resolved_cols = [resolve_rows(ys, n_expected=10) for ys in col_ys]
    row_y = [sum(vals) / len(vals) for vals in zip(*resolved_cols)]

    bubbles = []
    for col_idx, x in enumerate(col_x):
        for digit in range(10):
            y = row_y[digit]
            bubbles.append({
                "digit_position": col_idx,
                "digit_value": digit,
                "x": round(x / CANONICAL_WIDTH, 5),
                "y": round(y / CANONICAL_HEIGHT, 5),
                "radius": round(ROLL_BUBBLE_RADIUS_PX / CANONICAL_WIDTH, 5),
            })
    print(f"roll number grid: {len(bubbles)} bubbles (5 columns x 10 digits)")
    return {"num_digits": 5, "bubbles": bubbles}


def main():
    sheet_path = sys.argv[1] if len(sys.argv) > 1 else SAMPLE_SHEET_PATH
    img = cv2.imread(sheet_path)
    if img is None:
        raise SystemExit(f"Could not read {sheet_path}")

    gray0 = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    markers = find_registration_markers(gray0)
    warped = warp_to_canonical(img, markers)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

    roi = gray[600:2350, :]
    circles = cv2.HoughCircles(roi, cv2.HOUGH_GRADIENT, dp=1, minDist=18,
                                param1=80, param2=15, minRadius=9, maxRadius=16)
    if circles is None:
        raise SystemExit("No circles detected - check sample sheet quality")
    circles = circles[0]
    circles[:, 1] += 600

    col_rows = [[] for _ in range(4)]
    for cx, cy, cr in circles:
        best_col, best_dist = None, 999
        for ci, opts in enumerate(COLUMN_X):
            for ox in opts:
                d = abs(cx - ox)
                if d < best_dist:
                    best_dist = d
                    best_col = ci
        if best_dist < 10:
            col_rows[best_col].append(cy)

    final_rows = []
    for ci, ys in enumerate(col_rows):
        centers = cluster(ys)
        fixed = resolve_rows(centers)
        print(f"column {ci+1}: {len(centers)} raw clusters -> {len(fixed)} final rows")
        final_rows.append(fixed)

    bubbles = []
    for ci in range(4):
        for row_idx in range(50):
            q_num = START_QUESTION[ci] + row_idx
            y = final_rows[ci][row_idx]
            for opt, x in zip(OPTIONS, COLUMN_X[ci]):
                bubbles.append({
                    "question": q_num, "option": opt,
                    "x": round(x / CANONICAL_WIDTH, 5),
                    "y": round(y / CANONICAL_HEIGHT, 5),
                    "radius": round(BUBBLE_RADIUS_PX / CANONICAL_WIDTH, 5),
                })

    template = {
        "template_version": "ambition-guru-v1",
        "canonical_width": CANONICAL_WIDTH,
        "canonical_height": CANONICAL_HEIGHT,
        "markers": {
            "top_left": [MARGIN / CANONICAL_WIDTH, MARGIN / CANONICAL_HEIGHT],
            "top_right": [(CANONICAL_WIDTH - MARGIN) / CANONICAL_WIDTH, MARGIN / CANONICAL_HEIGHT],
            "bottom_left": [MARGIN / CANONICAL_WIDTH, (CANONICAL_HEIGHT - MARGIN) / CANONICAL_HEIGHT],
            "bottom_right": [(CANONICAL_WIDTH - MARGIN) / CANONICAL_WIDTH, (CANONICAL_HEIGHT - MARGIN) / CANONICAL_HEIGHT],
        },
        "bubbles": bubbles,
    }

    template["roll_number"] = build_roll_number_section(warped)

    out_path = Path(__file__).parent / "template_ambition_guru_v1.json"
    with open(out_path, "w") as f:
        json.dump(template, f, indent=2)
    print(f"\nwrote {out_path} with {len(bubbles)} main bubbles + {len(template['roll_number']['bubbles'])} roll-number bubbles")


if __name__ == "__main__":
    main()
