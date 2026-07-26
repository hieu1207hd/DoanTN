from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFormLayout, QLabel, QVBoxLayout, QWidget


class StatsPanel(QWidget):
    """
    Bảng số liệu đặt CẠNH video (không vẽ đè lên video nữa). Chỉ là 1 bảng
    label tĩnh - MainWindow gọi set_values(dict) mỗi khi có frame mới để
    cập nhật, tương ứng đúng dữ liệu của kênh đang hiển thị bên cạnh nó.
    """

    def __init__(self, title, labels):
        super().__init__()
        self.setMinimumWidth(190)

        layout = QVBoxLayout(self)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; padding-bottom: 6px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        self.value_labels = {}
        for label in labels:
            value_label = QLabel("--")
            value_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #8ab4f8;")
            form.addRow(label + ":", value_label)
            self.value_labels[label] = value_label

        layout.addLayout(form)
        layout.addStretch(1)

    def set_values(self, values):
        """values: dict {label: giá trị mới}. Bỏ qua label không tồn tại."""
        for label, val in values.items():
            if label in self.value_labels:
                self.value_labels[label].setText(str(val))

    def clear(self):
        for lbl in self.value_labels.values():
            lbl.setText("--")
