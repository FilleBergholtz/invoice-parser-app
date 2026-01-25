# 12-06 Plan – Implementation Summary

**Phase:** 12-ui-polish-pyside6  
**Plan:** 06  
**Status:** Implemented

## Changes

### 1. Candidate selector (fixed height, two-line layout)
- **`candidate_selector.py`:** Introduced `CandidateButton` (subclass of `QFrame`), fixed height 56 px, two `QLabel`s (`candidateAmountLabel`, `candidateMetaLabel`). Replaced `QPushButton` list with `CandidateButton` list; tooltips for full meta.
- **`app_style.qss`:** Added styles for `#candidateButton`, `#candidateAmountLabel`, `#candidateMetaLabel` (fixed height, no min-height/padding growth).

### 2. Settings duplication removed
- **`main_window.py`:** Menubar "Inställningar" renamed to **"AI"** with action "AI-inställningar..."; toolbar keeps **"Inställningar"**. Only one "Inställningar" label (toolbar); AI menu opens same dialog.
- **`about_dialog.py`:** Help text updated to "verktygsfältet Inställningar eller menyn AI → AI-inställningar".

### 3. AI settings dialog (two-pane, edit, masked key, Advanced)
- **`ai_settings_dialog.py`:** Refactored to two-pane layout: left `QListWidget` (OpenAI, Claude), right scroll area with detail form. Selecting provider loads form; Save updates current config. API key: placeholder "•••••••• (klicka Ersätt för att ändra)" when key exists, **"Ersätt"** clears and focuses input; **"Visa"** toggles echo. **"Avancerat"** collapsible (toggle button) contains Tröskelvärden and Gränser groups.

### 4. PDF viewer placeholder (no blank state)
- **`pdf_viewer.py`:** `QStackedWidget`: (0) placeholder widget with "PDF laddad. Kör analys för att visa sidor och resultat." and **Kör**-knapp; (1) toolbar + `_PDFGraphicsView`. `_has_analysis_results` drives which page is shown. `load_pdf()` shows placeholder; `set_candidates()` shows content. Signal `run_requested` emitted when Run CTA is clicked.
- **`main_window.py`:** In `set_input_file()` anropar `pdf_viewer.load_pdf(path)` så att placeholder visas direkt efter filval.

### 5. Run next to Open + placeholder CTA + enable/disable
- **`main_window.py`:** Run is already next to Open in toolbar. `pdf_viewer.run_requested` connected to `start_processing`. `pdf_viewer.set_run_button_enabled(False)` at run start, `True` at run finish.
- **`pdf_viewer.py`:** `set_run_button_enabled(enabled)` toggles placeholder Run button.

## Files modified
- `src/ui/views/candidate_selector.py`
- `src/ui/views/ai_settings_dialog.py`
- `src/ui/views/pdf_viewer.py`
- `src/ui/views/main_window.py`
- `src/ui/views/about_dialog.py`
- `src/ui/theme/app_style.qss`

## Verification
- Candidate list: fixed-height items, two-line amount + meta, tooltips.
- One "Inställningar" in toolbar; menyn "AI" öppnar samma dialog.
- AI-dialog: välj provider → redigera → Spara; API-nyckel maskad med Ersätt; Avancerat hopfällbart.
- Efter PDF-öppning: placeholder med text + Kör, ingen tom vit yta.
- Kör tillgänglig i verktygsfältet och i placeholder; inaktiverad under körning.
