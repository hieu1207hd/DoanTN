# config.py
# Toàn bộ tham số hệ thống tập trung ở đây. main.py PHẢI đọc từ config này
# thay vì hardcode rải rác trong code (đây là lỗi ở bản gốc: config.py tồn tại
# nhưng không hề được import ở main.py).

import os

# ===== 2 KÊNH XỬ LÝ ĐỘC LẬP, MỖI KÊNH 1 CAMERA RIÊNG =====
# Channel 1: camera nhìn toàn cảnh làn đường -> đếm lưu lượng + bắt vi phạm
#            không đội mũ bảo hiểm.
# Channel 2: camera nhìn đèn giao thông + vạch dừng -> bắt vi phạm vượt đèn đỏ.
# Bật/tắt độc lập từng kênh: kênh nào tắt thì không mở video/model của kênh
# đó, không ảnh hưởng gì tới kênh còn lại. Đang tắt channel 2 vì chưa setup
# camera góc đèn đỏ -> chỉ cần đổi ENABLE_CHANNEL2 = True khi có camera thật.
ENABLE_CHANNEL1 = True
ENABLE_CHANNEL2 = True

# SOURCE có thể là:
#   - đường dẫn file video, vd "test1.mp4"
#   - số nguyên = chỉ số camera USB/webcam, vd 0, 1, 2...
#   - URL luồng mạng (IP camera), vd "rtsp://192.168.1.10:554/stream1"
# Code tự nhận diện loại nguồn (xem utils/video_source.py::is_live_source).
SOURCE_CH1 = "test1.mp4"
SOURCE_CH2 = "source.mp4"   # placeholder - chưa có file/camera, đổi khi có

# Chỉ áp dụng khi SOURCE là FILE (không áp dụng cho camera sống, vì camera
# sống vốn đã chạy đúng tốc độ thực). Bật True để giữ nhịp phát lại đúng
# FPS gốc của video khi demo (dễ nhìn hơn), tắt False để xử lý nhanh nhất
# có thể (khuyến nghị khi đang test độ chính xác, không cần đúng nhịp).
SYNC_TO_REAL_FPS = False

# Bật/tắt lẻ 2 tính năng con bên trong channel 1 (không liên quan tới channel 2)
ENABLE_FLOW = True
ENABLE_HELMET = True

# ===== OUTPUT CHUNG =====
OUTPUT_DIR = "outputs"
RESIZE_WIDTH = 640                 # resize giữ tỉ lệ trước khi xử lý

# ===== LƯU VI PHẠM — TÁCH RIÊNG THEO TỪNG LOẠI =====
# Bản gốc dùng CHUNG 1 file violations.csv cho cả 2 kênh (khó tra cứu/thống kê
# riêng từng loại, và 2 thread của 2 kênh cùng ghi vào 1 file). Giờ mỗi loại
# vi phạm có: 1 file CSV riêng + 1 thư mục ảnh riêng, tách biệt hoàn toàn.
NO_HELMET_DIR = os.path.join(OUTPUT_DIR, "khong_doi_mu")
NO_HELMET_LOG_CSV = os.path.join(NO_HELMET_DIR, "vi_pham_khong_mu_bao_hiem.csv")

RED_LIGHT_DIR = os.path.join(OUTPUT_DIR, "vuot_den_do")
RED_LIGHT_LOG_CSV = os.path.join(RED_LIGHT_DIR, "vi_pham_vuot_den_do.csv")

# ===== MODEL PHƯƠNG TIỆN + TRACKING =====
VEHICLE_MODEL = "models/yolov8m.pt"
ALLOWED_VEHICLE_CLASSES = (2, 3)   # COCO: 2 = car, 3 = motorbike
VEHICLE_CONF = 0.5
# Ngưỡng conf riêng cho person (context_classes) - THẤP HƠN vehicle_conf.
# Lý do: bỏ sót 1 person (miss) làm mất luôn cơ hội check mũ bảo hiểm cho xe
# đó, tệ hơn việc detect dư 1 person không cần thiết (person chỉ dùng để đối
# chiếu, không tự sinh ra vi phạm). Đã quan sát thực tế: xe gần camera nhất
# (to nhất khung hình) đôi khi bị model bỏ sót person ở cùng ngưỡng với xe.
PERSON_CONF = 0.3
DEVICE = "auto"                    # "auto" | "cpu" | 0 (chỉ số GPU)
# LƯU Ý: requirements.txt liệt kê deep-sort-realtime nhưng code hiện tại dùng
# tracker mặc định của Ultralytics (ByteTrack), KHÔNG dùng deep-sort-realtime.
# Nếu báo cáo đồ án ghi "dùng DeepSORT" thì cần sửa lại core/tracker.py cho khớp,
# hoặc xoá dependency deep-sort-realtime khỏi requirements.txt cho đúng thực tế.

