# Phase 13: About page + app icons (branding & help) – Discussion / Spec

**Diskuterad:** 2026-01-24  
**Källa:** /gsd:discuss-phase 13

---

## CONTEXT (desktop app, not web)

- **Python desktop application** (NOT web).
- **GUI built with PySide6** (Qt for Python).
- **Engine runs as a subprocess** (CLI) and writes output files that GUI reads.
- **Architecture must remain unchanged.**

---

## FILES / STRUCTURE

| Path | Role |
|------|------|
| run_gui.py | Entry → src/ui/app.main() → QApplication + MainWindow |
| src/ui/app.py | QApplication setup, theme, app icon |
| src/ui/views/main_window.py | Main window, toolbar, menu (Help, Settings), central splitter |
| src/ui/views/about_dialog.py | **New.** About dialog with tabs (Om appen, Hjälp) |
| src/ui/views/pdf_viewer.py | PDF display |
| src/ui/views/ai_settings_dialog.py | AI settings |
| src/ui/services/engine_runner.py | Subprocess run |
| src/ui/theme/ | Existing theme (tokens, app_style.qss, apply_theme) |
| src/ui/assets/icons/ | **New.** SVG (and PNG/ICO) icon assets |
| src/ui/resources.qrc | **New.** Qt resource file for icons |
| src/ui/resources_rc.py | **New.** Compiled resources (pyside6-rcc) |

---

## PHASE GOAL

Add a **professional About page** that:

1. **Helps users understand how the app works.**
2. **Clearly credits the creator** of the application.

Also **replace default Qt icons** with **custom app and UI icons** (branding).

---

## HARD CONSTRAINTS

- **No web views, no HTTP, no backend services.**
- **Changes limited to `src/ui/`** (and asset/resource files under or next to it).
- **Prefer pure PySide6 + Qt resources (QRC).**
- **Minimal, clean, readable changes.**

---

## DELIVERABLES

### 1) About dialog (Help + Credit)

- **Create a new dialog:**
  - File: **src/ui/views/about_dialog.py**
  - Implement as **QDialog**.
- **Dialog structure – Tabs:**
  - **a) "Om appen"**
    - App name
    - Version (from `get_app_version()`)
    - Short description of what the app does: PDF → analysis → review → export
    - **"Skapad av: &lt;author&gt;"** (creator credit)
  - **b) "Hjälp"**
    - Step-by-step usage instructions:
      1. Open PDF
      2. Run analysis
      3. Review results / warnings
      4. Select candidate if needed
      5. Export to Excel
    - Short **troubleshooting** section: missing results, errors, low confidence / AI usage
- Use **existing theme styling** (objectName / QSS where applicable).
- **Access:**
  - Menu: **Help → About** (Hjälp → Om)
  - (Optional) Toolbar or shortcut if appropriate.

### 2) Application and UI icons (branding)

- Replace default Qt icons with **custom icons**.
- **Add icon assets:**
  - Folder: **src/ui/assets/icons/**
  - Use **SVG** for UI icons (action icons).
- **Create Qt resource file:**
  - **src/ui/resources.qrc**
  - Include: app icon + action icons (open, run, export, settings, about).
- **Compile resources** using **pyside6-rcc** and **import resources_rc** in the UI.

### 3) Apply icons in UI

- **Application/window icon:**
  - `app.setWindowIcon(QIcon(":/..."))`
  - `MainWindow.setWindowIcon(...)` (and About dialog).
- **Toolbar and menu actions:**
  - Open, Run, Export, Settings, About — set icons from `:/...` resource paths.
- Icons follow the **visual style** of the app theme.

### 4) Executable icon (Windows)

- Prepare a **multi-size .ico** file for Windows builds.
- Ensure **build process** (e.g. PyInstaller/Nuitka) uses the custom .ico instead of default.
- **No change to build tooling logic** beyond icon configuration (e.g. spec file or build script icon path).

---

## NON-GOALS

- No redesign of existing views.
- No changes to engine, pipeline, or subprocess behavior.
- No licensing/legal UI beyond simple credit text.

---

## ACCEPTANCE CRITERIA

- [ ] App has a **visible, professional About dialog** with help + author credit (tabs: Om appen, Hjälp).
- [ ] **Help menu** contains an **About** entry.
- [ ] App **window, toolbar, and menus** no longer use default Qt icons (custom icons from QRC).
- [ ] **Windows executable** displays correct custom icon in Explorer and taskbar.
- [ ] All changes confined to **src/ui/** and related assets (resources.qrc, assets/icons/, build icon config).

---

## PLAN MAPPING (för exekution)

| Plan | Deliverable | Innehåll |
|------|-------------|----------|
| 13-01 | §1 About dialog | about_dialog.py: QDialog with QTabWidget — "Om appen" (name, version, description, Skapad av), "Hjälp" (steps 1–5 + troubleshooting). Help menu → About in MainWindow. |
| 13-02 | §2–3 Icons (assets + QRC + apply) | src/ui/assets/icons/ (SVG/PNG), resources.qrc, pyside6-rcc → resources_rc; set app/window/toolbar/menu icons via ":/..." |
| 13-03 | §4 Windows .ico | Multi-size .ico for builds; PyInstaller/spec or build script uses custom icon. No refactor of build logic. |

---

*Discussion captured 2026-01-24*
