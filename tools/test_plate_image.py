"""
Script test RIÊNG chức năng nhận diện + đọc biển số bằng 1 ẢNH TĨNH - không
cần chạy cả pipeline (Tracker, GUI, video...). Dùng để kiểm tra nhanh model
plate.pt + EasyOCR có hoạt động đúng không, TRƯỚC KHI chạy cả hệ thống.

CÁCH DÙNG:
    python test_plate_image.py --image duong/dan/anh_xe.jpg

Ảnh đầu vào NÊN LÀ ảnh đã cắt gần đúng 1 chiếc xe (giống crop mà Tracker cắt
ra trong pipeline thật - xem channels/flow_helmet_channel.py), KHÔNG PHẢI ảnh
toàn cảnh nhiều xe - vì PlateDetector được thiết kế để chạy trên crop 1 xe,
không chạy trên cả khung hình (xem modules/plate.py). Nếu ảnh bạn có là ảnh
toàn cảnh, dùng thêm --vehicle-model để script tự detect + crop xe trước.

KẾT QUẢ:
    - In ra terminal: có detect được vùng biển số không, độ nét, text OCR đọc
      được, confidence.
    - Lưu 3 ảnh ra cùng thư mục với ảnh gốc để xem trực quan:
        <ten_anh>_1_bbox.jpg       - ảnh gốc + khung biển số đã detect
        <ten_anh>_2_plate_raw.jpg  - crop biển số THÔ (trước tiền xử lý)
        <ten_anh>_3_plate_processed.jpg - crop biển số SAU tiền xử lý (ảnh
                                          thật sự đưa vào EasyOCR)

Tuỳ chọn:
    --vehicle-model models/vehicle_vn.pt   dùng khi ảnh đầu vào là ẢNH TOÀN
                                            CẢNH (script tự detect xe to nhất
                                            + crop trước khi đưa vào plate
                                            detector, giống đúng pipeline
                                            thật)
    --plate-model models/plate.pt          mặc định lấy từ config.PLATE_MODEL
"""
import argparse
import os

import cv2

import config
from modules.plate import PlateDetector, PlateReader, preprocess_plate, sharpness_score


