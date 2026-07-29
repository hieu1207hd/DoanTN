"""
Công cụ hiệu chỉnh Channel 2 (vượt đèn đỏ) - CHỈ dùng khi đã có video/camera
thật cho góc quay đèn giao thông (config.SOURCE_CH2).

Cách dùng:
1. Sửa config.SOURCE_CH2 trỏ tới video/camera thật của bạn.
2. Chạy: python debug_redlight.py
3. 1 cửa sổ hiện ra: KÉO CHUỘT vẽ 1 khung chữ nhật quanh cụm đèn giao thông,
   nhấn ENTER hoặc SPACE để xác nhận (nhấn C để chọn lại từ đầu).
4. Script tự in ra dòng TRAFFIC_LIGHT_ROI = (...) để bạn copy thẳng vào
   config.py, chạy thử is_red() ngay trên frame đó, và lưu ảnh
   debug_redlight_setup.jpg để bạn kiểm tra bằng mắt vị trí ROI + stop_line
   có đúng với đèn/vạch dừng thật không.
"""
import cv2

import config
from core.redlight import RedLightDetector


def main():
    cap = cv2.VideoCapture(config.SOURCE_CH2)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(f"Không đọc được video/camera: {config.SOURCE_CH2}")
        print("-> Sửa config.SOURCE_CH2 trỏ đúng video/camera thật rồi chạy lại script này.")
        return

    h, w = frame.shape[:2]
    new_w = config.RESIZE_WIDTH
    new_h = int(h * (new_w / w))
    frame = cv2.resize(frame, (new_w, new_h))

    print("=== BƯỚC 1: chọn vùng đèn giao thông ===")
    print("Kéo chuột vẽ 1 khung quanh cụm đèn giao thông trong ảnh vừa hiện ra,")
    print("nhấn ENTER hoặc SPACE để xác nhận (nhấn C để huỷ và chọn lại).")
    x, y, w_roi, h_roi = cv2.selectROI("Chon vung den giao thong", frame, showCrosshair=True)
    cv2.destroyWindow("Chon vung den giao thong")

    if w_roi == 0 or h_roi == 0:
        print("Bạn chưa chọn vùng nào (bấm ESC/không kéo) - dừng lại, chạy lại script để thử tiếp.")
        return

    roi = (x, y, x + w_roi, y + h_roi)
    print(f"-> ROI vừa chọn (x1,y1,x2,y2) = {roi}")
    print("    Copy dòng sau vào config.py:")
    print(f"    TRAFFIC_LIGHT_ROI = {roi}")
    print()

    # ----- BƯỚC 2: chạy thử is_red() ngay với ROI vừa chọn -----
    detector = RedLightDetector(
        roi=roi,
        lower1=config.RED_HSV_LOWER1, upper1=config.RED_HSV_UPPER1,
        lower2=config.RED_HSV_LOWER2, upper2=config.RED_HSV_UPPER2,
        pixel_threshold=config.RED_PIXEL_THRESHOLD,
    )
    is_red = detector.is_red(frame)
    print(f"=== BƯỚC 2: kết quả is_red() trên frame này = {is_red} ===")
    print("So khớp với đèn thật trong ảnh lúc chọn:")
    print("- Nếu đèn đang ĐỎ mà is_red=False (hoặc ngược lại), thử nới rộng/hạ")
    print("  config.RED_PIXEL_THRESHOLD, hoặc chỉnh RED_HSV_LOWER/UPPER cho khớp")
    print("  màu đèn thật (đèn LED/ánh sáng ban đêm có thể lệch tông màu).")
    print("- Chạy lại script này ở 1 khoảnh khắc khác (đèn đang xanh) để so sánh 2 chiều.")
    print()

    # ----- BƯỚC 3: vẽ ROI + stop_line lên ảnh để xem trực quan -----
    vis = frame.copy()
    cv2.rectangle(vis, (roi[0], roi[1]), (roi[2], roi[3]), (0, 0, 255), 2)
    cv2.putText(vis, f"ROI den ({'DO' if is_red else 'khong do'})", (roi[0], max(roi[1] - 10, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    stop_line_y = int(new_h * config.STOP_LINE_Y_RATIO)
    cv2.line(vis, (0, stop_line_y), (new_w, stop_line_y), (0, 255, 255), 2)
    cv2.putText(vis, "stop_line (STOP_LINE_Y_RATIO)", (10, max(stop_line_y - 10, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

    cv2.imwrite("debug_redlight_setup.jpg", vis)
    print("Đã lưu debug_redlight_setup.jpg:")
    print("- Khung ĐỎ: đúng vùng ROI vừa chọn.")
    print("- Đường VÀNG: vị trí stop_line theo config.STOP_LINE_Y_RATIO hiện tại.")
    print("Mở ảnh lên xem đường vàng có đúng vị trí vạch dừng thật trên đường")
    print("không - nếu lệch, chỉnh STOP_LINE_Y_RATIO trong config.py rồi chạy lại.")


if __name__ == "__main__":
    main()
