# Phase 12: UI Polish (PySide6) – Discussion / Spec

**Diskuterad:** 2026-01-25  
**Källa:** /gsd:discuss-phase 12

---

## CONTEXT (desktop app, not web)

- Python desktop app with **PySide6 (Qt)**. No browser frontend. No HTTP services.
- GUI runs engine as **subprocess** (run_engine.py / packaged exe) and reads **output files** (run_summary.json, Excel).
- **Keep subprocess + files approach.** No client–server.

---

## FILES / STRUCTURE

| Path | Role |
|------|------|
| run_gui.py | Entry → src/ui/app.main() → QApplication + MainWindow |
| src/ui/app.py | QApplication setup, theme application point |
| src/ui/views/main_window.py | Main window, toolbar, central splitter, status bar |
| src/ui/views/pdf_viewer.py | PDF display + viewer toolbar |
| src/ui/views/ai_settings_dialog.py | AI provider/model/thresholds dialog |
| src/ui/views/candidate_selector.py | Validation candidate list |
| src/ui/services/engine_runner.py | Subprocess run, signals, state |

---

## PHASE GOAL

Make the UI **modern, consistent, and professional** (enterprise feel) **without changing architecture.**

---

## HARD CONSTRAINTS

- **No HTTP API layer, no services.**
- **Minimal readable changes, constrained to `src/ui/`.**
- **Avoid new dependencies;** prefer pure PySide6 + QSS.

---

## DELIVERABLES

### 1) Global theme system

- **Create `src/ui/theme/`:**
  - **tokens.py** – design tokens: colors, spacing scale, typography sizes, radius.
  - **app_style.qss** – modern QSS for: buttons, inputs, lists/tables, dialogs, toolbar, statusbar.
  - **apply_theme.py** – loads QSS + sets app font/palette (e.g. `apply_theme(app)`).
- **Apply theme globally** in `src/ui/app.py` right after `QApplication()`.

### 2) MainWindow professional layout

- **main_window.py:**
  - **Top toolbar actions:** Open PDF, Run, Export, Settings.
  - **Central QSplitter:** left = PDF viewer, right = results/candidate panel.
  - **Status bar** showing engine state: **Idle / Running / Success / Warning / Error** + last run summary (e.g. file count, OK/REVIEW).
  - **Empty state** when no PDF loaded: drag&amp;drop + “Open” CTA.
  - **Shortcuts:** Ctrl+O open, Ctrl+R run, Ctrl+E export.

### 3) Engine runner UX states

- **engine_runner.py:**
  - Standardize **states** and emit **signals:** `stateChanged`, `progressChanged` (step-based ok), `logLine`, `finished(success, paths)`.
  - **While Running:** disable/enable controls correctly; show progress + optional expandable log panel (stdout/stderr).
  - **On Error:** user-friendly dialog + “Show details” expandable (no raw trace in main message).

### 4) PDF viewer polish

- **pdf_viewer.py:**
  - **Viewer toolbar:** Zoom in/out, Fit width, Prev/Next page, page indicator/input.
  - Styled via theme (no new dependencies).

### 5) AI settings dialog polish

- **ai_settings_dialog.py:**
  - **Grouped settings:** Provider / Model / Thresholds / Limits.
  - **Help text** under key fields.
  - Optional **“Test connection”** button (if feasible without architecture changes; otherwise stub with validation UX).
  - Buttons and inputs follow theme.

---

## NON-GOALS

- No engine/pipeline refactor.
- No new backend/service layer.

---

## DONE / ACCEPTANCE

- [ ] UI theme applied globally and consistent (tokens + QSS + apply in app.py).
- [ ] MainWindow feels like a product: toolbar + splitter + status + empty state.
- [ ] Engine run UX has robust states, progress, and safe error messaging (stateChanged, progress, “Show details”).
- [ ] PDF viewer has basic pro navigation controls (zoom, fit, prev/next, page).
- [ ] Changes limited to **src/ui/** with clear file-level edits.

---

## PLAN MAPPING (för exekution)

| Plan | Deliverable | Innehåll |
|------|-------------|----------|
| 12-01 | §1 Theme | src/ui/theme/ (tokens, app_style.qss, apply_theme), apply in app.py |
| 12-02 | §2 MainWindow layout | Toolbar, QSplitter, status bar, empty state, shortcuts |
| 12-03 | §3 Engine runner UX | States, signals, progress, log panel, error dialog |
| 12-04 | §4 PDF viewer | Toolbar zoom/fit/prev/next, page indicator, theme |
| 12-05 | §5 AI settings dialog | Groups, help text, Test connection stub, theme |

---

*Discussion captured 2026-01-25*
