# 12-01: Global theme — Summary

**Done:** 2026-01-25

## Objective

Create a global theme system under `src/ui/theme/` and apply it in `app.py`. No new dependencies; pure PySide6 + QSS. (12-DISCUSS.md §1)

## Completed tasks

1. **Create src/ui/theme/ and tokens.py**
   - Package `src/ui/theme/` with `__init__.py`.
   - `tokens.py`: design tokens — `colors` (primary, background, text, success, warning, error, …), `spacing` (xs–xl), `typography` (font_family, font_size_base/small/large), `radius` (radius_sm/md/lg).
   - `__all__` so `from src.ui.theme.tokens import *` works.

2. **Create app_style.qss**
   - QSS for QPushButton (normal/hover/pressed/disabled, #primary), QLineEdit/QComboBox/QSpinBox, QListWidget/QTableWidget, QDialog/QGroupBox, QToolBar, QStatusBar, QLabel, QScrollBar.
   - Palette: light grey background (#f8fafc), dark text (#0f172a), blue accent (#2563eb).

3. **Create apply_theme.py**
   - `apply_theme(app)`: resolves path to `app_style.qss` next to module, loads with `open()`, `app.setStyleSheet(qss)`.
   - Sets default font from tokens: `QFont(typography["font_family"], typography["font_size_base"])`.

4. **Apply theme in app.py**
   - In `main()`, after `QApplication(sys.argv)`, call `apply_theme(app)` before creating MainWindow.
   - Import `apply_theme` from `src.ui.theme.apply_theme`.

## Verify

- `python -c "from src.ui.theme.tokens import *; print('tokens load ok')"` → ok
- `python -c "from PySide6.QtWidgets import QApplication; from src.ui.theme.apply_theme import apply_theme; import sys; app=QApplication(sys.argv); apply_theme(app); print('apply_theme ok')"` → ok
- `python -c "from src.ui.app import main; print('app imports and apply_theme is used')"` → ok

## Files changed

- `src/ui/theme/__init__.py` — new
- `src/ui/theme/tokens.py` — new
- `src/ui/theme/app_style.qss` — new
- `src/ui/theme/apply_theme.py` — new
- `src/ui/app.py` — call `apply_theme(app)` after QApplication()

## Success criteria

- UI theme applied globally and consistent (tokens + QSS + apply in app.py). All changes under `src/ui/`.
