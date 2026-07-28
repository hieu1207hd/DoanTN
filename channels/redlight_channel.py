import os
import queue
import threading
import time
from datetime import datetime

import cv2

import config
from core.redlight import RedLightDetector, RedLightViolationChecker
from core.tracker import Tracker
from modules.plate import PlateDetector, PlateReader, PlateVoteAggregator, sharpness_score
from utils.evidence import save_evidence
from utils.fps_counter import FPSCounter
from utils.logger import ViolationLogger
from utils.video_source import LiveFrameGrabber, is_live_source


class RedLightChannel:
    name = "Channel 2 - Red Light"

    def __init__(self, source):
        self.source = source
        self.frame_queue = queue.Queue(maxsize=1)
        self.violation_queue = queue.Queue()  # xem giải thích trong FlowHelmetChannel
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()  # set = đang tạm dừng
        self.thread = None

        # Public để GUI đọc/ghi trực tiếp (xem giải thích trong FlowHelmetChannel).
        self.tracker = None
        self.grabber = None  # LiveFrameGrabber nếu nguồn là camera/URL - None nếu là file video (xem _run())
        self.detector = None
        self.checker = None
        self.plate_detector = None
        self.plate_reader = None
        self.plate_votes = None
        self.plate_crops = {}
        self.plate_frame_count = {}
        self.is_red = False
        self.fps_counter = FPSCounter()
        self.current_fps = 0.0

    def start(self):
        self.thread = threading.Thread(target=self._run, name=self.name, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop_event.set()

    def pause(self):
        self._pause_event.set()

    def resume(self):
        self._pause_event.clear()

    @property
    def paused(self):
        return self._pause_event.is_set()

    def get_latest_frame(self):
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None

    def _run(self):
        live = is_live_source(self.source)

        if live:
            grabber = LiveFrameGrabber(self.source)
            self.grabber = grabber  # public để GUI hiện trạng thái mất kết nối/đang thử lại
            if not grabber.opened:
                print(f"[{self.name}] Không mở được camera/luồng: {self.source}")
                return
            grabber.start()
            read_frame = grabber.read
            release = grabber.stop
            frame_interval = None
        else:
            cap = cv2.VideoCapture(self.source)
            if not cap.isOpened():
                print(f"[{self.name}] Không đọc được video: {self.source} "
                      f"(kênh này sẽ không chạy, kiểm tra lại config.SOURCE_CH2)")
                return
            read_frame = cap.read
            release = cap.release

            frame_interval = None
            if config.SYNC_TO_REAL_FPS:
                fps = cap.get(cv2.CAP_PROP_FPS) or 25
                frame_interval = 1.0 / fps

        # Không đọc trước 1 frame "bỏ đi" chỉ để lấy kích thước — stop_line_y
        # phụ thuộc chiều cao frame nên khởi tạo NGAY trong vòng lặp, lần đầu tiên.
        self.tracker = Tracker(
            model_path=config.VEHICLE_MODEL,
            allowed_classes=config.ALLOWED_VEHICLE_CLASSES,
            device=config.DEVICE,
            conf=config.VEHICLE_CONF,
        )

        self.detector = RedLightDetector(
            roi=config.TRAFFIC_LIGHT_ROI,
            lower1=config.RED_HSV_LOWER1, upper1=config.RED_HSV_UPPER1,
            lower2=config.RED_HSV_LOWER2, upper2=config.RED_HSV_UPPER2,
            pixel_threshold=config.RED_PIXEL_THRESHOLD,
        )

        if config.ENABLE_PLATE:
            self.plate_detector = PlateDetector(config.PLATE_MODEL, conf=config.PLATE_CONF, device=config.DEVICE)
            self.plate_reader = PlateReader(
                langs=config.PLATE_OCR_LANGS,
                gpu=config.PLATE_OCR_GPU,
                allowlist=config.PLATE_OCR_ALLOWLIST,
                min_sharpness=config.PLATE_MIN_SHARPNESS,
                upscale_height=config.PLATE_UPSCALE_HEIGHT,
                model_storage_directory=config.PLATE_OCR_MODEL_DIR,
            )
            self.plate_votes = PlateVoteAggregator(
                window=config.PLATE_VOTE_WINDOW,
                min_count=config.PLATE_VOTE_MIN_COUNT,
                max_attempts=config.PLATE_MAX_ATTEMPTS,
            )

        # Vi phạm "vượt đèn đỏ" giờ lưu RIÊNG (thư mục ảnh + CSV riêng, không
        # còn dùng chung config.VIOLATION_LOG_CSV với kênh mũ bảo hiểm nữa).
        os.makedirs(config.RED_LIGHT_DIR, exist_ok=True)
        logger = ViolationLogger(config.RED_LIGHT_LOG_CSV)

        stop_line_y = None
        geometry_ready = False

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                time.sleep(0.1)
                continue

            loop_start = time.time()

            ret, raw_frame = read_frame()
            if not ret:
                break
            frame = self._resize(raw_frame)
            # Giữ lại raw_frame (ảnh gốc, chưa resize) để cắt ảnh vi phạm và
            # crop biển số với nhiều pixel thật hơn - xem giải thích tương tự
            # trong FlowHelmetChannel._run(). Bbox từ tracker luôn là toạ độ
            # trên frame ĐÃ resize, cần quy đổi lại bằng scale_x/scale_y.
            scale_x = raw_frame.shape[1] / frame.shape[1]
            scale_y = raw_frame.shape[0] / frame.shape[0]

            if not geometry_ready:
                stop_line_y = int(frame.shape[0] * config.STOP_LINE_Y_RATIO)
                self.checker = RedLightViolationChecker(stop_line_y, direction=config.DIRECTION)
                geometry_ready = True

            tracks, _ = self.tracker.track(frame)  # kênh này không cần context (person), luôn rỗng
            is_red = self.detector.is_red(frame)
            new_violations = self.checker.update(tracks, is_red)

            # Đọc biển số cho MỌI xe đang track (không chỉ xe vi phạm) - cùng
            # cơ chế với FlowHelmetChannel: chỉ chạy detector+OCR khi biển số
            # của track_id CHƯA được "chốt", VÀ chỉ mỗi N frame/xe (xem
            # PLATE_PROCESS_EVERY_N_FRAMES trong config.py - đây là nguyên
            # nhân chính gây tụt FPS nếu bỏ qua bước throttle này).
            if self.plate_detector is not None:
                for obj in tracks:
                    obj_id = obj["id"]
                    if not self.plate_votes.should_attempt(obj_id):
                        continue

                    self.plate_frame_count[obj_id] = self.plate_frame_count.get(obj_id, 0) + 1
                    if self.plate_frame_count[obj_id] % config.PLATE_PROCESS_EVERY_N_FRAMES != 0:
                        continue

                    x1, y1, x2, y2 = obj["bbox"]
                    vx1, vy1 = int(x1 * scale_x), int(y1 * scale_y)
                    vx2, vy2 = int(x2 * scale_x), int(y2 * scale_y)
                    vehicle_crop = raw_frame[vy1:vy2, vx1:vx2]

                    # Lọc mờ SỚM trên cả crop xe (rẻ, không cần chạy model)
                    # TRƯỚC KHI chạy plate_detector - xem giải thích trong
                    # FlowHelmetChannel._run().
                    if (config.PLATE_MIN_VEHICLE_SHARPNESS > 0
                            and sharpness_score(vehicle_crop) < config.PLATE_MIN_VEHICLE_SHARPNESS):
                        continue

                    plate_box = self.plate_detector.detect(vehicle_crop)
                    self.plate_votes.register_attempt(obj_id)
                    if plate_box is None:
                        continue
                    bx1, by1, bx2, by2 = plate_box
                    plate_crop = vehicle_crop[by1:by2, bx1:bx2]
                    ph, pw = plate_crop.shape[:2] if plate_crop is not None else (0, 0)
                    if ph >= config.MIN_PLATE_CROP_HEIGHT and pw >= config.MIN_PLATE_CROP_WIDTH:
                        raw_text, _plate_conf = self.plate_reader.read(plate_crop)
                        self.plate_votes.update(obj_id, raw_text)
                        self.plate_crops[obj_id] = plate_crop

            for obj_id in new_violations:
                match = next((o for o in tracks if o["id"] == obj_id), None)
                if match is not None:
                    x1, y1, x2, y2 = match["bbox"]
                    vx1, vy1 = int(x1 * scale_x), int(y1 * scale_y)
                    vx2, vy2 = int(x2 * scale_x), int(y2 * scale_y)
                    # 3 ảnh bằng chứng theo đề xuất giảng viên (áp dụng đồng
                    # nhất cho cả 2 loại vi phạm - xem utils/evidence.py):
                    # (1) ảnh TOÀN CẢNH có vẽ bbox khoanh phương tiện vi phạm,
                    # (2) crop RIÊNG phương tiện đó, (3) crop biển số lấy từ
                    # cache self.plate_crops (frame gần nhất đọc thành công
                    # biển số của track_id này).
                    vehicle_crop = raw_frame[vy1:vy2, vx1:vx2]

                    scene_img = raw_frame.copy()
                    cv2.rectangle(scene_img, (vx1, vy1), (vx2, vy2), (0, 0, 255), 3)

                    plate_img = self.plate_crops.get(obj_id)
                    scene_path, vehicle_path, plate_path = save_evidence(
                        config.RED_LIGHT_DIR, obj_id, scene_img, vehicle_crop, plate_img,
                    )
                    plate_text = self.plate_votes.get(obj_id) if self.plate_votes else ""
                    logger.log(obj_id, plate_text, "RED_LIGHT", scene_path, vehicle_path, plate_path)
                    self.violation_queue.put({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "channel": self.name,
                        "type": "RED_LIGHT",
                        "track_id": obj_id,
                        "plate": plate_text or "",
                        "scene_image": scene_path,
                        "vehicle_image": vehicle_path,
                        "plate_image": plate_path,
                    })

            for obj in tracks:
                x1, y1, x2, y2 = obj["bbox"]
                is_violator = obj["id"] in self.checker.violated_ids
                color = (0, 0, 255) if is_violator else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                plate_text = self.plate_votes.get(obj["id"]) if self.plate_votes else None
                if plate_text:
                    cv2.putText(frame, plate_text, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            self.current_fps = self.fps_counter.update()
            self.is_red = is_red  # public để GUI đọc hiện trạng đèn cho bảng số liệu
            self._draw_overlay(frame, self.checker.stop_line_y, is_red, self.detector.roi)
            self._push_frame(frame)

            if frame_interval is not None:
                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        release()

    @staticmethod
    def _draw_overlay(frame, stop_line_y, is_red, traffic_light_roi):
        # Vẽ stop_line (đổi màu theo đèn - vẫn hữu ích để tham chiếu trực
        # quan trên video), số liệu (Vượt đèn đỏ/FPS/trạng thái đèn) giờ hiển
        # thị ở bảng riêng trên GUI, không vẽ đè lên video nữa.
        rl_color = (0, 0, 255) if is_red else (0, 255, 0)
        cv2.line(frame, (0, stop_line_y), (frame.shape[1], stop_line_y), rl_color, 2)

        # Vẽ ROI đèn giao thông (nét đứt vàng) - TRƯỚC ĐÂY không vẽ gì cả
        # (chỉ có preview lúc đang kéo chuột), khiến chỉnh ROI này qua
        # ROIPanel không thấy phản hồi trực quan gì, tưởng nhầm là không có
        # tác dụng dù giá trị vẫn được áp dụng đúng. Đọc self.detector.roi
        # (giá trị SỐNG, có thể đã bị ROIPanel chỉnh) chứ không phải hằng số
        # config.TRAFFIC_LIGHT_ROI tĩnh, để luôn khớp đúng vùng đang dùng
        # thật để detect màu đèn.
        rx1, ry1, rx2, ry2 = traffic_light_roi
        roi_color = (0, 220, 255)
        step = 8
        for x in range(rx1, rx2, step * 2):
            cv2.line(frame, (x, ry1), (min(x + step, rx2), ry1), roi_color, 2)
            cv2.line(frame, (x, ry2), (min(x + step, rx2), ry2), roi_color, 2)
        for y in range(ry1, ry2, step * 2):
            cv2.line(frame, (rx1, y), (rx1, min(y + step, ry2)), roi_color, 2)
            cv2.line(frame, (rx2, y), (rx2, min(y + step, ry2)), roi_color, 2)

    def _push_frame(self, frame):
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
        self.frame_queue.put(frame)

    @staticmethod
    def _resize(frame):
        h, w = frame.shape[:2]
        new_w = config.RESIZE_WIDTH
        new_h = int(h * (new_w / w))
        return cv2.resize(frame, (new_w, new_h))
