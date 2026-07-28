from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

import config

# 3 mức hiệu năng máy hay gặp khi đưa hệ thống cho người khác chạy (giáo
# viên/hội đồng chấm...) - không phải ai cũng có GPU rời mạnh như máy phát
# triển. Giá trị cụ thể là điểm khởi đầu hợp lý, người dùng vẫn chỉnh tay
# thêm được ở phần "Chi tiết" bên dưới nếu cần.
PROFILES = {
    "Cao (GPU rời mạnh)": {
        "DEVICE": "auto",
        "RESIZE_WIDTH": 960,
        "PLATE_PROCESS_EVERY_N_FRAMES": 2,
        "PLATE_OCR_GPU": True,
    },
    "Trung bình (GPU tích hợp / CPU khá)": {
        "DEVICE": "auto",
        "RESIZE_WIDTH": 640,
        "PLATE_PROCESS_EVERY_N_FRAMES": 4,
        "PLATE_OCR_GPU": False,
    },
    "Thấp (chỉ CPU / card onboard yếu)": {
        "DEVICE": "cpu",
        "RESIZE_WIDTH": 480,
        "PLATE_PROCESS_EVERY_N_FRAMES": 8,
        "PLATE_OCR_GPU": False,
    },
}


class SetupPanel(QWidget):
    """Tab 'Cấu hình hệ thống' - chọn nhanh 1 trong 3 mức hiệu năng máy, tự
    điều chỉnh các tham số ảnh hưởng FPS nhiều nhất (thiết bị chạy model, độ
    phân giải xử lý, tần suất chạy OCR biển số) thay vì phải tự mò từng dòng
    trong config.py. Mục tiêu: máy không có GPU mạnh (hoặc chỉ có card
    onboard) vẫn chạy mượt được, chỉ cần đổi 1 lựa chọn.
    """

    def __init__(self):
        super().__init__()

        root = QVBoxLayout(self)

        intro = QLabel(
            "Chọn cấu hình phù hợp với máy đang chạy hệ thống. Máy không có GPU rời "
            "(chỉ có card đồ hoạ tích hợp/onboard) nên chọn mức Thấp để tránh giật/lag."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        profile_box = QGroupBox("Chọn nhanh theo cấu hình máy")
        profile_layout = QHBoxLayout(profile_box)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(list(PROFILES.keys()) + ["Tuỳ chỉnh"])
        self.profile_combo.currentTextChanged.connect(self._on_profile_selected)
        profile_layout.addWidget(self.profile_combo, stretch=1)
        root.addWidget(profile_box)

        detail_box = QGroupBox("Chi tiết (có thể tự tinh chỉnh thêm)")
        form = QFormLayout(detail_box)

        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto (tự chọn GPU nếu có)", "cpu (ép dùng CPU)"])
        form.addRow("Thiết bị chạy model:", self.device_combo)

        self.resize_spin = QSpinBox()
        self.resize_spin.setRange(320, 1280)
        self.resize_spin.setSingleStep(80)
        form.addRow("Độ phân giải xử lý (RESIZE_WIDTH):", self.resize_spin)

        self.plate_throttle_spin = QSpinBox()
        self.plate_throttle_spin.setRange(1, 15)
        form.addRow("Đọc biển số mỗi N frame/xe:", self.plate_throttle_spin)

        self.plate_gpu_check = QCheckBox("Chạy EasyOCR trên GPU (nếu có)")
        form.addRow(self.plate_gpu_check)

        self.enable_plate_check = QCheckBox("Bật tính năng nhận diện + đọc biển số")
        form.addRow(self.enable_plate_check)

        root.addWidget(detail_box)

        # Đặt giá trị ban đầu = đúng config.py hiện tại (không tự ý đổi gì
        # cho tới khi người dùng bấm Áp dụng).
        self._load_from_config()

        note = QLabel(
            "Lưu ý: \"Thiết bị chạy model\" và \"Bật/tắt đọc biển số\" chỉ có hiệu lực đầy đủ "
            "cho lần Bắt đầu TIẾP THEO (model đã tải sẵn không tự chuyển thiết bị giữa chừng) "
            "- nếu kênh đang chạy, hãy Dừng rồi Bắt đầu lại sau khi Áp dụng. Riêng \"Độ phân "
            "giải xử lý\" và \"Đọc biển số mỗi N frame\" có tác dụng NGAY LẬP TỨC kể cả khi đang chạy."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #f5a524;")
        root.addWidget(note)

        btn_row = QHBoxLayout()
        apply_btn = QPushButton("Áp dụng + lưu vào config.py")
        apply_btn.setObjectName("primaryButton")
        apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(apply_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        self.status_label = QLabel("")
        root.addWidget(self.status_label)

        root.addStretch(1)

    def _load_from_config(self):
        self.device_combo.setCurrentIndex(1 if config.DEVICE == "cpu" else 0)
        self.resize_spin.setValue(config.RESIZE_WIDTH)
        self.plate_throttle_spin.setValue(config.PLATE_PROCESS_EVERY_N_FRAMES)
        self.plate_gpu_check.setChecked(config.PLATE_OCR_GPU)
        self.enable_plate_check.setChecked(config.ENABLE_PLATE)

    def _on_profile_selected(self, name):
        if name not in PROFILES:
            return  # "Tuỳ chỉnh" - giữ nguyên giá trị người dùng đang tự chỉnh tay
        profile = PROFILES[name]
        self.device_combo.setCurrentIndex(1 if profile["DEVICE"] == "cpu" else 0)
        self.resize_spin.setValue(profile["RESIZE_WIDTH"])
        self.plate_throttle_spin.setValue(profile["PLATE_PROCESS_EVERY_N_FRAMES"])
        self.plate_gpu_check.setChecked(profile["PLATE_OCR_GPU"])

    def _apply(self):
        new_values = {
            "DEVICE": "cpu" if self.device_combo.currentIndex() == 1 else "auto",
            "RESIZE_WIDTH": self.resize_spin.value(),
            "PLATE_PROCESS_EVERY_N_FRAMES": self.plate_throttle_spin.value(),
            "PLATE_OCR_GPU": self.plate_gpu_check.isChecked(),
            "ENABLE_PLATE": self.enable_plate_check.isChecked(),
        }

        # 1. Áp dụng NGAY vào module config đang chạy trong bộ nhớ - mọi
        # channel (đang chạy hay chưa) đều đọc trực tiếp từ module config này
        # (vd config.RESIZE_WIDTH mỗi frame - xem channels/*.py::_resize),
        # không giữ bản sao riêng, nên setattr ở đây có hiệu lực ngay với
        # RESIZE_WIDTH/PLATE_PROCESS_EVERY_N_FRAMES. Riêng DEVICE/ENABLE_PLATE
        # chỉ được đọc lúc khởi tạo model trong _run() nên cần Dừng/Bắt đầu
        # lại mới áp dụng đầy đủ (đã ghi rõ trong note ở trên).
        for key, value in new_values.items():
            setattr(config, key, value)

        # 2. Ghi xuống config.py để giữ lại cho lần mở app sau.
        self._write_to_config_file(new_values)

        self.status_label.setText(
            "Đã áp dụng + lưu vào config.py. Nếu kênh đang chạy, Dừng rồi Bắt đầu lại "
            "để 'Thiết bị chạy model' và 'Bật/tắt đọc biển số' có hiệu lực đầy đủ."
        )

    @staticmethod
    def _write_to_config_file(new_values, config_path="config.py"):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            return

        for i, line in enumerate(lines):
            stripped = line.lstrip()
            for key, value in new_values.items():
                if stripped.startswith(f"{key} ") or stripped.startswith(f"{key}="):
                    indent = line[:len(line) - len(stripped)]
                    comment = ""
                    if "#" in line:
                        comment = "  " + line[line.index("#"):].rstrip("\n")
                    literal = repr(value) if isinstance(value, str) else str(value)
                    lines[i] = f"{indent}{key} = {literal}{comment}\n"
                    break

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except OSError:
            pass