# ===== ĐẾM LƯU LƯỢNG (core/flow.py) =====
DIRECTION = "up"          # "up" (dưới->lên) hoặc "down" (trên->xuống)
LINE_Y_RATIO = 0.6        # vị trí line đếm, tính theo % chiều cao khung hình

# ===== PHÁT HIỆN MŨ BẢO HIỂM (modules/helmet.py) =====
HELMET_MODEL = "models/helmet_detector_fine_tuned_3.pt"
HELMET_CONF = 0.25
DETECT_ZONE_RATIO = 0.3439  # chỉ check mũ khi object ở nửa dưới khung hình (gần cam, ảnh rõ)

# Class "motorcycle"/"car" (COCO id 2,3) chỉ bao quanh CÁI XE, không chắc chắn
# bao luôn đầu người ngồi trên xe -> cắt "top X% của bbox xe" có thể trúng
# gương/ghi-đông thay vì đầu người (đã xác nhận bằng debug_helmet.py trên
# video thật). Cách đúng: detect thêm class "person" (COCO id 0), tìm người
# chồng lấn nhiều nhất lên xe (utils/bbox.py::find_best_overlap), rồi cắt đầu
# từ bbox NGƯỜI đó thay vì bbox xe.
PERSON_CLASS_ID = 0
PERSON_HEAD_RATIO = 0.9  # % chiều cao bbox NGƯỜI (không phải bbox xe) coi là vùng đầu

HELMET_VOTE_WINDOW = 5    # số frame gần nhất dùng để "biểu quyết" trạng thái mũ bảo hiểm
HELMET_VOTE_MIN_COUNT = 3 # số phiếu NO_HELMET tối thiểu trong window mới tính là vi phạm

# Nếu head_crop (đo trên ẢNH GỐC, đã quy đổi lại từ bbox, KHÔNG phải ảnh đã
# resize) nhỏ hơn ngưỡng này -> xe được coi là quá xa/quá nhỏ để đánh giá
# đáng tin cậy, hệ thống báo "QUA XA" và bỏ qua, KHÔNG gọi model (tránh vừa
# tốn compute vừa đoán bừa trên ảnh gần như không còn thông tin thật).
# Giá trị chiều cao đã hạ từ 40 xuống 28 dựa trên bằng chứng thực tế từ
# debug_helmet.py: nhiều crop cao 31-35px (dưới 40 cũ) vẫn cho model ra kết
# quả có ý nghĩa (conf ~0.2-0.29, gần ngưỡng HELMET_CONF=0.25 thật). Chiều
# rộng vẫn giữ 40 vì trong thực tế chưa từng là yếu tố giới hạn (luôn > 60px).
# Tăng/giảm tiếp nếu sau khi chạy main.py trên video thật thấy còn nhiều
# trường hợp "QUA XA" oan hoặc ngược lại nhiều kết quả không đáng tin cậy.
MIN_HEAD_CROP_HEIGHT = 70
MIN_HEAD_CROP_WIDTH = 40

# ===== VƯỢT ĐÈN ĐỎ (core/redlight.py) — MODULE MỚI, bản gốc chưa có =====
# ROI (x1, y1, x2, y2) của vùng đèn giao thông trong khung hình ĐàRESIZE (640xH).
# ĐÂY LÀ TỌA ĐỘ MẪU, BẠN BẮT BUỘC PHẢI TỰ CHỈNH lại theo video thực tế của mình
# (xem hướng dẫn cách xác định ROI trong README_CHANGES.md).
TRAFFIC_LIGHT_ROI = (599, 34, 618, 112)
STOP_LINE_Y_RATIO = 0.4890  # vạch dừng, nên đặt phía TRƯỚC line đếm flow một chút

# Ngưỡng màu đỏ trong không gian HSV (OpenCV: H 0-179, S/V 0-255)
RED_HSV_LOWER1 = (0, 100, 100)
RED_HSV_UPPER1 = (10, 255, 255)
RED_HSV_LOWER2 = (160, 100, 100)
RED_HSV_UPPER2 = (179, 255, 255)
RED_PIXEL_THRESHOLD = 50   # số pixel đỏ tối thiểu trong ROI để coi là "đèn đang đỏ"

