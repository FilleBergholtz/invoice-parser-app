"""UI Entry point."""
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from . import resources_rc  # noqa: F401 - register resources
from .theme.apply_theme import apply_theme
from .views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    app.setWindowIcon(QIcon(":/icons/app.svg"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
