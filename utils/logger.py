import csv
import os
from datetime import datetime


class ViolationLogger:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)

        if not os.path.exists(csv_path):
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "timestamp", "track_id", "plate_number", "violation_type",
                    "image_path", "plate_image_path",
                ])

    def log(self, track_id, plate_number, violation_type, image_path, plate_image_path=""):
        # plate_number: chuỗi biển số đã đọc được (PlateVoteAggregator.get),
        # hoặc "" nếu chưa đọc được. image_path: ảnh bằng chứng CHÍNH (toàn
        # thân người / toàn xe - xem utils/evidence.py::save_evidence).
        # plate_image_path: ảnh crop riêng vùng biển số, "" nếu chưa có.
        # KHÔNG để None gây lỗi parse CSV, luôn ghi chuỗi rỗng thay vì None.
        with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().isoformat(timespec="seconds"),
                track_id,
                plate_number or "",
                violation_type,
                image_path,
                plate_image_path or "",
            ])
