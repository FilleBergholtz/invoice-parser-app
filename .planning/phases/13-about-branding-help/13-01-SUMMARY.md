---
phase: 13-about-branding-help
plan: "01"
subsystem: ui
tags: [PySide6, QDialog, QTabWidget, about, help]

# Dependency graph
requires: []
provides:
  - AboutDialog (Om appen + Hjälp)
  - Help menu with About action in MainWindow
affects: [13-02 icons]

# Tech tracking
tech-stack:
  added: []
  patterns: [tabbed about dialog, theme objectName]

key-files:
  created: [src/ui/views/about_dialog.py]
  modified: [src/ui/views/main_window.py]

key-decisions: []

# Metrics
duration: 5min
completed: "2026-01-25"
---

# Phase 13 Plan 01: About Dialog + Help Menu Summary

**Tabbed About dialog (Om appen, Hjälp) and Help → About in MainWindow.**

## Performance

- **Duration:** ~5 min
- **Tasks:** 2/2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `AboutDialog` in `src/ui/views/about_dialog.py`: QDialog with QTabWidget.
- Tab "Om appen": app name, version (`get_app_version()`), short description (PDF → analysis → review → export), "Skapad av: EPG".
- Tab "Hjälp": step-by-step usage (1–5) and short troubleshooting (saknade resultat, fel, låg konfidens/AI).
- MainWindow: "Hjälp" menu with "Om EPG PDF Extraherare..." opening AboutDialog modally.

## Task Commits

1. **Task 1: Create AboutDialog** – `8091d13` (feat)
2. **Task 2: Add Help menu and About action** – `ab715a7` (feat)

## Files Created/Modified

- `src/ui/views/about_dialog.py` – New. AboutDialog with Om appen + Hjälp tabs, theme styling.
- `src/ui/views/main_window.py` – Help menu, About action, `open_about()`.

## Deviations from Plan

None – plan followed.

## Next Step

Ready for 13-02-PLAN.md (icons: assets, resources.qrc, apply in UI).
