from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

VIOLATION_TYPE_LABELS = {
    "NO_HELMET": "Không đội mũ bảo hiểm",
    "RED_LIGHT": "Vượt đèn đỏ",
}


class ViolationsPanel(QWidget):
    """Tab 'Vi phạm' - hiển thị TRỰC TIẾP các vi phạm ngay khi hệ thống phát
    hiện được (đọc từ channel.violation_queue của cả 2 kênh), KHÔNG PHẢI chỉ
    xem lại qua file CSV/thư mục ảnh sau khi dừng hệ thống. Chọn 1 dòng trong
    bảng để xem 3 ảnh bằng chứng (toàn cảnh/xe/biển số) tương ứng.

    Đây CHỈ là hiển thị tạm thời trong phiên chạy hiện tại (mất khi đóng app)
    - việc lưu vĩnh viễn vẫn do CSV + ảnh trong thư mục outputs/ đảm nhiệm
    như trước, panel này không thay thế mà bổ sung góc nhìn real-time.
    """

    COLUMNS = ["Thời gian", "Kênh", "Loại vi phạm", "Biển số", "Track ID"]

    def __init__(self):
        super().__init__()
        self._rows = []  # list các dict event, cùng thứ tự với các dòng trong bảng

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        self.count_label = QLabel("Tổng vi phạm: 0")
        self.count_label.setObjectName("metricValue")
        header.addWidget(self.count_label)
        header.addStretch(1)
        clear_btn = QPushButton("Xoá danh sách hiển thị")
        clear_btn.setToolTip("Chỉ xoá khỏi danh sách đang hiện tạm thời - KHÔNG xoá file CSV/ảnh đã lưu")
        clear_btn.clicked.connect(self.clear)
        header.addWidget(clear_btn)
        root.addLayout(header)

        body = QHBoxLayout()

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        body.addWidget(self.table, stretch=3)

        preview = QVBoxLayout()
        preview.addWidget(QLabel("Ảnh toàn cảnh"))
        self.scene_label = self._make_image_label()
        preview.addWidget(self.scene_label)

        thumbs = QHBoxLayout()
        vehicle_col = QVBoxLayout()
        vehicle_col.addWidget(QLabel("Phương tiện"))
        self.vehicle_label = self._make_image_label(height=140)
        vehicle_col.addWidget(self.vehicle_label)
        thumbs.addLayout(vehicle_col)

        plate_col = QVBoxLayout()
        plate_col.addWidget(QLabel("Biển số"))
        self.plate_label = self._make_image_label(height=140)
        plate_col.addWidget(self.plate_label)
        thumbs.addLayout(plate_col)
        preview.addLayout(thumbs)

        preview_widget = QWidget()
        preview_widget.setLayout(preview)
        body.addWidget(preview_widget, stretch=2)

        root.addLayout(body)

    @staticmethod
    def _make_image_label(height=220):
        label = QLabel("Chọn 1 dòng để xem ảnh")
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumHeight(height)
        label.setObjectName("imagePreview")
        return label

    def add_violation(self, event):
        """event: dict từ channel.violation_queue (xem channels/*.py). Vi
        phạm mới nhất luôn chèn lên ĐẦU bảng (row 0) - dễ theo dõi khi đang
        xem trực tiếp, giống thứ tự tin nhắn mới nhất trong app chat, không
        phải cuộn xuống cuối bảng để tìm vi phạm vừa xảy ra.
        """
        self.table.insertRow(0)

        type_label = VIOLATION_TYPE_LABELS.get(event["type"], event["type"])
        values = [event["time"], event["channel"], type_label,
                  event["plate"] or "(chưa đọc được)", str(event["track_id"])]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if event["type"] == "RED_LIGHT":
                item.setForeground(Qt.red)
            self.table.setItem(0, col, item)

        self._rows.insert(0, event)
        self.count_label.setText(f"Tổng vi phạm: {len(self._rows)}")

    def _on_row_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        event = self._rows[rows[0].row()]
        self._set_preview(self.scene_label, event.get("scene_image"))
        self._set_preview(self.vehicle_label, event.get("vehicle_image"))
        self._set_preview(self.plate_label, event.get("plate_image"))

    @staticmethod
    def _set_preview(label, path):
        if not path:
            label.setText("Không có ảnh")
            label.setPixmap(QPixmap())
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            label.setText("Không đọc được ảnh\n(file có thể đã bị xoá/di chuyển)")
            return
        label.setPixmap(pixmap.scaled(label.width() or 300, label.height(),
                                       Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def clear(self):
        self.table.setRowCount(0)
        self._rows.clear()
        self.count_label.setText("Tổng vi phạm: 0")
        for label in (self.scene_label, self.vehicle_label, self.plate_label):
            label.setText("Chọn 1 dòng để xem ảnh")
            label.setPixmap(QPixmap())
