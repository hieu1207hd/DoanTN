# Bảng màu dùng chung, giữ tối giản (không quá nhiều màu nhấn) cho cảm giác
# chuyên nghiệp thay vì sặc sỡ - chỉ 1 màu nhấn chính (xanh dương nhạt) +
# 2 màu cảnh báo chuẩn (đỏ = vi phạm/lỗi, cam = tạm dừng/cảnh báo, xanh lá =
# đang chạy bình thường) dùng xuyên suốt cả 2 theme.
ACCENT = "#5b8def"
DANGER = "#e5484d"
WARNING = "#f5a524"
SUCCESS = "#3dd68c"

DARK_STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: #17181c;
    color: #e6e6e6;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QGroupBox {{
    background-color: #1e2025;
    border: 1px solid #2c2e34;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: {ACCENT};
}}

QPushButton {{
    background-color: #262832;
    border: 1px solid #383b46;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: #2f323d;
    border-color: {ACCENT};
}}

QPushButton:pressed {{
    background-color: #1c1e24;
}}

QPushButton:disabled {{
    color: #5a5c66;
    background-color: #1a1b20;
    border-color: #262832;
}}

QPushButton#primaryButton {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: #0e0f12;
    font-weight: 600;
}}

QPushButton#primaryButton:hover {{
    background-color: #6f9bf2;
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: #21232a;
    border: 1px solid #383b46;
    border-radius: 5px;
    padding: 5px 7px;
    color: #e6e6e6;
    selection-background-color: {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
}}

QLabel#statusLabel {{
    font-weight: 700;
    padding: 2px 0;
}}

QLabel#metricValue {{
    color: {ACCENT};
    font-weight: 700;
    font-size: 14px;
}}

QLabel#sectionTitle {{
    color: {ACCENT};
    font-weight: 700;
    font-size: 15px;
    padding: 2px 0 6px 0;
}}

QLabel#imagePreview {{
    background-color: #0e0f12;
    border: 1px dashed #383b46;
    border-radius: 8px;
    color: #6a6c76;
}}

QTabWidget::pane {{
    border: 1px solid #2c2e34;
    border-radius: 10px;
    top: -1px;
}}

QTabBar::tab {{
    background: #1e2025;
    border: 1px solid #2c2e34;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 9px 22px;
    margin-right: 3px;
    color: #9a9ca6;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background: #262832;
    color: {ACCENT};
}}

QTabBar::tab:hover {{
    color: #e6e6e6;
}}

QTableWidget {{
    background-color: #1e2025;
    alternate-background-color: #21232a;
    gridline-color: #2c2e34;
    border: 1px solid #2c2e34;
    border-radius: 8px;
    selection-background-color: #33405c;
    selection-color: #e6e6e6;
}}

QHeaderView::section {{
    background-color: #21232a;
    color: {ACCENT};
    padding: 6px;
    border: none;
    border-bottom: 1px solid #2c2e34;
    font-weight: 600;
}}

QScrollBar:vertical {{
    background: #17181c;
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: #383b46;
    border-radius: 5px;
    min-height: 24px;
}}
"""

LIGHT_STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: #f5f6f8;
    color: #202124;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}}

QGroupBox {{
    background-color: #ffffff;
    border: 1px solid #dcdfe4;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 14px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #3568d4;
}}

QPushButton {{
    background-color: #ffffff;
    border: 1px solid #d0d4db;
    border-radius: 6px;
    padding: 7px 18px;
    color: #202124;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: #eef2fb;
    border-color: #3568d4;
}}

QPushButton:pressed {{
    background-color: #e2e7f0;
}}

QPushButton:disabled {{
    color: #a7abb3;
    background-color: #f0f1f3;
    border-color: #e2e5ea;
}}

QPushButton#primaryButton {{
    background-color: #3568d4;
    border-color: #3568d4;
    color: #ffffff;
    font-weight: 600;
}}

QPushButton#primaryButton:hover {{
    background-color: #4a78dd;
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: #ffffff;
    border: 1px solid #d0d4db;
    border-radius: 5px;
    padding: 5px 7px;
    color: #202124;
    selection-background-color: #3568d4;
    selection-color: #ffffff;
}}

QComboBox::drop-down {{
    border: none;
}}

QLabel#statusLabel {{
    font-weight: 700;
    padding: 2px 0;
}}

QLabel#metricValue {{
    color: #3568d4;
    font-weight: 700;
    font-size: 14px;
}}

QLabel#sectionTitle {{
    color: #3568d4;
    font-weight: 700;
    font-size: 15px;
    padding: 2px 0 6px 0;
}}

QLabel#imagePreview {{
    background-color: #eceef2;
    border: 1px dashed #c3c8d1;
    border-radius: 8px;
    color: #7b7f88;
}}

QTabWidget::pane {{
    border: 1px solid #dcdfe4;
    border-radius: 10px;
    top: -1px;
    background: #ffffff;
}}

QTabBar::tab {{
    background: #eceef2;
    border: 1px solid #dcdfe4;
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 9px 22px;
    margin-right: 3px;
    color: #5f6368;
    font-weight: 600;
}}

QTabBar::tab:selected {{
    background: #ffffff;
    color: #3568d4;
}}

QTabBar::tab:hover {{
    color: #202124;
}}

QTableWidget {{
    background-color: #ffffff;
    alternate-background-color: #f5f6f8;
    gridline-color: #e2e5ea;
    border: 1px solid #dcdfe4;
    border-radius: 8px;
    selection-background-color: #d7e3fb;
    selection-color: #202124;
}}

QHeaderView::section {{
    background-color: #f0f1f3;
    color: #3568d4;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #dcdfe4;
    font-weight: 600;
}}

QScrollBar:vertical {{
    background: #f5f6f8;
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: #c3c8d1;
    border-radius: 5px;
    min-height: 24px;
}}
"""

THEMES = {"dark": DARK_STYLESHEET, "light": LIGHT_STYLESHEET}
