import os
import sys
import time

import cv2

# Xem giải thích chi tiết trong run_gui.py - đảm bảo config.py/models/outputs
# luôn được tìm ngay tại thư mục chứa file .exe khi đã đóng gói, không bị
# đóng cứng bên trong file thực thi.
_APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
sys.path.insert(0, _APP_DIR)
os.chdir(_APP_DIR)

import config
from channels.flow_helmet_channel import FlowHelmetChannel
from channels.redlight_channel import RedLightChannel


def build_enabled_channels():
    channels = []

    if config.ENABLE_CHANNEL1:
        channels.append(FlowHelmetChannel(config.SOURCE_CH1))

    if config.ENABLE_CHANNEL2:
        channels.append(RedLightChannel(config.SOURCE_CH2))

    return channels


def main():
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    channels = build_enabled_channels()
    if not channels:
        print("Chưa bật kênh nào cả — kiểm tra ENABLE_CHANNEL1 / ENABLE_CHANNEL2 trong config.py")
        return

    for ch in channels:
        ch.start()
        print(f"Đã khởi động: {ch.name}")

    try:
        while True:
            any_alive = False
            for ch in channels:
                if ch.thread is not None and ch.thread.is_alive():
                    any_alive = True

                frame = ch.get_latest_frame()
                if frame is not None:
                    cv2.imshow(ch.name, frame)

            if not any_alive:
                # tất cả video đã đọc hết / lỗi mở video ngay từ đầu
                break

            # ESC để thoát toàn bộ chương trình (đóng cả 2 kênh cùng lúc)
            if cv2.waitKey(1) == 27:
                break

            time.sleep(0.005)  # nhường CPU cho các thread xử lý, tránh vòng lặp hiển thị quay quá nhanh
    finally:
        for ch in channels:
            ch.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
