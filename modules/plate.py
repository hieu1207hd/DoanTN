import re
from collections import Counter, defaultdict, deque

import cv2
from ultralytics import YOLO

from utils.device import resolve_device


class PlateDetector:
    """Detect vùng biển số bên trong 1 crop xe (KHÔNG chạy trên cả khung
    hình gốc) - chạy trên crop của từng xe để tránh detect trúng biển số
    của xe khác đang đứng gần đó trong cùng khung hình.
    """

    def __init__(self, model_path, conf=0.4, device="auto"):
        self.model = YOLO(model_path)
        self.conf = conf
        self.device = resolve_device(device)

    def detect(self, vehicle_crop):
        """Trả về bbox (x1, y1, x2, y2) của vùng biển số, TÍNH THEO TOẠ ĐỘ
        CỦA vehicle_crop (không phải toạ độ khung hình gốc) - hoặc None nếu
        không detect được. Nếu detect ra nhiều box (hiếm, do nhiễu), chỉ lấy
        box có conf cao nhất.
        """
        if vehicle_crop is None or vehicle_crop.size == 0:
            return None

        results = self.model(vehicle_crop, conf=self.conf, device=self.device, verbose=False)

        best_box, best_conf = None, 0.0
        for r in results:
            if r.boxes is None:
                continue
            boxes = r.boxes.xyxy.cpu().numpy()
            confs = r.boxes.conf.cpu().numpy()
            for box, cf in zip(boxes, confs):
                if cf > best_conf:
                    best_conf = float(cf)
                    best_box = box

        if best_box is None:
            return None
        x1, y1, x2, y2 = map(int, best_box)
        return (x1, y1, x2, y2)


# Biển số VN chỉ gồm chữ in hoa + số. OCR hay lẫn dấu chấm/gạch ngang/khoảng
# trắng KHÔNG ổn định giữa các frame (lúc đọc ra "-", lúc không) -> bỏ hết
# ký tự không phải chữ/số để việc so khớp bình chọn (vote) giữa các frame
# chính xác hơn, thay vì cố tái tạo đúng định dạng gạch/chấm theo từng tỉnh.
_NON_ALNUM = re.compile(r"[^A-Z0-9]")


def clean_plate_text(raw_text):
    if not raw_text:
        return ""
    text = raw_text.upper().replace(" ", "")
    return _NON_ALNUM.sub("", text)


def sharpness_score(image):
    """Đo độ nét bằng phương sai Laplacian (cách đo mờ phổ biến, nhanh, không
    cần model): ảnh càng nét càng có nhiều biên rõ -> phương sai càng cao.
    Ảnh biển số mờ do rung/motion-blur/quá xa sẽ cho điểm thấp - dùng để lọc
    bỏ TRƯỚC khi tốn compute gọi OCR (xem PlateReader.read), tránh vừa mất
    thời gian vừa tạo ra kết quả rác làm nhiễu vote.
    """
    if image is None or image.size == 0:
        return 0.0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def preprocess_plate(image, target_height=64):
    """Tăng khả năng đọc được của ảnh biển số trước khi đưa vào OCR:
    1. Phóng to nếu ảnh nhỏ hơn target_height (biển số xa camera thường chỉ
       cao vài chục pixel - quá nhỏ để OCR nhận diện chính xác từng ký tự).
    2. Chuyển xám + cân bằng sáng cục bộ (CLAHE) để tăng tương phản chữ/nền,
       hữu ích khi biển số bị chói sáng hoặc thiếu sáng (ban đêm).
    KHÔNG áp dụng threshold nhị phân cứng (0/255): dễ mất nét chữ nếu chọn
    sai ngưỡng trong điều kiện ánh sáng thay đổi liên tục ngoài trời - CLAHE
    an toàn hơn cho nhiều điều kiện sáng khác nhau.
    """
    h, w = image.shape[:2]
    if h < target_height:
        scale = target_height / h
        image = cv2.resize(image, (int(w * scale), target_height), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


class PlateReader:
    """Đọc ký tự trong ảnh biển số đã crop, dùng EasyOCR (xem lý do chọn
    EasyOCR thay vì PaddleOCR trong config.py, mục NHẬN DIỆN + ĐỌC BIỂN SỐ).
    """

    def __init__(self, langs=("en",), gpu=False, allowlist=None, min_sharpness=0.0, upscale_height=64,
                 model_storage_directory=None):
        # Import trễ (bên trong __init__, không import ở đầu file): easyocr
        # là dependency khá nặng (tự tải model khi khởi tạo lần đầu) - chỉ
        # nên bắt buộc cài khi người dùng thực sự bật ENABLE_PLATE = True.
        import easyocr

        # model_storage_directory: chỉ định thư mục cục bộ chứa sẵn model của
        # EasyOCR (~150-200MB, mặc định EasyOCR tự tải về ~/.EasyOCR/model/
        # lúc chạy lần đầu, CẦN INTERNET). Khi đóng gói app đưa cho máy khác
        # không có mạng (xem PACKAGING.md), trỏ tham số này về 1 thư mục đã
        # copy sẵn model để chạy được hoàn toàn offline. None = dùng hành vi
        # mặc định của EasyOCR (tự tải/tự tìm ở vị trí chuẩn của nó).
        self.reader = easyocr.Reader(
            list(langs), gpu=gpu, verbose=False,
            model_storage_directory=model_storage_directory,
        )
        # allowlist: giới hạn tập ký tự OCR được phép đoán ra (biển số VN chỉ
        # có chữ in hoa + số, không có ký tự đặc biệt/chữ thường) - vừa NHANH
        # HƠN (giảm không gian tìm kiếm ký tự) vừa CHÍNH XÁC HƠN (loại trừ
        # luôn các ký tự không thể xuất hiện trên biển số).
        self.allowlist = allowlist
        # Ngưỡng độ nét tối thiểu (xem sharpness_score) - crop mờ hơn ngưỡng
        # này bị bỏ qua, KHÔNG gọi OCR (tốn compute vô ích + dễ đọc sai/rác).
        self.min_sharpness = min_sharpness
        # Chiều cao tối thiểu (px) crop biển số phải đạt được TRƯỚC khi OCR -
        # nhỏ hơn sẽ bị phóng to (xem preprocess_plate).
        self.upscale_height = upscale_height

    def read(self, plate_crop):
        """Trả về (text, confidence) đã ghép các dòng OCR đọc được lại với
        nhau theo thứ tự trên->dưới, trái->phải (biển số VN có loại 1 dòng
        và loại 2 dòng - easyocr trả về từng khối text rời rạc không theo
        thứ tự đọc tự nhiên, cần tự sắp lại theo toạ độ).
        """
        if plate_crop is None or plate_crop.size == 0:
            return "", 0.0

        if self.min_sharpness > 0 and sharpness_score(plate_crop) < self.min_sharpness:
            # Ảnh quá mờ - bỏ qua ngay, không gọi OCR (xem giải thích ở
            # sharpness_score/__init__).
            return "", 0.0

        processed = preprocess_plate(plate_crop, target_height=self.upscale_height)

        kwargs = {"allowlist": self.allowlist} if self.allowlist else {}
        results = self.reader.readtext(processed, **kwargs)
        if not results:
            return "", 0.0

        results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))

        texts = [clean_plate_text(r[1]) for r in results]
        texts = [t for t in texts if t]
        if not texts:
            return "", 0.0

        combined = "".join(texts)
        avg_conf = sum(r[2] for r in results) / len(results)
        return combined, float(avg_conf)


