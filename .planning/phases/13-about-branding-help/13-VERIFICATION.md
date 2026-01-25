# Phase 13: About page + app icons (branding & help) — Verification

**Status:** Not yet run (phase discussed 2026-01-24). Spec: 13-DISCUSS.md.

## Per-plan checks (to be filled when plans are executed)

| Plan   | Check | Resultat |
|--------|--------|----------|
| 13-01 | Help menu exists; About opens tabbed dialog (Om appen + Hjälp) with name, version, Skapad av, steps, troubleshooting | (pending) |
| 13-02 | src/ui/assets/icons/ + resources.qrc + resources_rc.py; app/window/toolbar/menu use ":/..." icons | (pending) |
| 13-03 | Multi-size .ico exists; build uses it; Windows .exe shows custom icon in Explorer/taskbar | (pending) |

## Acceptance (from 13-DISCUSS.md)

- [ ] App has a visible, professional About dialog with help + author credit (tabs: Om appen, Hjälp).
- [ ] Help menu contains an About entry.
- [ ] App window, toolbar, and menus no longer use default Qt icons (custom icons from QRC).
- [ ] Windows executable displays correct custom icon in Explorer and taskbar.
- [ ] All changes confined to src/ui/ and related assets.

## Samlad acceptanstest (för körning efter 13-01–13-03)

1. Starta `run_gui.py`.
2. Öppna **Hjälp → Om**. Kontrollera flikar "Om appen" (namn, version, Skapad av, beskrivning) och "Hjälp" (steg 1–5, felsökning).
3. Kontrollera att huvudfönster, toolbar och menyer visar egna ikoner (inga standard-Qt-ikoner).
4. Vid Windows-build: bygg exe och verifiera att ikonen visas i Utforskaren och i taskbar.

---

*Uppdaterad 2026-01-24 — /gsd:discuss-phase 13*
