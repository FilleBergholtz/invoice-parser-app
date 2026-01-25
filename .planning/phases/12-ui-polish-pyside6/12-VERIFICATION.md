# Phase 12: UI Polish (PySide6) — Verification

**Verifierad:** 2026-01-24

## Per-plan checks (from SUMMARY-filer)

| Plan   | Check | Resultat |
|--------|--------|----------|
| 12-01 | `from src.ui.theme.tokens import *` → "tokens load ok" | ✅ |
| 12-01 | `apply_theme(app)` → "apply_theme ok" | ✅ |
| 12-01 | `from src.ui.app import main` → "app imports and apply_theme is used" | ✅ |
| 12-02 | MainWindow + apply_theme, w.show() → "OK" | ✅ |
| 12-03 | EngineRunner stateChanged, logLine → "signals ok" | ✅ |
| 12-04 | PDFViewer() → "ok" | ✅ |
| 12-05 | AISettingsDialog: 4+ QGroupBox, "Testa anslutning"-knapp → "ok" | ✅ |

## Samlad acceptanstest

Kör:
```bash
python -c "
from PySide6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from src.ui.theme.apply_theme import apply_theme
from src.ui.theme import tokens
apply_theme(app)
from src.ui.views.main_window import MainWindow
w = MainWindow()
assert hasattr(w, 'run_action') and w.centralWidget() is not None
from src.ui.services.engine_runner import EngineRunner
r = EngineRunner('x', 'y')
assert hasattr(r, 'stateChanged') and hasattr(r, 'finished')
assert hasattr(w, '_show_run_error_dialog') and hasattr(w, 'log_toggle_btn')
assert hasattr(w.pdf_viewer, '_page_label') and w.pdf_viewer._view is not None
from src.ui.views.ai_settings_dialog import AISettingsDialog
from PySide6.QtWidgets import QGroupBox, QPushButton
dlg = AISettingsDialog(w)
assert len(dlg.findChildren(QGroupBox)) >= 4
assert any(b.text() == 'Testa anslutning' for b in dlg.findChildren(QPushButton))
print('Phase 12 acceptance: all ok')
"
```
**Resultat:** ✅ Phase 12 acceptance: all ok

## 12-CONTEXT / 12-DISCUSS success criteria

1. **Theme:** Tema appliceras globalt (tokens + QSS + apply_theme i app.py). ✅
2. **Layout:** Toolbar, QSplitter, statusfält, empty state (12-02). ✅
3. **Engine states:** Idle/Running/Success/Error i statusfält; Run inaktiverad under körning; stateChanged, "Visa detaljer" (12-03). ✅
4. **PDF viewer:** Zoom in/ut, Fit bredd, Föregående/Nästa, sidindikator (12-04). ✅
5. **AI-dialog:** Grupper, hjälptexter, "Testa anslutning"-stub, tema (12-05). ✅
6. **Ändringar begränsade till src/ui/.** ✅

## Manuell kontroll (rekommenderas)

- Starta `run_gui.py` (eller `python -m src.ui.app`).
- **Empty state:** Ingen PDF vald → "Öppna en PDF för att börja" + Öppna-knapp.
- **Toolbar:** Öppna PDF (Ctrl+O), Kör (Ctrl+R), Export (Ctrl+E), Inställningar.
- **Välj PDF** → splitter med PDF-viewer vänster, logg/resultat höger; sidindikator och zoom/fit/prev/next i PDF-toolbar.
- **Kör** → Run/Öppna/Export inaktiverade under körning; status "Running"; vid fel → dialog med "Visa detaljer".
- **Inställningar → AI-inställningar:** Fyra grupper (Provider, Modell, Tröskelvärden, Gränser), hjälptexter, "Testa anslutning".

---

*Verification run: 2026-01-24*
