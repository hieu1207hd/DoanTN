from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QLabel


class ROIVideoLabel(QLabel):
    """QLabel hiển thị video, có thêm khả năng cho người dùng CLICK-KÉO chuột
    TRỰC TIẾP trên video đang chạy để chọn ROI - áp dụng ngay vào channel
    đang chạy (qua gui/roi_panel.py), không cần công cụ ngoài, không cần sửa
    config.py + restart như trước.

    2 kiểu chọn:
    - "rect": kéo 1 hình chữ nhật (dùng cho ROI đèn giao thông, vùng rẽ phải).
    - "line": chỉ toạ độ Y lúc THẢ chuột có ý nghĩa (dùng cho vạch dừng, vùng
      nhận diện mũ bảo hiểm - vốn chỉ là 1 đường ngang, không phải vùng).

    Toạ độ phát ra qua signal roi_selected LUÔN là toạ độ trên FRAME (đúng hệ
    toạ độ mà các hằng số ROI trong config.py dùng - frame đã resize theo
    RESIZE_WIDTH), KHÔNG phải toạ độ pixel trên widget - vì pixmap hiển thị
    bị scale + căn giữa (letterbox) nên 2 hệ toạ độ này khác nhau.
    """

    roi_selected = pyqtSignal(tuple)  # rect: (x1,y1,x2,y2) | line: (y,)

    def __init__(self):
        super().__init__()
        self.edit_mode = None  # None | "rect" | "line"
        self._frame_w = None
        self._frame_h = None
        self._drag_start = None
        self._drag_current = None
        self.setMouseTracking(True)

    def set_frame_size(self, w, h):
        """Gọi mỗi lần có frame mới (từ ChannelPanel.show_frame) - cần biết
        kích thước frame GỐC (trước khi QLabel scale để hiển thị) để quy đổi
        toạ độ chuột (trên widget) về toạ độ frame."""
        self._frame_w, self._frame_h = w, h

    @property
    def frame_size(self):
        """(w, h) của frame gốc lần gần nhất, hoặc None nếu chưa có frame nào
        - dùng khi cần quy đổi giá trị pixel tuyệt đối sang tỉ lệ (0-1), vd
        gui/roi_panel.py lúc lưu ROI dạng "line" xuống config.py."""
        if not self._frame_w or not self._frame_h:
            return None
        return self._frame_w, self._frame_h

    def set_edit_mode(self, mode):
        self.edit_mode = mode
        self._drag_start = None
        self._drag_current = None
        self.setCursor(Qt.CrossCursor if mode else Qt.ArrowCursor)
        self.update()

    def _display_rect(self):
        """Vùng (trong toạ độ widget) đang thực sự hiển thị pixmap. QLabel
        AlignCenter căn giữa pixmap đã scale bên trong label - phần thừa 2
        bên là khoảng trống (letterbox khi tỉ lệ khung hình video khác tỉ lệ
        panel) - PHẢI trừ offset này, nếu không ROI chọn được sẽ bị lệch.
        """
        pixmap = self.pixmap()
        if pixmap is None:
            return None
        pw, ph = pixmap.width(), pixmap.height()
        lw, lh = self.width(), self.height()
        return (lw - pw) // 2, (lh - ph) // 2, pw, ph

    def _widget_to_frame(self, pos):
        disp = self._display_rect()
        if disp is None or not self._frame_w or not self._frame_h:
            return None
        ox, oy, pw, ph = disp
        x, y = pos.x() - ox, pos.y() - oy
        if pw == 0 or ph == 0 or x < 0 or y < 0 or x > pw or y > ph:
            return None
        fx = int(x * self._frame_w / pw)
        fy = int(y * self._frame_h / ph)
        return max(0, min(self._frame_w - 1, fx)), max(0, min(self._frame_h - 1, fy))

    def _frame_to_widget(self, fx, fy):
        disp = self._display_rect()
        ox, oy, pw, ph = disp
        return ox + int(fx * pw / self._frame_w), oy + int(fy * ph / self._frame_h)

    def mousePressEvent(self, event):
        if self.edit_mode and event.button() == Qt.LeftButton:
            pt = self._widget_to_frame(event.pos())
            if pt is not None:
                self._drag_start = pt
                self._drag_current = pt
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.edit_mode and self._drag_start is not None:
            pt = self._widget_to_frame(event.pos())
            if pt is not None:
                self._drag_current = pt
                self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.edit_mode and self._drag_start is not None and self._drag_current is not None:
            x1, y1 = self._drag_start
            x2, y2 = self._drag_current

            if self.edit_mode == "rect":
                rect = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
                # Bỏ qua click nhầm/kéo quá ngắn (dễ xảy ra nếu người dùng chỉ
                # bấm chuột 1 phát mà không kéo) - tránh tạo ROI 1-2px vô nghĩa.
                if rect[2] - rect[0] >= 4 and rect[3] - rect[1] >= 4:
                    self.roi_selected.emit(rect)
            elif self.edit_mode == "line":
                self.roi_selected.emit((y2,))

        self._drag_start = None
        self._drag_current = None
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)  # vẽ pixmap (video) như QLabel bình thường trước
        if not self.edit_mode or self._drag_start is None or self._drag_current is None:
            return
        if self._display_rect() is None:
            return

        ox, oy, pw, ph = self._display_rect()
        painter = QPainter(self)
        painter.setPen(QPen(QColor(0, 220, 255), 2, Qt.DashLine))

        if self.edit_mode == "rect":
            x1, y1 = self._frame_to_widget(*self._drag_start)
            x2, y2 = self._frame_to_widget(*self._drag_current)
            painter.drawRect(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
        elif self.edit_mode == "line":
            _, y = self._frame_to_widget(*self._drag_current)
            painter.drawLine(ox, y, ox + pw, y)

        painter.end()
