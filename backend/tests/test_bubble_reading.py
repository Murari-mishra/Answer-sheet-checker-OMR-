import json
from pathlib import Path

import cv2
import numpy as np

from app.services.bubble_reading import ROLL_COLUMN_X, ROLL_ROW_Y, read_roll_number


TEMPLATE_PATH = Path(__file__).parents[1] / "app" / "templates" / "template_ambition_guru_v1.json"


def test_read_roll_number_uses_template_coordinates_and_row_digits():
    with TEMPLATE_PATH.open() as file:
        template = json.load(file)

    image = np.full((2350, 1700, 3), 255, dtype=np.uint8)
    expected = "90695"

    for bubble in template["roll_number"]["bubbles"]:
        position = int(bubble["digit_position"])
        digit = int(bubble["digit_value"])
        if expected[position] != str(digit):
            continue
        x = round(ROLL_COLUMN_X[position])
        y = round(ROLL_ROW_Y[digit])
        radius = round(bubble["radius"] * template["canonical_width"] * 0.8)
        cv2.circle(image, (x, y), radius, (0, 0, 0), -1)

    result = read_roll_number(image, template)

    assert result is not None
    assert result["roll_number"] == expected
    assert result["uncertain"] is False
