import cv2
from ultralytics import YOLO

import config
from core.tracker import Tracker
from utils.bbox import find_best_overlap
from utils.crop import crop_head


def main():
    # ----- BƯỚC 1: tên class thật của model mũ bảo hiểm -----
    helmet_model = YOLO(config.HELMET_MODEL)
    print("=== BƯỚC 1: model.names của helmet model ===")
    print(helmet_model.names)

    names_lower = [str(n).lower() for n in helmet_model.names.values()]
    has_helmet_kw = any("helmet" in n for n in names_lower)
    if not has_helmet_kw:
        print("!!! CẢNH BÁO: không có class nào chứa chữ 'helmet'.")
        print("    -> modules/helmet.py sẽ KHÔNG BAO GIỜ nhận ra HELMET/NO_HELMET,")
        print("    luôn trả về None (UNKNOWN). Đây rất có thể là nguyên nhân chính.")
        print("    Cách sửa: sửa lại điều kiện if/elif trong HelmetDetector.detect()")
        print("    cho khớp đúng tên class thật ở trên.")
    else:
        print("-> OK, có ít nhất 1 class chứa chữ 'helmet'.")
    print()

    # ----- BƯỚC 2: lấy 1 bbox xe THẬT từ chính video, y hệt lúc chạy pipeline -----
    cap = cv2.VideoCapture(config.SOURCE_CH1)
    ret, raw_frame = cap.read()
    if not ret:
        print(f"Không đọc được video: {config.SOURCE_CH1}")
        return

    h, w = raw_frame.shape[:2]
    new_w = config.RESIZE_WIDTH
    new_h = int(h * (new_w / w))
    frame = cv2.resize(raw_frame, (new_w, new_h))
    scale_x = raw_frame.shape[1] / frame.shape[1]
    scale_y = raw_frame.shape[0] / frame.shape[0]

    tracker = Tracker(
        model_path=config.VEHICLE_MODEL,
        allowed_classes=config.ALLOWED_VEHICLE_CLASSES,
        context_classes=(config.PERSON_CLASS_ID,),
        context_conf=config.PERSON_CONF,
        device=config.DEVICE,
        conf=config.VEHICLE_CONF,
    )
    tracks, persons = tracker.track(frame)

    if not tracks:
        print("=== BƯỚC 2: Không detect được xe nào ở frame đầu tiên. ===")
        print("    -> Thử sửa script này để lấy 1 frame khác giữa video (frame đầu")
        print("    thường ít xe hơn), hoặc kiểm tra lại VEHICLE_MODEL/VEHICLE_CONF.")
        return

    motorbike_tracks = [t for t in tracks if t["class_id"] == 3]
    if not motorbike_tracks:
        print("=== BƯỚC 2: Frame đầu tiên không có xe máy nào (chỉ có ô tô/khác). ===")
        print(f"    (tracks phát hiện được: {[t['class_id'] for t in tracks]})")
        print("    Lưu ý: ô tô KHÔNG cần check mũ bảo hiểm (production đã bỏ qua ô tô),")
        print("    nên debug script cần đúng 1 xe MÁY để kiểm tra pipeline này.")
        print("    Thử sửa script lấy frame khác trong video có xe máy.")
        return

    def _bbox_area(t):
        bx1, by1, bx2, by2 = t["bbox"]
        return (bx2 - bx1) * (by2 - by1)

    # Chọn xe máy có bbox LỚN NHẤT (gần camera nhất) để test -> đại diện hơn
    # cho trường hợp thực sự cần đánh giá, thay vì random chọn xe máy đầu
    # tiên (có thể đang ở xa, crop nhỏ, không phản ánh đúng khả năng model).
    motorbike_tracks.sort(key=_bbox_area, reverse=True)
    obj = motorbike_tracks[0]
    x1, y1, x2, y2 = obj["bbox"]
    print(f"=== BƯỚC 2: bbox xe máy LỚN NHẤT trong frame (trên ảnh đã resize) = {(x1, y1, x2, y2)}, class_id={obj['class_id']} ===")
    print(f"    (tổng {len(motorbike_tracks)} xe máy trong frame, đã chọn xe gần camera nhất)")
    print(f"    (phát hiện được {len(persons)} person trong frame này)")

    cy = (y1 + y2) // 2
    zone_threshold = int(frame.shape[0] * config.DETECT_ZONE_RATIO)
    in_zone = cy > zone_threshold
    print(f"cy={cy}, ngưỡng detect_zone={zone_threshold} (frame cao {frame.shape[0]}px)")
    if in_zone:
        print("-> OK, object này NẰM TRONG detect_zone, sẽ được check mũ bảo hiểm.")
    else:
        print("!!! object này KHÔNG nằm trong detect_zone -> sẽ luôn là UNKNOWN.")
        print("    Nếu TOÀN BỘ xe trong video của bạn đều rơi vào trường hợp này,")
        print("    hạ config.DETECT_ZONE_RATIO xuống (vd 0.3) hoặc đổi lại logic")
        print("    zone cho phù hợp góc quay camera thật của bạn.")
    print()

    # ----- BƯỚC 2b: tìm person chồng lấn nhiều nhất lên xe này (KHÔNG phải bbox xe) -----
    rider = find_best_overlap(obj["bbox"], persons)
    print("=== BƯỚC 2b: tìm person khớp với xe (thay vì dùng bbox xe để đoán đầu) ===")
    if rider is None:
        print("!!! Không tìm thấy person nào chồng lấn lên xe này.")
        print("    -> Production sẽ báo 'KHONG THAY NGUOI', KHÔNG gọi model.")
        print("    3 khả năng: (1) xe này thực sự không có người (xe dựng/đỗ),")
        print("    (2) người bị che khuất nên model không detect ra,")
        print("    (3) người có tồn tại gần đó nhưng bbox không thực sự chồng lấn.")

        vis = frame.copy()
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 0, 255), 2)  # xe đang xét: ĐỎ
        for p in persons:
            pxa, pya, pxb, pyb = p["bbox"]
            cv2.rectangle(vis, (pxa, pya), (pxb, pyb), (0, 255, 0), 1)  # person: XANH LÁ
        cv2.imwrite("debug_no_person_match.jpg", vis)
        print("    Đã lưu debug_no_person_match.jpg: khung ĐỎ = xe đang xét,")
        print("    khung XANH LÁ = toàn bộ person model detect được trong frame.")
        print("    Mở ảnh lên xem: xe đỏ có người ngồi trên/cạnh không? Nếu có mà")
        print("    khung xanh gần nhất không chồng lấn khung đỏ -> do (3), cần nới")
        print("    lỏng find_best_overlap (vd giãn thêm biên xe trước khi so overlap).")
        return
    print(f"-> Tìm thấy person bbox (trên ảnh đã resize) = {rider['bbox']}")
    print()

    # ----- BƯỚC 3: crop đúng như pipeline thật (cắt bbox NGƯỜI từ ẢNH GỐC) -----
    px1, py1, px2, py2 = rider["bbox"]
    rx1, ry1 = int(px1 * scale_x), int(py1 * scale_y)
    rx2, ry2 = int(px2 * scale_x), int(py2 * scale_y)
    head_crop = crop_head(raw_frame, rx1, ry1, rx2, ry2, config.PERSON_HEAD_RATIO)
    crop_shape = head_crop.shape if head_crop is not None else None
    print(f"=== BƯỚC 3: kích thước head_crop (cắt từ bbox NGƯỜI trên ảnh GỐC) = {crop_shape} ===")
    if head_crop is None or head_crop.size == 0:
        print("!!! head_crop RỖNG -> model không có gì để nhận diện, luôn None (UNKNOWN).")
        print("    Kiểm tra lại bbox person ở BƯỚC 2b và config.PERSON_HEAD_RATIO.")
        return

    crop_h, crop_w = head_crop.shape[:2]
    if crop_h < config.MIN_HEAD_CROP_HEIGHT or crop_w < config.MIN_HEAD_CROP_WIDTH:
        print(f"!!! head_crop ({crop_w}x{crop_h}) nhỏ hơn ngưỡng tối thiểu "
              f"({config.MIN_HEAD_CROP_WIDTH}x{config.MIN_HEAD_CROP_HEIGHT}).")
        print("    -> Production sẽ báo 'QUA XA' cho xe này, KHÔNG gọi model.")
        print("    Xe này nằm quá xa camera để đánh giá đáng tin cậy.")

    cv2.imwrite("debug_head_crop.jpg", head_crop)
    print("Đã lưu debug_head_crop.jpg - MỞ FILE NÀY LÊN XEM có nhìn rõ đầu người,")
    print("có bị quá nhỏ/mờ/lệch không nằm trong khung hay không.")
    print()

    # ----- BƯỚC 4: chạy model TRỰC TIẾP trên crop, in TOÀN BỘ kết quả thô -----
    print("=== BƯỚC 4: kết quả thô của model trên head_crop (conf hạ về 0.05 để xem model CÓ thấy gì không) ===")
    results = helmet_model(head_crop, conf=0.05, verbose=False)
    found_any = False
    for r in results:
        if r.boxes is None:
            continue
        for cls_id, conf in zip(r.boxes.cls.cpu().numpy(), r.boxes.conf.cpu().numpy()):
            found_any = True
            name = helmet_model.names[int(cls_id)]
            print(f"  class='{name}'  conf={conf:.3f}")

    if not found_any:
        print("  (không detect được gì, kể cả với conf=0.05)")
        print("  -> model không nhận ra được gì trong crop này. Rất có thể do crop")
        print("  quá nhỏ/mờ/lệch vùng đầu (BƯỚC 3), KHÔNG PHẢI do ngưỡng conf.")
    else:
        print("  -> model CÓ thấy gì đó trong crop. Nếu tên class ở trên không khớp")
        print("  với điều kiện if/elif trong HelmetDetector.detect() thì đây chính")
        print("  là nguyên nhân (xem lại BƯỚC 1).")


if __name__ == "__main__":
    main()
