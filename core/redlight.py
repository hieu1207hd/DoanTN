import cv2
import numpy as np


class RedLightDetector:
    def __init__(self, roi, lower1, upper1, lower2, upper2, pixel_threshold=50):
        self.roi = roi  # (x1, y1, x2, y2)
        self.lower1 = np.array(lower1, dtype=np.uint8)
        self.upper1 = np.array(upper1, dtype=np.uint8)
        self.lower2 = np.array(lower2, dtype=np.uint8)
        self.upper2 = np.array(upper2, dtype=np.uint8)
        self.pixel_threshold = pixel_threshold

    def is_red(self, frame):
        x1, y1, x2, y2 = self.roi
        patch = frame[y1:y2, x1:x2]
        if patch.size == 0:
            return False

        hsv = cv2.cvtColor(patch, cv2.COLOR_BGR2HSV)
        # màu đỏ nằm ở 2 đầu của dải Hue (gần 0 và gần 179) nên cần 2 mask
        mask1 = cv2.inRange(hsv, self.lower1, self.upper1)
        mask2 = cv2.inRange(hsv, self.lower2, self.upper2)
        red_pixels = cv2.countNonZero(mask1) + cv2.countNonZero(mask2)

        return red_pixels >= self.pixel_threshold


class RedLightViolationChecker:
    def __init__(self, stop_line_y, direction="up"):
        self.stop_line_y = stop_line_y
        self.direction = direction
        self.prev_positions = {}
        self.violated_ids = set()

    def _crossed_line(self, prev_y, cy):
        if self.direction == "up":
            return prev_y > self.stop_line_y >= cy
        return prev_y < self.stop_line_y <= cy

    def update(self, tracks, is_red):
        new_violations = []

        for obj in tracks:
            obj_id = obj["id"]
            x1, y1, x2, y2 = obj["bbox"]
            cy = (y1 + y2) // 2

            prev_y = self.prev_positions.get(obj_id)
            self.prev_positions[obj_id] = cy

            if prev_y is None:
                continue

            if self._crossed_line(prev_y, cy) and is_red and obj_id not in self.violated_ids:
                self.violated_ids.add(obj_id)
                new_violations.append(obj_id)

        return new_violations
