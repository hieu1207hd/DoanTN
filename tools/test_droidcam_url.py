"""
Script test trực tiếp URL DroidCam - thử vài biến thể endpoint hay gặp, in rõ
lỗi OpenCV trả về cho từng cái, KHÔNG qua GUI để dễ debug hơn.

CÁCH DÙNG:
    python test_droidcam_url.py 192.168.1.53

(thay đúng WiFi IP hiện trong app DroidCam trên điện thoại - đảm bảo DroidCam
đang mở và ở màn hình chạy server lúc chạy script này)
"""
import sys
import time

import cv2

if len(sys.argv) < 2:
    print("Cách dùng: python test_droidcam_url.py <ip_dien_thoai>")
    print("Ví dụ:    python test_droidcam_url.py 192.168.1.53")
    sys.exit(1)

ip = sys.argv[1]
port = 4747

candidates = [
    f"http://{ip}:{port}/mjpegfeed?640x480",
    f"http://{ip}:{port}/mjpegfeed",
    f"http://{ip}:{port}/video",
    f"http://{ip}:{port}/videofeed",
]

print(f"Đang test {len(candidates)} URL khả dĩ cho DroidCam tại {ip}:{port}...\n")

any_ok = False
for url in candidates:
    print(f"--- Thử: {url}")
    t0 = time.time()
    cap = cv2.VideoCapture(url)
    opened = cap.isOpened()
    print(f"    isOpened() = {opened}  (mất {time.time()-t0:.1f}s)")

    if opened:
        ret, frame = cap.read()
        if ret and frame is not None:
            out = f"droidcam_test_{candidates.index(url)}.jpg"
            cv2.imwrite(out, frame)
            print(f"    ĐỌC FRAME OK ({frame.shape[1]}x{frame.shape[0]}) -> đã lưu {out}")
            any_ok = True
        else:
            print("    isOpened=True nhưng đọc frame LỖI (ret=False) - stream có thể không đúng định dạng MJPEG mà OpenCV hiểu được.")
    cap.release()
    print()

if any_ok:
    print("=> Dùng đúng URL vừa báo 'ĐỌC FRAME OK' ở trên, dán vào ô URL trong GUI.")
else:
    print("=> Không URL nào đọc được frame. Khả năng cao là vấn đề MẠNG (PC và điện thoại")
    print("   không cùng dải IP, hoặc firewall chặn port 4747) chứ không phải sai endpoint -")
    print("   quay lại kiểm tra bước mở http://{}:{} bằng TRÌNH DUYỆT trên PC trước.".format(ip, port))
