import os

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QStackedWidget,
    QVBoxLayout, QWidget,
)

from gui.attr_utils import set_nested_attr


class SourcePicker(QWidget):
    """
    Cho phép chọn 1 trong 3 loại nguồn: file video / camera (webcam) / URL
    (RTSP-HTTP). Trả về đúng kiểu dữ liệu mà Tracker/Channel cần: str (path
    hoặc URL) hoặc int (chỉ số camera) - xem utils/video_source.py::is_live_source.
    """

    def __init__(self, default_path=""):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["File video", "Camera (webcam)", "URL (RTSP/HTTP)"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

        self.stack = QStackedWidget()

        # --- File video ---
        file_widget = QWidget()
        file_layout = QHBoxLayout(file_widget)
        file_layout.setContentsMargins(0, 0, 0, 0)
        self.file_edit = QLineEdit(default_path)
        self.file_edit.setPlaceholderText("Chưa chọn file...")
        browse_btn = QPushButton("Chọn file...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(self.file_edit, stretch=1)
        file_layout.addWidget(browse_btn)

        # --- Camera ---
        cam_widget = QWidget()
        cam_layout = QHBoxLayout(cam_widget)
        cam_layout.setContentsMargins(0, 0, 0, 0)
        cam_layout.addWidget(QLabel("Chỉ số camera:"))
        self.cam_spin = QSpinBox()
        self.cam_spin.setRange(0, 10)
        cam_layout.addWidget(self.cam_spin)
        cam_layout.addStretch(1)

        # --- URL ---
        url_widget = QWidget()
        url_layout = QHBoxLayout(url_widget)
        url_layout.setContentsMargins(0, 0, 0, 0)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("rtsp://... hoặc http://...")
        url_layout.addWidget(self.url_edit)

        self.stack.addWidget(file_widget)
        self.stack.addWidget(cam_widget)
        self.stack.addWidget(url_widget)

        layout.addWidget(self.type_combo)
        layout.addWidget(self.stack)

    def _on_type_changed(self, index):
        self.stack.setCurrentIndex(index)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file video", "",
            "Video files (*.mp4 *.avi *.mov *.mkv);;All files (*.*)",
        )
        if path:
            self.file_edit.setText(path)

    def get_source(self):
        """Trả về source đúng kiểu (str path/URL, hoặc int chỉ số camera)."""
        idx = self.type_combo.currentIndex()
        if idx == 0:
            return self.file_edit.text().strip()
        if idx == 1:
            return self.cam_spin.value()
        return self.url_edit.text().strip()

    def set_enabled(self, enabled):
        self.type_combo.setEnabled(enabled)
        self.stack.setEnabled(enabled)


class ConfSlider(QWidget):
    """1 dòng label + QDoubleSpinBox cho 1 tham số conf/tỉ lệ (0.0 - 1.0)."""

    valueChanged = pyqtSignal(float)

    def __init__(self, label, value, minimum=0.0, maximum=1.0, step=0.05):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel(label))
        self.spin = QDoubleSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.spin.setDecimals(2)
        self.spin.setValue(value)
        self.spin.valueChanged.connect(self.valueChanged.emit)
        layout.addWidget(self.spin)

    def value(self):
        return self.spin.value()

    def set_value(self, v):
        self.spin.blockSignals(True)
        self.spin.setValue(v)
        self.spin.blockSignals(False)


