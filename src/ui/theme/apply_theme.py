"""Apply global theme to QApplication: load QSS and set default font."""

from pathlib import Path
from typing import TYPE_CHECKING

from . import tokens

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication


def apply_theme(app: "QApplication") -> None:
    """Load app_style.qss, set app stylesheet and default font.

    Resolves QSS path relative to this module. Uses tokens for font.
    """
    # Path to app_style.qss (next to apply_theme.py)
    this_dir = Path(__file__).resolve().parent
    qss_path = this_dir / "app_style.qss"

    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            qss = f.read()
        app.setStyleSheet(qss)

    # Default font from tokens
    from PySide6.QtGui import QFont

    family = tokens.typography.get("font_family", "Segoe UI")
    size = tokens.typography.get("font_size_base", 10)
    font = QFont(family, size)
    app.setFont(font)
