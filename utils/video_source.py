import queue
import threading
import time

import cv2


def is_live_source(source):
    if isinstance(source, int):
        return True
    if isinstance(source, str) and source.lower().startswith(("rtsp://", "http://", "https://", "udp://")):
        return True
    return False


class LiveFrameGrabber:
    """Đọc frame liên tục từ camera/luồng mạng (webcam, điện thoại làm IP
    camera, CCTV ngoài trời qua RTSP...) trong 1 thread riêng, LUÔN giữ frame
    MỚI NHẤT (drop frame cũ nếu xử lý theo không kịp) - đúng nguyên tắc real-
    time của hệ thống ITS, khác với đọc file video (đọc tuần tự, không bỏ
    frame nào, xem channels/*.py).

    TỰ KẾT NỐI LẠI khi mất kết nối giữa chừng (rớt Wi-Fi, camera khởi động
    lại, RTSP timeout...) - đây là khác biệt quan trọng so với chạy video
    file có sẵn: mạng thực tế KHÔNG ổn định tuyệt đối, nếu không tự reconnect
    thì cả channel sẽ dừng hẳn chỉ vì 1 lần rớt mạng thoáng qua, phải vào GUI
    bấm Dừng/Bắt đầu lại thủ công - không chấp nhận được cho hệ thống chạy
    24/7 ngoài hiện trường.
    """

    def __init__(self, source, reconnect_delay=2.0, max_reconnect_attempts=None):
        self.source = source
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts  # None = thử lại vô hạn

        self.cap = cv2.VideoCapture(source)
        self._configure_capture()

        self.opened = self.cap.isOpened()
        # Public - GUI có thể đọc để hiện trạng thái "Mất kết nối, đang thử
        # lại..." thay vì tưởng nhầm hệ thống bị treo/đứng hình.
        self.connected = self.opened

        self._queue = queue.Queue(maxsize=1)
        self._stop_event = threading.Event()
        self._thread = None

    def _configure_capture(self):
        try:
            # Giảm buffer nội bộ về mức thấp nhất (tuỳ backend/driver có hỗ trợ hay không,
            # không hỗ trợ cũng không sao vì grabber thread bên dưới đã tự lo việc này).
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

    def start(self):
        # Nơi gọi (channels/*.py) đã kiểm tra self.opened NGAY SAU khi tạo
        # grabber để báo lỗi sớm nếu source sai hẳn (URL/index không hợp lệ,
        # gõ nhầm IP...) - fail-fast ở bước NÀY là đúng, người dùng cần biết
        # ngay lúc setup thay vì app cứ lặng lẽ thử lại vô tận với 1 địa chỉ
        # sai. self._grab_loop() dưới đây chỉ lo trường hợp KẾT NỐI ĐÃ THÀNH
        # CÔNG rồi mới rớt giữa chừng (rớt Wi-Fi, camera khởi động lại, RTSP
        # timeout...) - tình huống này KHÔNG nên dừng cả channel, phải tự thử
        # kết nối lại (xem _reconnect()).
        self._thread = threading.Thread(target=self._grab_loop, daemon=True)
        self._thread.start()

    def _reconnect(self):
        """Thử mở lại kết nối, lặp lại mỗi reconnect_delay giây cho tới khi
        thành công, hết self._stop_event, hoặc vượt max_reconnect_attempts.
        Trả về True nếu kết nối lại thành công."""
        attempts = 0
        while not self._stop_event.is_set():
            attempts += 1
            self.cap.release()
            time.sleep(self.reconnect_delay)
            if self._stop_event.is_set():
                return False

            self.cap = cv2.VideoCapture(self.source)
            self._configure_capture()
            if self.cap.isOpened():
                self.connected = True
                return True

            if self.max_reconnect_attempts is not None and attempts >= self.max_reconnect_attempts:
                return False
        return False

    def _grab_loop(self):
        if not self.cap.isOpened():
            self.connected = False
            if not self._reconnect():
                return

        while not self._stop_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                # Đọc lỗi giữa chừng - KHÔNG thoát thread ngay (bản gốc làm
                # vậy, khiến cả channel dừng hẳn chỉ vì 1 lần rớt mạng) - thử
                # kết nối lại, chỉ thực sự dừng nếu _reconnect() bỏ cuộc
                # (vượt max_reconnect_attempts hoặc đã gọi stop()).
                self.connected = False
                if not self._reconnect():
                    break
                continue

            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
            self._queue.put(frame)

        self.cap.release()

    def read(self, timeout=2.0):
        try:
            frame = self._queue.get(timeout=timeout)
            return True, frame
        except queue.Empty:
            return False, None

    def stop(self):
        self._stop_event.set()
