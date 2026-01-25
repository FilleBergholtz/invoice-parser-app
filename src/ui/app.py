"""UI Entry point."""
import sys
from PySide6.QtWidgets import QApplication
from .theme.apply_theme import apply_theme
from .views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    apply_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
