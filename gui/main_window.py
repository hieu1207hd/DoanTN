import queue

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QTabWidget, QVBoxLayout, QWidget,
)

import config
from channels.flow_helmet_channel import FlowHelmetChannel
from channels.redlight_channel import RedLightChannel
from gui.channel_panel import ChannelPanel
from gui.control_panel import ControlPanel
from gui.roi_panel import ROIPanel
from gui.setup_panel import SetupPanel
from gui.stats_panel import StatsPanel
from gui.theme import THEMES
from gui.violations_panel import ViolationsPanel


class MainWindow(QMainWindow):
    """
    Cửa sổ chính: 1 window, QTabWidget với 2 tab:
    - "Trung tâm giám sát": 2 cột cạnh nhau, mỗi cột = video panel (trên) +
      control panel (dưới) của ĐÚNG 1 kênh. 2 cột hoàn toàn độc lập: mỗi
      ControlPanel tự quản lý channel của riêng nó (tạo/dừng/đổi nguồn/chỉnh
      conf), MainWindow chỉ lo phần hiển thị frame (đọc qua timer riêng
      từng cột).
    - "Vi phạm": bảng vi phạm cập nhật TRỰC TIẾP (không phải chỉ xem lại qua
      CSV sau khi dừng) - đọc từ channel.violation_queue của cả 2 kênh.
    """

    REFRESH_MS = 30  # ~33 FPS hiển thị tối đa (không phải FPS xử lý thật của channel)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hệ thống giám sát giao thông")
        self.resize(1440, 900)

        self._theme = "dark"

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(12, 10, 12, 10)
        central_layout.setSpacing(8)
        self.setCentralWidget(central)

        # ===== Thanh tiêu đề trên cùng: tên hệ thống + nút đổi theme =====
        topbar = QHBoxLayout()
        title_label = QLabel("🚦 Hệ thống giám sát giao thông")
        title_label.setObjectName("sectionTitle")
        topbar.addWidget(title_label)
        topbar.addStretch(1)
        self.theme_btn = QPushButton("☀ Giao diện sáng")
        self.theme_btn.clicked.connect(self._toggle_theme)
        topbar.addWidget(self.theme_btn)
        central_layout.addLayout(topbar)

        self.tabs = QTabWidget()
        central_layout.addWidget(self.tabs)

        # ===== Tab 1: Trung tâm giám sát =====
        dashboard = QWidget()
        main_layout = QHBoxLayout(dashboard)

        # ----- Cột 1: Channel 1 - Lưu lượng + Mũ bảo hiểm -----
        col1 = QVBoxLayout()
        row1 = QHBoxLayout()
        self.panel1 = ChannelPanel("Channel 1 - Lưu lượng + Mũ bảo hiểm")
        self.stats1 = StatsPanel(
            "Số liệu",
            ["Tổng xe"] + list(config.VEHICLE_CLASS_NAMES.values()) + ["Không đội mũ", "Kết nối", "FPS"],
        )
        row1.addWidget(self.panel1, stretch=3)
        row1.addWidget(self.stats1, stretch=1)
        # ROIPanel: cho phép kéo chuột TRỰC TIẾP trên video đang chạy để
        # chỉnh vùng nhận diện, áp dụng ngay (không cần sửa config.py +
        # restart) - xem gui/roi_panel.py.
        self.roi_panel1 = ROIPanel(
            video_label=self.panel1.video_label,
            get_channel=lambda: self.control1.channel,
            roi_specs=[
                {"label": "Vùng nhận diện (mũ bảo hiểm/biển số)", "kind": "line",
                 "attr": "detect_zone_y", "config_name": "DETECT_ZONE_RATIO"},
            ],
        )
        self.control1 = ControlPanel(
            title="Điều khiển - Channel 1",
            default_source=config.SOURCE_CH1,
            conf_fields=[
                ("Conf xe (car/motorbike)", "tracker.vehicle_conf", config.VEHICLE_CONF),
                ("Conf person (tìm người)", "tracker.context_conf", config.PERSON_CONF),
                ("Conf mũ bảo hiểm", "helmet_detector.conf", config.HELMET_CONF),
                ("Conf biển số", "plate_detector.conf", config.PLATE_CONF),
            ],
            on_start=self._start_channel1,
            on_stop=self._stop_channel1,
        )
        col1.addLayout(row1, stretch=1)
        col1.addWidget(self.roi_panel1)
        col1.addWidget(self.control1)

        # ----- Cột 2: Channel 2 - Vượt đèn đỏ -----
        col2 = QVBoxLayout()
        row2 = QHBoxLayout()
        self.panel2 = ChannelPanel("Channel 2 - Vượt đèn đỏ")
        self.stats2 = StatsPanel("Số liệu", ["Vượt đèn đỏ", "Đèn hiện tại", "Kết nối", "FPS"])
        row2.addWidget(self.panel2, stretch=3)
        row2.addWidget(self.stats2, stretch=1)
        self.roi_panel2 = ROIPanel(
            video_label=self.panel2.video_label,
            get_channel=lambda: self.control2.channel,
            roi_specs=[
                {"label": "ROI đèn giao thông", "kind": "rect",
                 "attr": "detector.roi", "config_name": "TRAFFIC_LIGHT_ROI"},
                {"label": "Vạch dừng", "kind": "line",
                 "attr": "checker.stop_line_y", "config_name": "STOP_LINE_Y_RATIO"},
            ],
        )
        self.control2 = ControlPanel(
            title="Điều khiển - Channel 2",
            default_source=config.SOURCE_CH2,
            conf_fields=[
                ("Conf xe (car/motorbike)", "tracker.vehicle_conf", config.VEHICLE_CONF),
                ("Conf biển số", "plate_detector.conf", config.PLATE_CONF),
            ],
            on_start=self._start_channel2,
            on_stop=self._stop_channel2,
        )
        col2.addLayout(row2, stretch=1)
        col2.addWidget(self.roi_panel2)
        col2.addWidget(self.control2)

        main_layout.addLayout(col1, stretch=1)
        main_layout.addLayout(col2, stretch=1)

        self.tabs.addTab(dashboard, "📹 Trung tâm giám sát")

        # ===== Tab 2: Vi phạm (real-time, không phải chỉ xem lại CSV) =====
        self.violations_panel = ViolationsPanel()
        self.tabs.addTab(self.violations_panel, "⚠ Vi phạm")

        # ===== Tab 3: Cấu hình hệ thống (chọn nhanh theo hiệu năng máy) =====
        self.setup_panel = SetupPanel()
        self.tabs.addTab(self.setup_panel, "⚙ Cấu hình hệ thống")

        self.timer1 = QTimer(self)
        self.timer1.timeout.connect(self._update_panel1)
        self.timer1.start(self.REFRESH_MS)

        self.timer2 = QTimer(self)
        self.timer2.timeout.connect(self._update_panel2)
        self.timer2.start(self.REFRESH_MS)

        # Giữ hành vi tương thích: nếu config bật sẵn ENABLE_CHANNEL1/2, tự
        # bắt đầu ngay khi mở app - người dùng vẫn có thể Dừng/đổi nguồn/
        # Bắt đầu lại bất cứ lúc nào qua control panel bên dưới video.
        if config.ENABLE_CHANNEL1:
            self.control1.trigger_start()
        else:
            self.panel1.show_placeholder("Chọn nguồn rồi bấm Bắt đầu")

        if config.ENABLE_CHANNEL2:
            self.control2.trigger_start()
        else:
            self.panel2.show_placeholder("Chọn nguồn rồi bấm Bắt đầu")

    # ----- theme sáng/tối -----
    def _toggle_theme(self):
        self._theme = "light" if self._theme == "dark" else "dark"
        QApplication.instance().setStyleSheet(THEMES[self._theme])
        self.theme_btn.setText("☀ Giao diện sáng" if self._theme == "dark" else "🌙 Giao diện tối")

    # ----- callback tạo/dừng channel, do ControlPanel gọi -----
    def _start_channel1(self, source):
        channel = FlowHelmetChannel(source)
        channel.start()
        return channel

    def _stop_channel1(self, channel):
        channel.stop()
        self.panel1.show_placeholder("Đã dừng - chọn nguồn rồi bấm Bắt đầu")

    def _start_channel2(self, source):
        channel = RedLightChannel(source)
        channel.start()
        return channel

    def _stop_channel2(self, channel):
        channel.stop()
        self.panel2.show_placeholder("Đã dừng - chọn nguồn rồi bấm Bắt đầu")

    # ----- hiển thị frame + số liệu, đọc qua đúng channel hiện tại của mỗi ControlPanel -----
    def _update_panel1(self):
        channel = self.control1.channel
        if channel is None:
            self.stats1.clear()
            return

        frame = channel.get_latest_frame()
        if frame is not None:
            self.panel1.show_frame(frame)

        values = {"FPS": f"{channel.current_fps:.1f}", "Kết nối": self._connection_status(channel)}
        if channel.flow is not None:
            values["Tổng xe"] = channel.flow.total
            # Lấy tên cột trực tiếp từ config.VEHICLE_CLASS_NAMES (thay vì gõ
            # cứng "Ô tô"/"Xe máy" như bản gốc chỉ có 2 loại COCO) - đổi model
            # sang bộ class khác chỉ cần sửa config.py, GUI tự cập nhật theo,
            # không phải sửa lại chỗ này.
            for cls_id, name in config.VEHICLE_CLASS_NAMES.items():
                values[name] = channel.flow.counts_by_class.get(cls_id, 0)
        if channel.helmet_votes is not None:
            values["Không đội mũ"] = len(channel.helmet_votes.violated_ids)
        self.stats1.set_values(values)

        self._drain_violations(channel)

    def _update_panel2(self):
        channel = self.control2.channel
        if channel is None:
            self.stats2.clear()
            return

        frame = channel.get_latest_frame()
        if frame is not None:
            self.panel2.show_frame(frame)

        values = {"FPS": f"{channel.current_fps:.1f}", "Kết nối": self._connection_status(channel)}
        if channel.checker is not None:
            values["Vượt đèn đỏ"] = len(channel.checker.violated_ids)
        values["Đèn hiện tại"] = "ĐỎ" if getattr(channel, "is_red", False) else "Không đỏ"
        self.stats2.set_values(values)

        self._drain_violations(channel)

    def _drain_violations(self, channel):
        """Đọc HẾT các sự kiện vi phạm mới có trong hàng đợi của channel (có
        thể nhiều sự kiện dồn dập giữa 2 lần timer) và đẩy vào tab Vi phạm.
        """
        queue_ = getattr(channel, "violation_queue", None)
        if queue_ is None:
            return
        while True:
            try:
                event = queue_.get_nowait()
            except queue.Empty:
                break
            self.violations_panel.add_violation(event)

    @staticmethod
    def _connection_status(channel):
        """"--" cho file video (không có khái niệm mất kết nối). Với camera/
        URL: "Đang thử kết nối lại..." khi LiveFrameGrabber phát hiện rớt kết
        nối - xem utils/video_source.py::LiveFrameGrabber._reconnect."""
        grabber = getattr(channel, "grabber", None)
        if grabber is None:
            return "--"
        return "OK" if grabber.connected else "Đang thử kết nối lại..."

    def closeEvent(self, event):
        self.timer1.stop()
        self.timer2.stop()
        if self.control1.channel is not None:
            self.control1.channel.stop()
        if self.control2.channel is not None:
            self.control2.channel.stop()
        event.accept()