def detect_vehicle_crop(image, vehicle_model_path):
    """Dùng khi ảnh đầu vào là ảnh toàn cảnh - tự detect xe TO NHẤT trong ảnh
    (giả định là xe cần test) rồi crop ra, giống bước Tracker làm trong
    pipeline thật. Trả về (crop, bbox) hoặc (None, None) nếu không detect
    được xe nào.
    """
    from ultralytics import YOLO

    model = YOLO(vehicle_model_path)
    results = model(image, conf=config.VEHICLE_CONF, verbose=False)

    best_box, best_area = None, 0
    for r in results:
        if r.boxes is None:
            continue
        for box, cls in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.cls.cpu().numpy()):
            if int(cls) not in config.ALLOWED_VEHICLE_CLASSES:
                continue
            x1, y1, x2, y2 = map(int, box)
            area = (x2 - x1) * (y2 - y1)
            if area > best_area:
                best_area = area
                best_box = (x1, y1, x2, y2)

    if best_box is None:
        return None, None
    x1, y1, x2, y2 = best_box
    return image[y1:y2, x1:x2], best_box


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Đường dẫn ảnh cần test")
    ap.add_argument("--vehicle-model", default=None,
                     help="Nếu ảnh là ảnh toàn cảnh (nhiều xe/nền), truyền model xe để tự crop trước")
    ap.add_argument("--plate-model", default=config.PLATE_MODEL)
    ap.add_argument("--plate-conf", type=float, default=config.PLATE_CONF,
                     help="Ghi đè conf để test nhanh, không cần sửa config.py")
    args = ap.parse_args()

    image = cv2.imread(args.image)
    if image is None:
        print(f"LỖI: không đọc được ảnh tại {args.image} - kiểm tra lại đường dẫn.")
        return

    base, ext = os.path.splitext(args.image)

    if args.vehicle_model:
        print(f"Đang detect xe trong ảnh toàn cảnh bằng {args.vehicle_model}...")
        vehicle_crop, bbox = detect_vehicle_crop(image, args.vehicle_model)
        if vehicle_crop is None:
            print("Không detect được xe nào trong ảnh - dừng lại. Thử ảnh khác hoặc bỏ --vehicle-model "
                  "nếu ảnh này đã là ảnh crop sẵn 1 xe.")
            return
        print(f"  -> Đã crop xe tại bbox {bbox}")
    else:
        vehicle_crop = image
        bbox = (0, 0, image.shape[1], image.shape[0])

    print(f"\nĐang chạy PlateDetector ({args.plate_model})...")
    plate_detector = PlateDetector(args.plate_model, conf=args.plate_conf, device=config.DEVICE)

    # In tên các class model này thực sự có - kiểm tra nhanh xem có đúng là
    # model biển số không (nhỡ trỏ nhầm file .pt khác, vd model mũ bảo hiểm).
    print(f"  -> model.names = {plate_detector.model.names}")

    plate_box = plate_detector.detect(vehicle_crop)

    if plate_box is None:
        print(f"KHÔNG detect được vùng biển số nào ở conf={args.plate_conf}.")

        # Chẩn đoán sâu hơn: chạy lại model ở conf CỰC THẤP để xem model có
        # THẤY GÌ KHÔNG (dù không đủ tin cậy) - phân biệt 2 tình huống khác
        # nhau hoàn toàn:
        #   (a) model CÓ thấy vùng nghi ngờ nhưng conf thấp hơn ngưỡng -> chỉ
        #       cần hạ PLATE_CONF là xong.
        #   (b) model KHÔNG thấy gì cả dù conf=0.01 -> vấn đề nằm ở MODEL
        #       (train chưa đủ, sai domain ảnh, hoặc nhầm file .pt khác) chứ
        #       không phải do chỉnh ngưỡng conf.
        print("\nĐang thử lại ở conf=0.01 để chẩn đoán (chỉ để xem, KHÔNG dùng ngưỡng này khi chạy thật)...")
        raw_results = plate_detector.model(vehicle_crop, conf=0.01, device=plate_detector.device, verbose=False)
        found_any = False
        for r in raw_results:
            if r.boxes is None:
                continue
            for box, cf in zip(r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()):
                found_any = True
                print(f"    -> ứng viên bbox={tuple(map(int, box))} conf={float(cf):.3f}")

        if found_any:
            print("\n=> Model CÓ thấy vùng nghi ngờ nhưng conf thấp hơn ngưỡng hiện tại "
                  f"({args.plate_conf}) - thử hạ PLATE_CONF trong config.py (hoặc dùng --plate-conf khi test) "
                  "xuống gần mức conf ứng viên cao nhất ở trên.")
        else:
            print("\n=> Model KHÔNG thấy GÌ CẢ dù ở conf cực thấp (0.01) - đây KHÔNG phải vấn đề ngưỡng "
                  "conf. Khả năng cao: (1) models/plate.pt không phải model biển số thật (kiểm tra lại "
                  "model.names in ra ở trên - nếu không phải 1 class kiểu 'plate'/'license_plate', bạn "
                  "đang trỏ nhầm file .pt), (2) model chưa được train đủ tốt cho GÓC CHỤP/KHOẢNG CÁCH như "
                  "ảnh này (vd chỉ train trên ảnh chụp gần/thẳng biển số, không quen với ảnh chụp cả đuôi "
                  "xe), (3) thử crop tay 1 vùng SÁT NGAY biển số (không qua --vehicle-model) rồi test lại - "
                  "nếu model detect được trên crop sát mà không detect được trên crop cả xe, nghĩa là model "
                  "cần ảnh đầu vào 'zoom' gần hơn so với thiết kế hiện tại của pipeline (đáng để biết sớm).")

        annotated = vehicle_crop.copy()
        cv2.imwrite(f"{base}_1_bbox{ext}", annotated)
        return

    px1, py1, px2, py2 = plate_box
    print(f"  -> Detect được vùng biển số tại (trong toạ độ vehicle crop): {plate_box}")

    plate_raw = vehicle_crop[py1:py2, px1:px2]
    ph, pw = plate_raw.shape[:2]
    print(f"  -> Kích thước crop biển số: {pw}x{ph}px")
    if ph < config.MIN_PLATE_CROP_HEIGHT or pw < config.MIN_PLATE_CROP_WIDTH:
        print(f"  CẢNH BÁO: nhỏ hơn ngưỡng MIN_PLATE_CROP_HEIGHT/WIDTH hiện tại "
              f"({config.MIN_PLATE_CROP_HEIGHT}x{config.MIN_PLATE_CROP_WIDTH}) - trong pipeline thật, "
              f"crop này sẽ bị BỎ QUA, không chạy OCR.")

    sharp = sharpness_score(plate_raw)
    print(f"  -> Độ nét (sharpness_score): {sharp:.1f}")

    processed = preprocess_plate(plate_raw, target_height=config.PLATE_UPSCALE_HEIGHT)

    print(f"\nĐang chạy EasyOCR (lần đầu có thể chậm do tự tải model)...")
    plate_reader = PlateReader(
        langs=config.PLATE_OCR_LANGS,
        gpu=config.PLATE_OCR_GPU,
        allowlist=config.PLATE_OCR_ALLOWLIST,
        min_sharpness=0,  # tắt lọc mờ khi test - muốn thấy kết quả OCR thật dù ảnh mờ
        upscale_height=config.PLATE_UPSCALE_HEIGHT,
        model_storage_directory=config.PLATE_OCR_MODEL_DIR,
    )
    text, ocr_conf = plate_reader.read(plate_raw)

    print("\n" + "=" * 40)
    print(f"KẾT QUẢ: text='{text}'  confidence={ocr_conf:.3f}")
    print("=" * 40)

    # Lưu ảnh để xem trực quan
    annotated = vehicle_crop.copy()
    cv2.rectangle(annotated, (px1, py1), (px2, py2), (0, 255, 0), 2)
    cv2.putText(annotated, text or "(khong doc duoc)", (px1, max(py1 - 10, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imwrite(f"{base}_1_bbox{ext}", annotated)
    cv2.imwrite(f"{base}_2_plate_raw{ext}", plate_raw)
    cv2.imwrite(f"{base}_3_plate_processed{ext}", processed)

    print(f"\nĐã lưu 3 ảnh kiểm tra trực quan:")
    print(f"  {base}_1_bbox{ext}            - ảnh + khung biển số")
    print(f"  {base}_2_plate_raw{ext}       - crop biển số thô")
    print(f"  {base}_3_plate_processed{ext} - crop sau tiền xử lý (ảnh thật đưa vào OCR)")


if __name__ == "__main__":
    main()
