"""
Script HIỆU CHỈNH ngưỡng độ nét cho tính năng đọc biển số.

CHẠY SCRIPT NÀY TRÊN MÁY BẠN (nơi đã cài ultralytics/torch/easyocr đầy đủ),
KHÔNG chạy được trong sandbox của Claude vì môi trường này không có mạng để
cài torch/ultralytics/easyocr.

Mục đích: quét toàn bộ video, chạy ĐÚNG pipeline thật (Tracker + PlateDetector
+ PlateReader), ghi lại sharpness_score của TỪNG lần detect biển số kèm kết
quả OCR - để bạn nhìn số liệu thật và tự chọn ngưỡng PLATE_MIN_SHARPNESS /
PLATE_MIN_VEHICLE_SHARPNESS phù hợp với video/camera của mình, thay vì đoán mò.

Cách dùng:
    python tools/calibrate_plate_thresholds.py --video test1.mp4 \
        --vehicle-model models/best.pt --plate-model models/plate.pt

Kết quả:
    - In ra màn hình từng dòng: track_id, frame, sharpness xe, sharpness biển
      số, text OCR đọc được, confidence.
    - Lưu toàn bộ ra plate_calibration.csv để mở bằng Excel/Google Sheets,
      sort theo cột sharpness_bien_so rồi nhìn bằng mắt: từ mức sharpness nào
      trở xuống thì chữ trong ảnh_bien_so bắt đầu không đọc được nữa - đó
      chính là ngưỡng nên đặt cho PLATE_MIN_SHARPNESS.
    - Cột sharpness_xe dùng để chọn PLATE_MIN_VEHICLE_SHARPNESS tương tự,
      nhưng đối chiếu ở mức "xe" (thường ngưỡng này sẽ THẤP hơn ngưỡng biển
      số, vì ảnh xe to hơn/có nhiều chi tiết hơn nên phương sai Laplacian tự
      nhiên cao hơn).
    - Cột anh_bien_so là đường dẫn tới ảnh crop đã lưu (thư mục
      plate_calibration_crops/) - mở trực tiếp ảnh đó để đối chiếu bằng mắt
      với con số sharpness, ĐỪNG chỉ tin con số mà không nhìn ảnh thật.
"""
import argparse
import csv
import os

import cv2

import config
from core.tracker import Tracker
from modules.plate import PlateDetector, PlateReader, sharpness_score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--vehicle-model", default=config.VEHICLE_MODEL)
    ap.add_argument("--plate-model", default=config.PLATE_MODEL)
    ap.add_argument("--every-n-frames", type=int, default=2,
                     help="Chỉ xử lý 1 frame mỗi N frame để chạy nhanh hơn khi hiệu chỉnh (mặc định 2).")
    ap.add_argument("--out-csv", default="plate_calibration.csv")
    ap.add_argument("--out-dir", default="plate_calibration_crops")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    tracker = Tracker(args.vehicle_model, allowed_classes=(2, 3), device=config.DEVICE, conf=config.VEHICLE_CONF)
    plate_detector = PlateDetector(args.plate_model, conf=config.PLATE_CONF, device=config.DEVICE)
    plate_reader = PlateReader(
        langs=config.PLATE_OCR_LANGS,
        gpu=config.PLATE_OCR_GPU,
        allowlist=config.PLATE_OCR_ALLOWLIST,
        min_sharpness=0.0,  # TẮT lọc mờ khi hiệu chỉnh - muốn thấy TẤT CẢ số liệu, kể cả case mờ
        upscale_height=config.PLATE_UPSCALE_HEIGHT,
    )

    cap = cv2.VideoCapture(args.video)
    rows = []
    frame_idx = -1
    saved_count = 0

    print("Đang quét video, có thể mất vài phút tuỳ độ dài video + CPU/GPU...")

    while True:
        ret, raw_frame = cap.read()
        if not ret:
            break
        frame_idx += 1
        if frame_idx % args.every_n_frames != 0:
            continue

        h0, w0 = raw_frame.shape[:2]
        frame = cv2.resize(raw_frame, (config.RESIZE_WIDTH, int(h0 * config.RESIZE_WIDTH / w0)))
        scale_x = w0 / frame.shape[1]
        scale_y = h0 / frame.shape[0]

        tracks, _ = tracker.track(frame)

        for obj in tracks:
            x1, y1, x2, y2 = obj["bbox"]
            vx1, vy1 = int(x1 * scale_x), int(y1 * scale_y)
            vx2, vy2 = int(x2 * scale_x), int(y2 * scale_y)
            vehicle_crop = raw_frame[vy1:vy2, vx1:vx2]
            if vehicle_crop.size == 0:
                continue

            sharp_vehicle = sharpness_score(vehicle_crop)

            plate_box = plate_detector.detect(vehicle_crop)
            if plate_box is None:
                continue
            bx1, by1, bx2, by2 = plate_box
            plate_crop = vehicle_crop[by1:by2, bx1:bx2]
            if plate_crop.size == 0:
                continue

            sharp_plate = sharpness_score(plate_crop)
            text, conf = plate_reader.read(plate_crop)

            saved_count += 1
            crop_path = os.path.join(args.out_dir, f"{saved_count:04d}_id{obj['id']}_f{frame_idx}.jpg")
            cv2.imwrite(crop_path, plate_crop)

            row = {
                "track_id": obj["id"],
                "frame": frame_idx,
                "sharpness_xe": round(sharp_vehicle, 1),
                "sharpness_bien_so": round(sharp_plate, 1),
                "ocr_text": text,
                "ocr_conf": round(conf, 3),
                "anh_bien_so": crop_path,
            }
            rows.append(row)
            print(f"track={obj['id']:>4} frame={frame_idx:>5} "
                  f"sharp_xe={sharp_vehicle:7.1f} sharp_bienso={sharp_plate:7.1f} "
                  f"text='{text}' conf={conf:.2f}")

    cap.release()

    if rows:
        with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    print(f"\nXong. {len(rows)} lần detect được biển số, chi tiết trong {args.out_csv}")
    print(f"Ảnh crop từng lần trong thư mục {args.out_dir}/ - mở kèm CSV để đối chiếu bằng mắt.")
    print("Cách chọn ngưỡng: sort CSV theo sharpness_bien_so tăng dần, mở lần lượt các ảnh "
          "anh_bien_so từ thấp lên cao, tìm mức sharpness mà TỪ ĐÓ TRỞ LÊN mắt thường bắt đầu "
          "đọc được chữ rõ ràng - đó là giá trị nên đặt cho PLATE_MIN_SHARPNESS. Làm tương tự với "
          "cột sharpness_xe (đối chiếu cùng dòng) để chọn PLATE_MIN_VEHICLE_SHARPNESS.")


if __name__ == "__main__":
    main()
