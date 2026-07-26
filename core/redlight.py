import cv2
import numpy as np

from utils.bbox import bbox_overlap_area


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
    def __init__(self, stop_line_y, direction="up", right_turn_zone=None, right_turn_min_overlap=0.35):
        self.stop_line_y = stop_line_y
        self.direction = direction
        # Ở HẦU HẾT giao lộ tại Việt Nam, xe được phép rẽ phải khi đèn đỏ (trừ
        # khi có biển "cấm rẽ phải khi đèn đỏ" hoặc đèn tín hiệu rẽ phải
        # riêng) - nếu coi MỌI xe cắt qua vạch dừng lúc đèn đỏ là vi phạm thì
        # sẽ bắt oan rất nhiều xe đang rẽ phải hợp lệ. right_turn_zone (x1,
        # y1, x2, y2) đánh dấu vùng ảnh tương ứng làn/khu vực rẽ phải - xe cắt
        # vạch dừng lúc đèn đỏ nhưng bbox nằm phần lớn trong vùng này thì
        # KHÔNG tính vi phạm. None = tắt hẳn ngoại lệ (dùng cho giao lộ có
        # biển cấm rẽ phải, hoặc khi camera không bao quát được làn rẽ phải).
        self.right_turn_zone = right_turn_zone
        self.right_turn_min_overlap = right_turn_min_overlap
        self.prev_positions = {}
        self.violated_ids = set()
        # Xe bị loại trừ vì đang rẽ phải hợp lệ - KHÔNG phải vi phạm, lưu lại
        # riêng chỉ để debug/hiển thị (phân biệt với xe chưa từng cắt vạch).
        self.right_turn_ids = set()

    def _crossed_line(self, prev_y, cy):
        if self.direction == "up":
            return prev_y > self.stop_line_y >= cy
        return prev_y < self.stop_line_y <= cy

    def _is_turning_right(self, bbox):
        """True nếu bbox xe chồng lấn đủ nhiều (>= right_turn_min_overlap
        tính theo % diện tích bbox xe) lên right_turn_zone - coi là đang rẽ
        phải hợp lệ. Luôn trả về False nếu right_turn_zone chưa cấu hình.
        """
        if self.right_turn_zone is None:
            return False
        x1, y1, x2, y2 = bbox
        bbox_area = max(0, x2 - x1) * max(0, y2 - y1)
        if bbox_area == 0:
            return False
        overlap = bbox_overlap_area(bbox, self.right_turn_zone)
        return (overlap / bbox_area) >= self.right_turn_min_overlap

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
                if self._is_turning_right(obj["bbox"]):
                    # Rẽ phải hợp lệ theo right_turn_zone đã cấu hình - không
                    # tính vi phạm, chỉ ghi nhận lại để debug/thống kê.
                    self.right_turn_ids.add(obj_id)
                    continue
                self.violated_ids.add(obj_id)
                new_violations.append(obj_id)

        return new_violations