class PlateVoteAggregator:
    """Bình chọn (vote) biển số ổn định theo track_id qua nhiều frame - cùng
    nguyên lý với HelmetVoteAggregator (modules/helmet.py): 1 lần đọc OCR
    trên 1 frame dễ sai/thiếu ký tự, nên gom N lần đọc gần nhất của CÙNG 1
    xe rồi chọn kết quả xuất hiện NHIỀU NHẤT, chỉ "chốt" (lock) một lần khi
    đã đủ số phiếu tối thiểu - sau khi chốt thì không đọc OCR lại nữa cho
    track_id đó (tiết kiệm compute, xem channels/flow_helmet_channel.py).
    """

    def __init__(self, window=7, min_count=3, max_attempts=20):
        self.window = window
        self.min_count = min_count
        self.history = defaultdict(lambda: deque(maxlen=window))
        self.locked_text = {}  # track_id -> text đã chốt
        # Đếm số lần ĐÃ THỰC SỰ chạy OCR (không tính lần bị lọc mờ/throttle
        # bỏ qua) cho mỗi track_id - dùng để "bỏ cuộc" nếu vượt max_attempts
        # mà vẫn chưa chốt được (xem PLATE_MAX_ATTEMPTS trong config.py).
        self.max_attempts = max_attempts
        self.attempts = defaultdict(int)
        self.gave_up = set()

    def is_locked(self, track_id):
        return track_id in self.locked_text

    def has_given_up(self, track_id):
        return track_id in self.gave_up

    def should_attempt(self, track_id):
        """False nếu track_id đã chốt biển số HOẶC đã bỏ cuộc (thử quá
        max_attempts lần mà vẫn không chốt được) - gọi TRƯỚC khi chạy
        plate_detector + OCR để không tốn compute vô ích trên xe không thể
        đọc được biển số (biển hỏng, góc khuất, mờ toàn bộ video...).
        """
        return track_id not in self.locked_text and track_id not in self.gave_up

    def register_attempt(self, track_id):
        """Gọi mỗi lần THỰC SỰ chạy OCR cho track_id (kể cả khi đọc ra rỗng)
        - đủ max_attempts mà vẫn chưa chốt thì đánh dấu bỏ cuộc.
        """
        self.attempts[track_id] += 1
        if self.attempts[track_id] >= self.max_attempts and track_id not in self.locked_text:
            self.gave_up.add(track_id)

    def update(self, track_id, text):
        """Thêm 1 lần đọc mới (bỏ qua nếu track_id đã chốt hoặc text rỗng).
        Trả về text vừa được chốt nếu lần update này khiến đủ điều kiện
        chốt, ngược lại trả về None.
        """
        if track_id in self.locked_text or not text:
            return None

        self.history[track_id].append(text)

        best_text, count = Counter(self.history[track_id]).most_common(1)[0]
        if count >= self.min_count:
            self.locked_text[track_id] = best_text
            return best_text

        return None

    def get(self, track_id):
        """Text hiện có để HIỂN THỊ (không nhất thiết đã chốt): ưu tiên text
        đã chốt, nếu chưa thì trả về lần đọc gần nhất (tạm thời, có thể còn
        đổi ở frame sau), hoặc None nếu track_id chưa đọc được lần nào.
        """
        if track_id in self.locked_text:
            return self.locked_text[track_id]
        hist = self.history.get(track_id)
        if hist:
            return hist[-1]
        return None
