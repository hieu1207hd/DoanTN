import os
from datetime import datetime

import cv2


def save_evidence(directory, track_id, scene_img, vehicle_img, plate_img=None):
    """Lưu ẢNH BẰNG CHỨNG cho 1 lần vi phạm - LUÔN 3 ẢNH, áp dụng ĐỒNG NHẤT
    cho cả 2 loại vi phạm (theo đề xuất giảng viên hướng dẫn):
      1. scene_img: ẢNH TOÀN CẢNH tại thời điểm vi phạm, đã VẼ SẴN bbox khoanh
         vùng phương tiện vi phạm - giữ nguyên bối cảnh xung quanh (làn
         đường, xe khác, đèn tín hiệu) để làm bằng chứng đầy đủ ngữ cảnh.
      2. vehicle_img: crop RIÊNG phương tiện vi phạm (không kèm nền/bbox vẽ
         đè) - nhìn rõ chi tiết xe mà không bị nhiễu bởi phần còn lại khung
         hình.
      3. plate_img: crop RIÊNG vùng biển số, nếu đã đọc được tại thời điểm
         vi phạm.

    Cả 3 ảnh dùng CHUNG 1 timestamp trong tên file để thấy rõ là CÙNG 1 lần
    vi phạm, tên file dạng "{track_id}_{yyyymmdd_HHMMSS}_{loại}.jpg", vd:
        outputs/khong_doi_mu/17_20260728_101530_toancanh.jpg
        outputs/khong_doi_mu/17_20260728_101530_xe.jpg
        outputs/khong_doi_mu/17_20260728_101530_bienso.jpg

    Trả về (scene_path, vehicle_path, plate_path). plate_path là "" nếu
    plate_img là None hoặc rỗng (chưa đọc được biển số tại thời điểm vi phạm)
    - KHÔNG lưu file rỗng, để tránh rác trong thư mục output.
    """
    os.makedirs(directory, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    scene_path = os.path.join(directory, f"{track_id}_{ts}_toancanh.jpg")
    cv2.imwrite(scene_path, scene_img)

    vehicle_path = os.path.join(directory, f"{track_id}_{ts}_xe.jpg")
    cv2.imwrite(vehicle_path, vehicle_img)

    plate_path = ""
    if plate_img is not None and plate_img.size > 0:
        plate_path = os.path.join(directory, f"{track_id}_{ts}_bienso.jpg")
        cv2.imwrite(plate_path, plate_img)

    return scene_path, vehicle_path, plate_path