# ===== NGOẠI LỆ RẼ PHẢI KHI ĐÈN ĐỎ =====
# Ở HẦU HẾT giao lộ tại Việt Nam, xe được phép rẽ phải khi đèn đỏ (trừ khi có
# biển "cấm rẽ phải khi đèn đỏ" hoặc đèn tín hiệu rẽ phải riêng) - bản gốc
# coi MỌI xe cắt qua vạch dừng lúc đèn đỏ là vi phạm, kể cả xe đang rẽ phải
# hợp lệ -> bắt oan rất nhiều tại các giao lộ VN thông thường (không phải
# lỗi hiếm gặp, mà gần như XẢY RA VỚI MỌI GIAO LỘ CÓ LÀN RẼ PHẢI).
#
# RIGHT_TURN_ZONE (x1, y1, x2, y2): vùng ảnh tương ứng làn/khu vực xe rẽ phải
# đi qua (thường ở góc phải giao lộ, ngay sau vạch dừng) - xe cắt vạch dừng
# lúc đèn đỏ NHƯNG bbox chồng lấn đủ nhiều với vùng này thì KHÔNG tính vi
# phạm. ĐÂY LÀ TỌA ĐỘ MẪU, BẮT BUỘC PHẢI TỰ CHỈNH theo giao lộ thực tế (đo
# trên khung hình ĐÃ RESIZE 640xH, giống cách xác định TRAFFIC_LIGHT_ROI) -
# hoặc để None để TẮT HẲN ngoại lệ này (dùng cho giao lộ có biển cấm rẽ phải,
# hoặc camera không bao quát được làn rẽ phải nên không định nghĩa vùng được).
RIGHT_TURN_ZONE = (483, 99, 605, 358)  # vd: (480, 40, 640, 200)

# Tỉ lệ diện tích bbox xe phải nằm trong RIGHT_TURN_ZONE để được coi là "đang
# rẽ phải" hợp lệ. Đặt THẤP quá -> dễ bỏ lọt vi phạm thật (xe đi thẳng sát
# vùng rẽ cũng bị loại trừ oan). Đặt CAO quá -> xe rẽ phải vẫn bị bắt vi phạm
# vì bbox chưa kịp chồng lấn đủ nhiều lúc cắt vạch dừng (xe vừa bắt đầu rẽ).
RIGHT_TURN_MIN_OVERLAP = 0.35


# ===== NHẬN DIỆN + ĐỌC BIỂN SỐ (modules/plate.py) — MODULE MỚI, bản gốc =====
# ===== chưa có. Dùng chung cho CẢ 2 kênh (gắn biển số vào vi phạm không mũ  =====
# ===== bảo hiểm VÀ vi phạm vượt đèn đỏ).                                    =====
ENABLE_PLATE = True

# Model YOLO đã train sẵn, chỉ detect VỊ TRÍ vùng biển số trên ảnh xe (không
# tự đọc ký tự) -> chạy trên crop của TỪNG XE (không chạy trên cả khung hình,
# để tránh detect trúng biển số của xe khác đứng gần đó).
PLATE_MODEL = "models/plate.pt"
PLATE_CONF = 0.4

# Đọc ký tự trong vùng biển số đã detect: dùng EasyOCR thay vì PaddleOCR.
# Lý do: EasyOCR chỉ cần "pip install easyocr" là chạy được ngay, trong khi
# PaddleOCR đòi hỏi cài thêm framework PaddlePaddle riêng (bản CPU/GPU phải
# khớp đúng phiên bản CUDA của máy) -> dễ lỗi khi đem đồ án chạy demo trên
# máy khác/máy hội đồng. Độ chính xác 2 bên chênh nhau không nhiều với biển
# số xe (ít ký tự, font rõ ràng), nên ưu tiên EasyOCR cho dễ triển khai.
PLATE_OCR_LANGS = ("en",)
PLATE_OCR_GPU = False      # đổi True nếu máy có GPU và muốn OCR nhanh hơn

