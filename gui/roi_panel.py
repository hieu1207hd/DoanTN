from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from gui.attr_utils import set_nested_attr


class ROIPanel(QWidget):
    """Thanh công cụ chọn ROI TRỰC TIẾP trên video đang chạy - kéo chuột 1
    lần là áp dụng ngay vào channel (qua set_nested_attr, cùng cơ chế với
    slider conf ở ControlPanel), không cần sửa config.py + restart.

    roi_specs: list dict, mỗi dict mô tả 1 ROI có thể chỉnh, vd:
        {"label": "ROI đèn giao thông", "kind": "rect", "attr": "detector.roi",
         "config_name": "TRAFFIC_LIGHT_ROI"}
    - kind: "rect" (hình chữ nhật, giá trị attr là tuple (x1,y1,x2,y2)) hoặc
      "line" (1 đường ngang, giá trị attr là 1 số nguyên y - ví dụ
      checker.stop_line_y / channel.detect_zone_y đã dùng đúng kiểu này).
    - config_name: TÊN hằng số tương ứng trong config.py (dùng cho nút "Lưu
      vào config.py" - xem save_to_config()); để None nếu ROI này không có
      hằng số tương ứng trực tiếp trong config.py (không cho lưu).
    """

    def __init__(self, video_label, get_channel, roi_specs, config_path="config.py"):
        super().__init__()
        self.video_label = video_label
        self.get_channel = get_channel
        self.roi_specs = roi_specs
        self.config_path = config_path
        self._last_value = {}  # spec label -> giá trị vừa áp dụng (để nút Lưu dùng)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        layout.addWidget(QLabel("Chỉnh ROI:"))
        self.combo = QComboBox()
        for spec in roi_specs:
            self.combo.addItem(spec["label"])
        layout.addWidget(self.combo, stretch=1)

        self.draw_btn = QPushButton("Kéo chọn trên video")
        self.draw_btn.setCheckable(True)
        self.draw_btn.clicked.connect(self._toggle_draw)
        layout.addWidget(self.draw_btn)

        self.save_btn = QPushButton("Lưu vào config.py")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._save_current_to_config)
        layout.addWidget(self.save_btn)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label, stretch=1)

        self.video_label.roi_selected.connect(self._on_roi_selected)
        self.combo.currentIndexChanged.connect(self._on_combo_changed)

    def _current_spec(self):
        return self.roi_specs[self.combo.currentIndex()]

    def _toggle_draw(self, checked):
        if checked:
            spec = self._current_spec()
            self.video_label.set_edit_mode(spec["kind"])
            self.draw_btn.setText("Đang chờ kéo chuột trên video...")
        else:
            self.video_label.set_edit_mode(None)
            self.draw_btn.setText("Kéo chọn trên video")

    def _on_combo_changed(self, _index):
        # Đổi lựa chọn ROI khác thì tắt luôn edit mode đang bật dở, tránh áp
        # nhầm giá trị vừa kéo cho ROI không phải cái người dùng đang xem.
        self.draw_btn.setChecked(False)
        self.video_label.set_edit_mode(None)
        self.draw_btn.setText("Kéo chọn trên video")
        spec = self._current_spec()
        self.save_btn.setEnabled(spec.get("config_name") is not None and spec["label"] in self._last_value)

    def _on_roi_selected(self, value):
        spec = self._current_spec()
        applied = value[0] if spec["kind"] == "line" else value

        channel = self.get_channel()
        if channel is None:
            self.status_label.setText("Chưa bắt đầu channel - chưa áp dụng được, nhưng vẫn có thể Lưu vào config.py.")
        else:
            set_nested_attr(channel, spec["attr"], applied)
            self.status_label.setText(f"Đã áp dụng ngay: {spec['label']} = {applied}")

        self._last_value[spec["label"]] = applied
        self.save_btn.setEnabled(spec.get("config_name") is not None)

        self.draw_btn.setChecked(False)
        self.video_label.set_edit_mode(None)
        self.draw_btn.setText("Kéo chọn trên video")

    def _save_current_to_config(self):
        spec = self._current_spec()
        config_name = spec.get("config_name")
        value = self._last_value.get(spec["label"])
        if config_name is None or value is None:
            return

        # "line" lưu vào config.py dưới dạng TỈ LỆ (0-1) vì các hằng số line
        # trong config.py (LINE_Y_RATIO, STOP_LINE_Y_RATIO, DETECT_ZONE_RATIO)
        # đều là tỉ lệ để không phụ thuộc kích thước frame cụ thể - còn giá
        # trị live-apply ở trên vẫn là pixel tuyệt đối (đúng kiểu channel
        # đang dùng nội bộ lúc chạy).
        if spec["kind"] == "line":
            frame_size = self.video_label.frame_size
            frame_h = frame_size[1] if frame_size else 1
            new_literal = f"{value / frame_h:.4f}"
        else:
            new_literal = repr(tuple(value))

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            found = False
            for i, line in enumerate(lines):
                stripped = line.lstrip()
                if stripped.startswith(f"{config_name} ") or stripped.startswith(f"{config_name}="):
                    indent = line[:len(line) - len(stripped)]
                    comment = ""
                    if "#" in line:
                        comment = "  " + line[line.index("#"):].rstrip("\n")
                    lines[i] = f"{indent}{config_name} = {new_literal}{comment}\n"
                    found = True
                    break

            if not found:
                self.status_label.setText(f"Không tìm thấy {config_name} trong {self.config_path} để lưu.")
                return

            with open(self.config_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            self.status_label.setText(f"Đã lưu {config_name} = {new_literal} vào {self.config_path}.")
        except OSError as e:
            self.status_label.setText(f"Lỗi khi lưu config.py: {e}")
