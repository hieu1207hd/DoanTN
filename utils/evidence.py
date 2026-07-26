import os
from datetime import datetime

import cv2


def save_evidence(directory, track_id, evidence_label, evidence_img, plate_img=None):
    """Lưu ẢNH BẰNG CHỨNG cho 1 lần vi phạm - LUÔN 2 ẢNH cho mỗi vi phạm để
    đồng bộ giữa 2 loại vi phạm (bản gốc: no-helmet chỉ lưu ảnh đầu, red-light
    chỉ lưu ảnh xe - không đồng nhất):
      1. Ảnh CHÍNH (evidence_img): toàn thân người (vi phạm không mũ bảo
         hiểm) hoặc toàn xe (vi phạm vượt đèn đỏ) - evidence_label phân biệt
         2 loại này khi đặt tên file ("nguoi" / "xe").
      2. Ảnh biển số (plate_img): crop riêng vùng biển số, nếu đã đọc được.

    2 ảnh dùng CHUNG 1 timestamp trong tên file để thấy rõ là CÙNG 1 lần vi
    phạm, tên file dạng: "{track_id}_{yyyymmdd_HHMMSS}_{label}.jpg", vd:
        outputs/khong_doi_mu/17_20260723_101530_nguoi.jpg
        outputs/khong_doi_mu/17_20260723_101530_bienso.jpg

    Trả về (evidence_path, plate_path). plate_path là "" nếu plate_img là
    None hoặc rỗng (chưa đọc được biển số tại thời điểm vi phạm) - KHÔNG lưu
    file rỗng, để tránh rác trong thư mục output.
    """
    os.makedirs(directory, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    evidence_path = os.path.join(directory, f"{track_id}_{ts}_{evidence_label}.jpg")
    cv2.imwrite(evidence_path, evidence_img)

    plate_path = ""
    if plate_img is not None and plate_img.size > 0:
        plate_path = os.path.join(directory, f"{track_id}_{ts}_bienso.jpg")
        cv2.imwrite(plate_path, plate_img)

    return evidence_path, plate_path
