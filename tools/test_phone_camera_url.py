"""
Script test URL camera điện thoại - hỗ trợ cả DroidCam và IP Webcam, thử vài
biến thể endpoint hay gặp của từng app, in rõ lỗi OpenCV cho từng cái.

CÁCH DÙNG:
    python test_phone_camera_url.py 192.168.1.53

(thay đúng WiFi IP hiện trong app trên điện thoại - đảm bảo app đang mở và ở
màn hình đang chạy server lúc chạy script này)

Nếu biết chắc đang dùng app nào, chạy kèm tên app cho nhanh (bỏ qua thử app kia):
    python test_phone_camera_url.py 192.168.1.53 droidcam
    python test_phone_camera_url.py 192.168.1.53 ipwebcam
"""
import sys
import time

import cv2

if len(sys.argv) < 2:
    print("Cách dùng: python test_phone_camera_url.py <ip_dien_thoai> [droidcam|ipwebcam]")
    sys.exit(1)

ip = sys.argv[1]
app_filter = sys.argv[2].lower() if len(sys.argv) > 2 else None

candidates = []
if app_filter in (None, "droidcam"):
    candidates += [
        (f"http://{ip}:4747/mjpegfeed?640x480", "DroidCam"),
        (f"http://{ip}:4747/mjpegfeed", "DroidCam"),
        (f"http://{ip}:4747/video", "DroidCam"),
    ]
if app_filter in (None, "ipwebcam"):
    candidates += [
        (f"http://{ip}:8080/video", "IP Webcam"),
    ]

print(f"Đang test {len(candidates)} URL khả dĩ tại IP {ip}...\n")

any_ok = False
for i, (url, app_name) in enumerate(candidates):
    print(f"--- [{app_name}] Thử: {url}")
    t0 = time.time()
    cap = cv2.VideoCapture(url)
    opened = cap.isOpened()
    print(f"    isOpened() = {opened}  (mất {time.time()-t0:.1f}s)")

    if opened:
        ret, frame = cap.read()
        if ret and frame is not None:
            out = f"phone_cam_test_{i}.jpg"
            cv2.imwrite(out, frame)
            print(f"    ĐỌC FRAME OK ({frame.shape[1]}x{frame.shape[0]}) -> đã lưu {out}")
            any_ok = True
        else:
            print("    isOpened=True nhưng đọc frame LỖI - stream có thể không đúng định dạng MJPEG mà OpenCV hiểu được.")
    cap.release()
    print()

if any_ok:
    print("=> Dùng đúng URL vừa báo 'ĐỌC FRAME OK' ở trên, dán vào ô URL trong GUI.")
else:
    print("=> Không URL nào đọc được frame. Kiểm tra lại:")
    print("   1. App trên điện thoại có đang mở + ở màn hình chạy server không?")
    print(f"   2. Mở http://{ip}:PORT bằng TRÌNH DUYỆT trên PC trước (PORT=4747 cho DroidCam, 8080 cho IP Webcam) - nếu trình duyệt cũng không vào được thì là vấn đề MẠNG (PC/điện thoại khác dải IP, hoặc firewall chặn port), không phải sai endpoint.")
