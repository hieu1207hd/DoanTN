DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
}

QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: #8ab4f8;
}

QPushButton {
    background-color: #2d2d2d;
    border: 1px solid #454545;
    border-radius: 6px;
    padding: 6px 16px;
}

QPushButton:hover {
    background-color: #383838;
    border-color: #8ab4f8;
}

QPushButton:pressed {
    background-color: #444;
}

QPushButton:disabled {
    color: #666;
    background-color: #242424;
    border-color: #333;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #2a2a2a;
    border: 1px solid #454545;
    border-radius: 4px;
    padding: 4px 6px;
    color: #e0e0e0;
}

QComboBox::drop-down {
    border: none;
}

QLabel#statusLabel {
    font-weight: bold;
    padding: 2px 0;
}
"""
