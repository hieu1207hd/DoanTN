"""
Script tìm đúng chỉ số (index) camera của DroidCam Client - KHÔNG dùng
cv2.imshow (tránh lỗi thiếu GUI support/GTK trên bản opencv-python-headless,
vốn là bản đúng cần dùng cho project này vì hiển thị qua PyQt5).

CÁCH DÙNG:
1. Mở DroidCam Client, kết nối vào điện thoại trước (đã thấy hình điện thoại
   hiện ngay trong cửa sổ DroidCam Client).
2. Chạy: python find_camera_index.py
3. Script thử lần lượt index 0..5, mở được thì CHỤP 1 ẢNH lưu ra file
   camera_index_X.jpg trong cùng thư mục.
4. Mở lần lượt các file camera_index_0.jpg, camera_index_1.jpg... bằng File
   Explorer - file nào là hình từ ĐIỆN THOẠI (không phải mặt bạn qua webcam
   laptop) thì số X trong tên file đó chính là "Chỉ số camera" cần điền
   trong GUI.
"""
import cv2

MAX_INDEX_TO_TRY = 6

print("Đang quét camera, có thể mất vài giây do vài index không tồn tại...")
found_any = False

for idx in range(MAX_INDEX_TO_TRY):
    cap = cv2.VideoCapture(idx)
    if not cap.isOpened():
        print(f"[index {idx}] Không có camera / không mở được - bỏ qua.")
        cap.release()
        continue

    # Đọc vài frame đầu bỏ đi - nhiều webcam/camera ảo trả về frame đen/lỗi
    # ở lần đọc đầu tiên lúc mới mở, cần "khởi động" vài frame trước khi
    # frame thực sự ổn định.
    ret, frame = False, None
    for _ in range(5):
        ret, frame = cap.read()

    if not ret or frame is None:
        print(f"[index {idx}] Mở được nhưng đọc frame lỗi - bỏ qua.")
        cap.release()
        continue

    out_path = f"camera_index_{idx}.jpg"
    cv2.imwrite(out_path, frame)
    print(f"[index {idx}] OK - đã lưu {out_path} ({frame.shape[1]}x{frame.shape[0]}) - MỞ FILE NÀY ĐỂ XEM.")
    found_any = True
    cap.release()

if not found_any:
    print("\nKhông tìm thấy camera nào mở được ở index 0-5. Kiểm tra lại DroidCam Client "
          "đã kết nối điện thoại chưa, hoặc thử tăng MAX_INDEX_TO_TRY lên cao hơn.")
else:
    print("\nXong. Mở lần lượt các file camera_index_*.jpg vừa lưu, tìm đúng ảnh chụp từ "
          "điện thoại rồi dùng đúng số index đó trong GUI.")
