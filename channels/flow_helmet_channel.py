import os
import queue
import threading
import time
from datetime import datetime

import cv2

import config
from core.flow import TrafficFlow
from core.tracker import Tracker
from modules.helmet import HelmetDetector, HelmetVoteAggregator
from modules.plate import PlateDetector, PlateReader, PlateVoteAggregator, sharpness_score
from utils.bbox import find_best_overlap
from utils.crop import crop_head
from utils.evidence import save_evidence
from utils.fps_counter import FPSCounter
from utils.logger import ViolationLogger
from utils.video_source import LiveFrameGrabber, is_live_source


class FlowHelmetChannel:
    name = "Channel 1 - Flow + Helmet"

    def __init__(self, source):
        self.source = source
        self.frame_queue = queue.Queue(maxsize=1)
        # Hàng đợi sự kiện vi phạm - đẩy vào mỗi khi có vi phạm mới, GUI
        # (tab "Vi phạm") đọc bằng get_nowait() theo cùng cơ chế polling với
        # frame_queue, không giới hạn maxsize vì có thể nhiều vi phạm dồn dập
        # mà GUI chưa kịp đọc hết - không được phép rớt mất 1 vi phạm nào
        # (khác với frame, rớt 1 frame hình không sao).
        self.violation_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()  # set = đang tạm dừng
        self.thread = None

        # Các attribute này chỉ có giá trị thật SAU KHI start() và _run() đã
        # khởi tạo xong (vài chục ms đầu). Public để GUI đọc/ghi trực tiếp:
        # - đọc self.flow / self.helmet_votes để hiện số liệu
        # - ghi self.tracker.vehicle_conf = x, self.helmet_detector.conf = x
        #   để chỉnh ngưỡng conf NGAY LẬP TỨC khi kênh đang chạy (live-tuning),
        #   không cần dừng/khởi động lại kênh.
        self.tracker = None
        self.grabber = None  # LiveFrameGrabber nếu nguồn là camera/URL - None nếu là file video (xem _run())
        self.helmet_detector = None
        self.helmet_votes = None
        self.plate_detector = None
        self.plate_reader = None
        self.plate_votes = None
        self.plate_crops = {}
        self.plate_frame_count = {}
        self.detect_zone_y = None
        self.flow = None
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
            # Camera trực tiếp / luồng mạng: dùng grabber luôn giữ frame MỚI NHẤT
            # để đảm bảo real-time, không bị trễ dần khi xử lý chậm hơn camera.
            grabber = LiveFrameGrabber(self.source)
            self.grabber = grabber  # public để GUI hiện trạng thái mất kết nối/đang thử lại
            if not grabber.opened:
                print(f"[{self.name}] Không mở được camera/luồng: {self.source}")
                return
            grabber.start()
            read_frame = grabber.read
            release = grabber.stop
            frame_interval = None  # camera đã tự chạy đúng tốc độ thực, không cần throttle
        else:
            # File video thường: đọc tuần tự từng frame, không bỏ frame nào
            # (quan trọng khi cần test độ chính xác/đếm đúng số liệu).
            cap = cv2.VideoCapture(self.source)
            if not cap.isOpened():
                print(f"[{self.name}] Không đọc được video: {self.source}")
                return
            read_frame = cap.read
            release = cap.release

            frame_interval = None
            if config.SYNC_TO_REAL_FPS:
                fps = cap.get(cv2.CAP_PROP_FPS) or 25
                frame_interval = 1.0 / fps

        # Không đọc trước 1 frame "bỏ đi" chỉ để lấy kích thước — làm vậy sẽ mất
        # đúng frame đầu tiên của video/camera. line_y phụ thuộc chiều cao
        # frame nên được khởi tạo NGAY BÊN TRONG vòng lặp, ở lần lặp đầu tiên.
        self.tracker = Tracker(
            model_path=config.VEHICLE_MODEL,
            allowed_classes=config.ALLOWED_VEHICLE_CLASSES,
            context_classes=(config.PERSON_CLASS_ID,) if config.ENABLE_HELMET else (),
            context_conf=config.PERSON_CONF,
            device=config.DEVICE,
            conf=config.VEHICLE_CONF,
        )

        if config.ENABLE_HELMET:
            self.helmet_detector = HelmetDetector(config.HELMET_MODEL, conf=config.HELMET_CONF, device=config.DEVICE)
            self.helmet_votes = HelmetVoteAggregator(
                window=config.HELMET_VOTE_WINDOW,
                min_no_helmet=config.HELMET_VOTE_MIN_COUNT,
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

        # Vi phạm "không đội mũ" giờ lưu RIÊNG (thư mục ảnh + CSV riêng, không
        # còn dùng chung config.VIOLATION_LOG_CSV với kênh vượt đèn đỏ nữa).
        os.makedirs(config.NO_HELMET_DIR, exist_ok=True)
        logger = ViolationLogger(config.NO_HELMET_LOG_CSV)

        line_y = None
        geometry_ready = False

        while not self._stop_event.is_set():
            if self._pause_event.is_set():
                # Tạm dừng: KHÔNG gọi read_frame() (giữ nguyên vị trí đang
                # đọc dở của file video, không tua về đầu) - chỉ ngủ ngắn rồi
                # kiểm tra lại. Thread vẫn sống, mọi state (tracker ID,
                # helmet_votes, plate_votes...) giữ nguyên - khác hẳn Stop
                # (huỷ hẳn thread, mất toàn bộ state, lần Start sau đọc lại
                # từ đầu file).
                time.sleep(0.1)
                continue

            loop_start = time.time()

            ret, raw_frame = read_frame()
            if not ret:
                break
            frame = self._resize(raw_frame)
            # Toạ độ bbox mà tracker trả về là trên ẢNH ĐÃ RESIZE (nhỏ, để
            # tracking cho nhanh). Muốn cắt đầu ra để check mũ bảo hiểm với
            # nhiều pixel thật hơn, phải quy đổi bbox này sang toạ độ trên
            # raw_frame (ảnh gốc, chưa resize) bằng tỉ lệ scale dưới đây.
            scale_x = raw_frame.shape[1] / frame.shape[1]
            scale_y = raw_frame.shape[0] / frame.shape[0]

            if not geometry_ready:
                line_y = int(frame.shape[0] * config.LINE_Y_RATIO)
                if config.ENABLE_FLOW:
                    self.flow = TrafficFlow(line_y=line_y, direction=config.DIRECTION)
                # detect_zone_y: toạ độ Y tuyệt đối (trên frame ĐÃ RESIZE),
                # tính 1 LẦN từ DETECT_ZONE_RATIO lúc khởi động - lưu thành
                # attribute public (thay vì đọc config.DETECT_ZONE_RATIO lại
                # mỗi frame) để GUI có thể chỉnh trực tiếp lúc đang chạy qua
                # ROIPanel (xem gui/roi_panel.py), giống cơ chế live-tuning
                # conf đã có.
                self.detect_zone_y = int(frame.shape[0] * config.DETECT_ZONE_RATIO)
                geometry_ready = True

            tracks, persons = self.tracker.track(frame)

            if self.flow is not None:
                self.flow.update(tracks)

            for obj in tracks:
                x1, y1, x2, y2 = obj["bbox"]
                obj_id = obj["id"]
                cls = obj["class_id"]
                # Tra tên hiển thị theo dict thay vì if/else nhị phân (bản gốc
                # chỉ có 2 loại xe COCO nên viết tắt được "Car" vs "Motorbike"
                # - giờ model có 4 loại (bus/car/motorbike/truck) nên PHẢI tra
                # dict, viết if/else nhị phân sẽ hiển thị sai tên cho bus/truck).
                label = config.VEHICLE_CLASS_NAMES.get(cls, f"Class{cls}")
                is_motorbike = (cls == config.MOTORBIKE_CLASS_ID)

                # Ô tô không cần đội mũ bảo hiểm -> KHÔNG áp dụng check này cho
                # ô tô (status=None nghĩa là "không áp dụng", khác với UNKNOWN
                # là "có áp dụng nhưng chưa xác định được"). Ngoài ra người lái
                # ô tô ngồi trong khoang kín, hầu như không thể detect ra
                # "person" riêng -> nếu vẫn chạy find_best_overlap cho ô tô sẽ
                # luôn ra "KHONG THAY NGUOI" một cách vô nghĩa.
                status, color = None, (0, 255, 0)
                cy = (y1 + y2) // 2

                # Đọc biển số cho MỌI xe (cả car lẫn motorbike, không chỉ xe vi
                # phạm) - chạy TRƯỚC khối check mũ bảo hiểm bên dưới để nếu xe
                # này vi phạm ngay trong frame này, đã có sẵn crop biển số mới
                # nhất để lưu làm ảnh bằng chứng thứ 2. Chỉ chạy detector+OCR
                # (tốn compute) khi: xe đã đủ gần (tái dùng DETECT_ZONE_RATIO)
                # VÀ biển số của track_id này CHƯA được "chốt" - sau khi chốt
                # thì chỉ đọc từ cache, không tốn thêm compute nữa. self.plate_crops
                # luôn giữ crop THÀNH CÔNG gần nhất của mỗi track_id để dùng
                # làm ảnh bằng chứng khi xe đó vi phạm (không nhất thiết phải
                # đúng khung hình xảy ra vi phạm).
                plate_text = None
                if self.plate_detector is not None:
                    in_plate_zone = cy > self.detect_zone_y

                    if in_plate_zone and self.plate_votes.should_attempt(obj_id):
                        self.plate_frame_count[obj_id] = self.plate_frame_count.get(obj_id, 0) + 1
                        # Chỉ thực sự chạy detector+OCR (nặng) mỗi N frame cho
                        # từng xe - xem giải thích PLATE_PROCESS_EVERY_N_FRAMES
                        # trong config.py (nguyên nhân chính gây tụt FPS).
                        if self.plate_frame_count[obj_id] % config.PLATE_PROCESS_EVERY_N_FRAMES == 0:
                            vx1, vy1 = int(x1 * scale_x), int(y1 * scale_y)
                            vx2, vy2 = int(x2 * scale_x), int(y2 * scale_y)
                            vehicle_crop = raw_frame[vy1:vy2, vx1:vx2]

                            # Lọc mờ SỚM trên cả crop xe (rẻ, không cần chạy
                            # model) TRƯỚC KHI chạy plate_detector - xe đang
                            # motion-blur thì vùng biển số bên trong hầu như
                            # chắc chắn cũng mờ, chạy detector+OCR chỉ phí.
                            if (config.PLATE_MIN_VEHICLE_SHARPNESS <= 0
                                    or sharpness_score(vehicle_crop) >= config.PLATE_MIN_VEHICLE_SHARPNESS):
                                plate_box = self.plate_detector.detect(vehicle_crop)
                                self.plate_votes.register_attempt(obj_id)

                                if plate_box is not None:
                                    bx1, by1, bx2, by2 = plate_box
                                    plate_crop = vehicle_crop[by1:by2, bx1:bx2]
                                    ph, pw = plate_crop.shape[:2] if plate_crop is not None else (0, 0)

                                    if ph >= config.MIN_PLATE_CROP_HEIGHT and pw >= config.MIN_PLATE_CROP_WIDTH:
                                        raw_text, _plate_conf = self.plate_reader.read(plate_crop)
                                        self.plate_votes.update(obj_id, raw_text)
                                        self.plate_crops[obj_id] = plate_crop

                    plate_text = self.plate_votes.get(obj_id)

                if self.helmet_detector is not None and is_motorbike:
                    status, color = "UNKNOWN", (0, 255, 255)
                    in_detect_zone = cy > self.detect_zone_y

                    if in_detect_zone:
                        # Bbox xe (class 3) chỉ bao cái xe, KHÔNG chắc bao luôn
                        # đầu người ngồi trên xe -> tìm person chồng lấn nhiều
                        # nhất lên xe này, cắt đầu từ bbox NGƯỜI đó thay vì bbox xe.
                        rider = find_best_overlap(obj["bbox"], persons)

                        if rider is None:
                            status, color = "KHONG THAY NGUOI", (160, 160, 160)
                        else:
                            px1, py1, px2, py2 = rider["bbox"]
                            rx1, ry1 = int(px1 * scale_x), int(py1 * scale_y)
                            rx2, ry2 = int(px2 * scale_x), int(py2 * scale_y)
                            head_crop = crop_head(raw_frame, rx1, ry1, rx2, ry2, config.PERSON_HEAD_RATIO)

                            crop_h, crop_w = head_crop.shape[:2] if head_crop is not None else (0, 0)
                            if crop_h < config.MIN_HEAD_CROP_HEIGHT or crop_w < config.MIN_HEAD_CROP_WIDTH:
                                # Xe quá xa camera -> crop còn lại quá ít pixel để tin cậy.
                                # Báo rõ "QUA XA" thay vì cố đoán trên ảnh gần như không
                                # còn thông tin (tránh cả false positive lẫn false negative).
                                status, color = "QUA XA", (160, 160, 160)
                            else:
                                result = self.helmet_detector.detect(head_crop)

                                if result is False:
                                    status, color = "NO HELMET", (0, 0, 255)
                                elif result is True:
                                    status, color = "HELMET", (0, 255, 0)

                                if self.helmet_votes.update(obj_id, result):
                                    # 3 ảnh bằng chứng theo đề xuất giảng viên
                                    # (áp dụng đồng nhất cho cả 2 loại vi phạm
                                    # - xem utils/evidence.py): (1) ảnh TOÀN
                                    # CẢNH có vẽ bbox khoanh phương tiện vi
                                    # phạm, (2) crop RIÊNG phương tiện đó,
                                    # (3) crop biển số lấy từ cache
                                    # self.plate_crops (frame gần nhất đọc
                                    # thành công biển số của track_id này).
                                    vhx1, vhy1 = int(x1 * scale_x), int(y1 * scale_y)
                                    vhx2, vhy2 = int(x2 * scale_x), int(y2 * scale_y)
                                    vehicle_crop_evidence = raw_frame[vhy1:vhy2, vhx1:vhx2]

                                    scene_img = raw_frame.copy()
                                    cv2.rectangle(scene_img, (vhx1, vhy1), (vhx2, vhy2), (0, 0, 255), 3)

                                    plate_img = self.plate_crops.get(obj_id)
                                    scene_path, vehicle_path, plate_path = save_evidence(
                                        config.NO_HELMET_DIR, obj_id, scene_img, vehicle_crop_evidence, plate_img,
                                    )
                                    logger.log(obj_id, plate_text, "NO_HELMET", scene_path, vehicle_path, plate_path)
                                    self.violation_queue.put({
                                        "time": datetime.now().strftime("%H:%M:%S"),
                                        "channel": self.name,
                                        "type": "NO_HELMET",
                                        "track_id": obj_id,
                                        "plate": plate_text or "",
                                        "scene_image": scene_path,
                                        "vehicle_image": vehicle_path,
                                        "plate_image": plate_path,
                                    })

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                label_text = f"{label} | ID {obj_id}"
                if status is not None:
                    label_text += f" | {status}"
                if plate_text:
                    label_text += f" | {plate_text}"
                cv2.putText(frame, label_text, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            self.current_fps = self.fps_counter.update()
            self._draw_overlay(frame, line_y, self.detect_zone_y)
            self._push_frame(frame)

            if frame_interval is not None:
                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        release()

    @staticmethod
    def _draw_overlay(frame, line_y, detect_zone_y):
        # Đường đếm lưu lượng (đỏ, nét liền).
        cv2.line(frame, (0, line_y), (frame.shape[1], line_y), (0, 0, 255), 2)

        # Vùng nhận diện (mũ bảo hiểm/biển số chỉ xử lý bên dưới đường này) -
        # vẽ nét đứt màu vàng để phân biệt với đường đếm, và để người dùng
        # THẤY ĐƯỢC thay đổi ngay khi chỉnh qua ROIPanel (kéo chuột trên
        # video) - trước đây KHÔNG vẽ gì cả nên chỉnh xong không biết có tác
        # dụng hay không dù giá trị đã thực sự được áp dụng.
        if detect_zone_y is not None:
            zone_color = (0, 220, 255)
            step = 12
            for x in range(0, frame.shape[1], step * 2):
                cv2.line(frame, (x, detect_zone_y), (min(x + step, frame.shape[1]), detect_zone_y), zone_color, 2)

    def _push_frame(self, frame):
        # queue maxsize=1: luôn giữ frame MỚI NHẤT, bỏ frame cũ nếu thread
        # chính chưa kịp lấy ra hiển thị (ưu tiên real-time hơn là không mất frame).
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
