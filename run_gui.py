import os
import sys
_APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
sys.path.insert(0, _APP_DIR)
os.chdir(_APP_DIR)

from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.theme import DARK_STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