class ControlPanel(QGroupBox):
    """
    Panel điều khiển cho 1 kênh: chọn nguồn, Start/Stop, chỉnh conf live,
    hiện FPS + trạng thái. Không tự chứa logic xử lý gì - chỉ điều khiển
    1 đối tượng channel (FlowHelmetChannel/RedLightChannel) được truyền vào
    qua callback start_channel/stop_channel do MainWindow cung cấp.
    """

    def __init__(self, title, default_source, conf_fields, on_start, on_stop):
        """
        conf_fields: list các tuple (label, attr_path, default_value) mô tả
            tham số conf cần hiện slider, vd:
            [("Conf xe", "tracker.vehicle_conf", 0.5), ...]
            attr_path là đường dẫn attribute trên đối tượng channel, dùng
            getattr/setattr theo từng cấp (vd "tracker.vehicle_conf").
        on_start(source) -> channel: callback tạo + start channel, trả về
            đối tượng channel vừa tạo (hoặc None nếu lỗi).
        on_stop(channel): callback dừng channel.
        """
        super().__init__(title)
        self.conf_fields = conf_fields
        self.on_start = on_start
        self.on_stop = on_stop
        self.channel = None

        layout = QVBoxLayout(self)

        self.source_picker = SourcePicker(default_source if isinstance(default_source, str) else "")
        layout.addWidget(self.source_picker)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ Bắt đầu")
        self.start_btn.setObjectName("primaryButton")
        self.pause_btn = QPushButton("⏸ Tạm dừng")
        self.stop_btn = QPushButton("■ Dừng")
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._handle_start)
        self.pause_btn.clicked.connect(self._handle_pause_toggle)
        self.stop_btn.clicked.connect(self._handle_stop)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.pause_btn)
        btn_layout.addWidget(self.stop_btn)
        layout.addLayout(btn_layout)

        self.status_label = QLabel("● Chưa chạy")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        conf_box = QFormLayout()
        self.sliders = {}
        for label, attr_path, default_value in conf_fields:
            slider = ConfSlider(label, default_value)
            slider.valueChanged.connect(lambda v, p=attr_path: self._on_conf_changed(p, v))
            conf_box.addRow(slider)
            self.sliders[attr_path] = slider
        layout.addLayout(conf_box)

        self.fps_label = QLabel("FPS: --")
        layout.addWidget(self.fps_label)

        self.fps_timer = QTimer(self)
        self.fps_timer.timeout.connect(self._refresh_fps)
        self.fps_timer.start(500)

    def trigger_start(self):
        """Gọi từ bên ngoài (vd MainWindow tự khởi động kênh theo config lúc mở app)."""
        self._handle_start()

    def _handle_start(self):
        source = self.source_picker.get_source()
        if source == "" or source is None:
            self.status_label.setText("● Chưa chọn nguồn hợp lệ")
            return

        self.channel = self.on_start(source)
        if self.channel is None:
            self.status_label.setText("● Lỗi khi khởi động")
            return

        self.source_picker.set_enabled(False)
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("⏸ Tạm dừng")
        self.stop_btn.setEnabled(True)
        self.status_label.setText("● Đang chạy")
        self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")

        # Áp lại giá trị conf hiện tại trên slider vào channel vừa tạo (để
        # nếu người dùng đã chỉnh trước khi bấm Start, giá trị đó được dùng
        # ngay từ đầu thay vì đợi lần valueChanged tiếp theo).
        for attr_path, slider in self.sliders.items():
            set_nested_attr(self.channel, attr_path, slider.value())

    def _handle_pause_toggle(self):
        if self.channel is None:
            return
        if self.channel.paused:
            self.channel.resume()
            self.pause_btn.setText("⏸ Tạm dừng")
            self.status_label.setText("● Đang chạy")
            self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        else:
            self.channel.pause()
            self.pause_btn.setText("▶ Tiếp tục")
            self.status_label.setText("● Đang tạm dừng")
            self.status_label.setStyleSheet("color: #ffb74d; font-weight: bold;")

    def _handle_stop(self):
        if self.channel is not None:
            self.on_stop(self.channel)
        self.channel = None

        self.source_picker.set_enabled(True)
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ Tạm dừng")
        self.stop_btn.setEnabled(False)
        self.status_label.setText("● Đã dừng")
        self.status_label.setStyleSheet("color: #888;")
        self.fps_label.setText("FPS: --")

    def _on_conf_changed(self, attr_path, value):
        # Ghi live vào channel đang chạy (nếu có) - có hiệu lực ngay frame kế tiếp.
        if self.channel is not None:
            set_nested_attr(self.channel, attr_path, value)

    def _refresh_fps(self):
        if self.channel is None:
            return

        if self.channel.thread is not None and not self.channel.thread.is_alive():
            # Thread tự thoát (nguồn lỗi ngay từ đầu, hoặc file video đã hết)
            # -> tự đưa UI về trạng thái "đã dừng" thay vì hiện "Đang chạy" mãi.
            self.channel = None
            self.source_picker.set_enabled(True)
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.pause_btn.setText("⏸ Tạm dừng")
            self.stop_btn.setEnabled(False)
            self.status_label.setText("● Nguồn lỗi hoặc đã hết video")
            self.status_label.setStyleSheet("color: #e57373; font-weight: bold;")
            self.fps_label.setText("FPS: --")
            return

        if getattr(self.channel, "current_fps", 0) > 0:
            self.fps_label.setText(f"FPS: {self.channel.current_fps:.1f}")