# Giới hạn tập ký tự OCR được phép đoán (biển số VN chỉ có chữ in hoa + số)
# -> vừa NHANH HƠN vừa CHÍNH XÁC HƠN (xem PlateReader trong modules/plate.py).
PLATE_OCR_ALLOWLIST = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Ảnh biển số nhỏ hơn chiều cao này (px) sẽ được PHÓNG TO trước khi OCR (xem
# preprocess_plate trong modules/plate.py) - biển số quá nhỏ khiến EasyOCR
# dễ đọc sai/thiếu ký tự.
PLATE_UPSCALE_HEIGHT = 64

# Ngưỡng độ nét tối thiểu (đo bằng phương sai Laplacian - xem sharpness_score
# trong modules/plate.py) để chấp nhận gọi OCR trên 1 crop. Crop mờ hơn
# ngưỡng này (do rung camera/xe di chuyển nhanh/quá xa) sẽ bị BỎ QUA, không
# gọi OCR - vừa tiết kiệm compute vừa tránh đọc rác làm nhiễu vote.
# 0 = tắt lọc mờ (luôn gọi OCR). Giá trị mẫu ~40-80 tuỳ chất lượng camera,
# CẦN tự đo lại: in ra sharpness_score() của vài chục crop thật (đọc được
# và không đọc được) rồi chọn ngưỡng nằm giữa 2 nhóm đó.
PLATE_MIN_SHARPNESS = 0

# Bao nhiêu FRAME mới cho phép chạy detector + OCR biển số 1 LẦN cho MỖI xe
# (khi xe đó CHƯA "chốt" được biển số) - vd = 3 nghĩa là cứ 3 frame liên tiếp
# của cùng 1 xe thì chỉ frame thứ 3 mới thực sự chạy model, 2 frame trước bị
# bỏ qua hoàn toàn (không tốn compute). Đây là nguyên nhân chính gây TỤT FPS
# khi bật ENABLE_PLATE: detector YOLO + EasyOCR chạy cho MỌI xe, MỌI frame,
# cho tới khi chốt được biển số - 2 xe cùng lúc x model detect + OCR mỗi
# frame là rất nặng, đặc biệt khi chạy CPU. Tăng giá trị này (5-10) nếu vẫn
# còn tụt FPS nhiều - đổi lại là mất nhiều frame hơn mới chốt được biển số
# (không ảnh hưởng độ chính xác cuối cùng, chỉ tăng thời gian tới lúc chốt).
PLATE_PROCESS_EVERY_N_FRAMES = 3

# Lọc mờ SỚM hơn PLATE_MIN_SHARPNESS ở trên: PLATE_MIN_SHARPNESS đo độ nét
# của ẢNH BIỂN SỐ SAU KHI ĐÃ detect ra (vẫn phải chạy YOLO plate model rồi
# mới biết mờ hay không - phí nếu biết chắc cả khung hình đang mờ). Ngưỡng
# này đo độ nét của CẢ CROP XE (rẻ hơn nhiều, chỉ 1 phép Laplacian, không
# cần chạy model nào) TRƯỚC KHI gọi plate_detector - nếu xe đang bị motion
# blur (di chuyển nhanh/rung), gần như chắc chắn vùng biển số bên trong
# cũng mờ tương tự -> bỏ qua luôn từ bước này, đợi frame sau xe nét hơn.
# 0 = tắt (không lọc ở bước này). CẦN tự đo giống PLATE_MIN_SHARPNESS, nhưng
# đo trên ảnh crop XE (to hơn ảnh biển số) nên giá trị ngưỡng thường sẽ khác.
PLATE_MIN_VEHICLE_SHARPNESS = 0

# Trần số lần THỰC SỰ đã chạy OCR cho 1 xe (tính cả những lần đọc rỗng/sai,
# không tính những lần bị bỏ qua bởi 2 bộ lọc mờ ở trên hay throttle theo
# frame) - vượt qua ngưỡng này mà VẪN CHƯA chốt được biển số thì NGỪNG THỬ
# HẲN cho track_id đó (is_locked-style: xem PlateVoteAggregator.should_attempt).
# Tránh trường hợp biển số vốn dĩ không thể đọc được (mờ toàn bộ video, góc
# khuất...) khiến hệ thống chạy OCR vô tận trên xe đó tới khi ra khỏi khung
# hình - vẫn tốn compute dù đã throttle + lọc mờ ở 2 bước trên.
PLATE_MAX_ATTEMPTS = 20


# Giống HELMET_VOTE_WINDOW/MIN_COUNT: 1 lần đọc OCR trên 1 frame dễ sai/thiếu
# ký tự (do góc nghiêng, mờ, xe đang di chuyển) -> gom N lần đọc gần nhất của
# CÙNG 1 xe (track_id) rồi "chốt" theo kết quả xuất hiện nhiều nhất, chỉ chốt
# khi đã đủ số phiếu tối thiểu để tránh chốt nhầm ngay từ 1-2 lần đọc đầu.
PLATE_VOTE_WINDOW = 7
PLATE_VOTE_MIN_COUNT = 3

# Vùng biển số detect được (đo trên ảnh crop xe, ẢNH GỐC chưa resize - xem
# giải thích tương tự MIN_HEAD_CROP_HEIGHT/WIDTH) nhỏ hơn ngưỡng này thì bỏ
# qua, không gọi OCR (biển quá nhỏ/quá xa, OCR gần như chắc chắn đọc sai).
MIN_PLATE_CROP_HEIGHT = 12
MIN_PLATE_CROP_WIDTH = 35

# Tái sử dụng DETECT_ZONE_RATIO (chỉ xử lý xe ở nửa dưới khung hình, gần
# camera, ảnh rõ hơn) để giới hạn vùng chạy plate detector + OCR, tránh tốn
# compute vô ích trên xe còn ở xa (gần như chắc chắn biển số chưa đọc được).
