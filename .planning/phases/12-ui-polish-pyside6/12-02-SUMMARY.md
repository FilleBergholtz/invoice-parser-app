# 12-02: MainWindow professional layout — Summary

**Done:** 2026-01-24

## Objective

Refine MainWindow into a professional layout: toolbar (Öppna/Kör/Export/Inställningar), central QSplitter (PDF vänster | resultat/kandidat höger), statusfält med motorstatus och senaste körningssammanfattning, empty state med drag&drop + Öppna-CTA, samt kortkommandon Ctrl+O / Ctrl+R / Ctrl+E. Allt i `src/ui/views/main_window.py`, utan nya beroenden. (12-02-PLAN.md, 12-DISCUSS.md §2)

## Completed tasks

1. **Toolbar**
   - QToolBar med QAction: Öppna PDF (Ctrl+O), Kör (Ctrl+R), Export (Ctrl+E), Inställningar.
   - Öppna → filväljare / `browse_file`; Kör → `start_processing` (inaktiverad tills PDF är vald); Export → `open_output_dir`; Inställningar → `open_ai_settings`.
   - Kortkommandon via `QKeySequence.StandardKey.Open` respektive `QKeySequence("Ctrl+R")` och `QKeySequence("Ctrl+E")`.

2. **Central QSplitter**
   - Huvudinnehållet är antingen empty state eller en horisontell QSplitter.
   - **Vänster:** PDF-viewer (`PDFViewer`).
   - **Höger:** Resultatpanel med input-/output-rader, progress, logg och (vid behov) valideringssektion med kandidatväljare och knappar.
   - Standardstorlek splitter: `[500, 400]`.
   - Växling mellan vyerna via `QStackedWidget`: index 0 = empty state, index 1 = innehåll (splitter).

3. **Statusfält**
   - `QStatusBar` via `self.statusBar().showMessage(...)`.
   - `_update_status_bar(state, summary)` uppdaterar text. Tillstånd: Idle | Running | Success | Error.
   - Motor: `runner.started` → "Running"; `runner.finished(0)` → "Success" + senaste sammanfattning; `runner.error` → "Error" (plus `_on_engine_error` som loggar och sätter status).
   - Senaste körning: från `handle_result` byggs `_last_run_summary` (t.ex. "1 fil, 1 OK" eller "2 filer, 1 OK, 1 review") och visas tillsammans med tillståndet.

4. **Empty state**
   - När ingen PDF är vald: första sidan i stacked widget visar "Öppna en PDF för att börja" och en tydlig **Öppna**-knapp som anropar `browse_file`.
   - Drag & drop: `setAcceptDrops(True)` på fönstret behålls; `dragEnterEvent` / `dropEvent` anropar `set_input_file(path)` vid släpp. Efter val av fil växlas till innehållsvyn (splitter).

5. **Kortkommandon**
   - Ctrl+O (Öppna), Ctrl+R (Kör), Ctrl+E (Export) kopplade till respektive toolbar-aktion; inga extra QShortcut behövdes.

## Verify

- `python -c "from PySide6.QtWidgets import QApplication; from src.ui.theme.apply_theme import apply_theme; from src.ui.views.main_window import MainWindow; import sys; app=QApplication(sys.argv); apply_theme(app); w=MainWindow(); w.show(); print('OK')"` → ok
- Manuellt: starta run_gui, prova Ctrl+O / Ctrl+R / Ctrl+E, empty state → välj PDF → splitter med PDF och panel, statusfält visar Idle/Success/Error och senaste körning.

## Files changed

- `src/ui/views/main_window.py` — toolbar, QStackedWidget (empty | splitter), status bar, `_update_status_bar`, `_on_engine_error`, `_last_run_summary`, ersättning av `validation_widget` med `validation_section` i högerpanelen, borttagen `start_btn`/`status_label` till förmån för `run_action` och statusBar.

## Success criteria ( från 12-02-PLAN )

- MainWindow has top toolbar with Open PDF, Run, Export, Settings — **ja**
- Central content uses QSplitter: left PDF viewer, right results/candidate panel — **ja**
- Status bar shows engine state (Idle/Running/Success/Error) and last run summary — **ja**
- Empty state when no PDF: drag&drop + Open CTA — **ja**
- Shortcuts: Ctrl+O open, Ctrl+R run, Ctrl+E export — **ja**
- All changes in `src/ui/views/main_window.py` — **ja**
