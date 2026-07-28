import cv2
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from gui.roi_video_label import ROIVideoLabel


class ChannelPanel(QWidget):
    """
    1 panel hiển thị video cho 1 kênh (Channel 1 hoặc Channel 2).

    Panel này CHỈ lo hiển thị - không tự đọc video, không tự chạy model gì
    cả. Frame đã được channel (FlowHelmetChannel/RedLightChannel) xử lý và
    vẽ sẵn bbox/overlay từ trước; panel chỉ nhận numpy array (BGR, từ
    OpenCV) qua show_frame() và convert sang QPixmap để vẽ lên QLabel.
    """

    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setObjectName("sectionTitle")

        self.video_label = ROIVideoLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(320, 240)
        self.video_label.setStyleSheet("background-color: #202020; color: #999; border-radius: 6px;")
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setText("Đang chờ dữ liệu...")

        layout.addWidget(self.title_label)
        layout.addWidget(self.video_label, stretch=1)

    def show_frame(self, frame):
        """frame: numpy array BGR (định dạng chuẩn của OpenCV)."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        self.video_label.set_frame_size(w, h)  # để ROIVideoLabel quy đổi toạ độ chuột -> toạ độ frame
        bytes_per_line = ch * w
        # .copy() bắt buộc: QImage chỉ giữ tham chiếu tới buffer của rgb, nếu
        # không copy, dữ liệu có thể bị giải phóng/ghi đè trước khi vẽ xong.
        qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(qimg)

        # Co giãn vừa khung hiện tại nhưng giữ tỉ lệ khung hình (video dọc
        # sẽ không bị méo dù panel ngang) - tính lại mỗi lần vẽ nên tự thích
        # nghi khi người dùng resize cửa sổ.
        scaled = pixmap.scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled)

    def show_placeholder(self, text):
        self.video_label.setText(text)
