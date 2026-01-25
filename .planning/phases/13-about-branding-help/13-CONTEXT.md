# Phase 13: About page + app icons (branding & help) – Context

**Tillagd:** 2026-01-24  
**Status:** Planned  
**Spec:** Se **13-DISCUSS.md** för CONTEXT, HARD CONSTRAINTS, DELIVERABLES (1–4), NON-GOALS, ACCEPTANCE och PLAN MAPPING.

---

## Mål

1. **About-sida:** Professionell dialog som förklarar hur appen fungerar och anger skaparen (Skapad av).
2. **Branding:** Ersätt standard-Qt-ikoner med egna app- och UI-ikoner (fönster, toolbar, menyer); Windows-.ico för executable.

---

## Scope (kort)

- **About-dialog:** QDialog med flikar **"Om appen"** (namn, version, beskrivning, Skapad av) och **"Hjälp"** (steg-för-steg + felsökning). Öppnas via **Hjälp → Om**.
- **Ikoner:** Ikonfiler i **src/ui/assets/icons/** (SVG för actions); **resources.qrc** + pyside6-rcc; ikoner sätts på app, fönster, toolbar och menyactions (Open, Run, Export, Settings, About).
- **Windows .ico:** Flerstorleks-.ico för build; byggkonfigurationen använder den, utan större ändringar i bygglogik.

Allt enligt 13-DISCUSS.md; ändringar begränsade till **src/ui/** och tillhörande assets.

---

## Befintlig kod

- **src/ui/views/main_window.py** – setWindowTitle, menuBar, "Inställningar" med "AI-inställningar...". Ingen Hjälp/Om-meny.
- **src/config.py** – get_app_version() från pyproject.toml.
- **src/ui/theme/** – tema (tokens, app_style.qss, apply_theme).
- **run_gui.py**, **src/ui/app.py** – app-start.

---

## Planer (efter 13-DISCUSS)

- **13-01:** About-dialog med flikar (Om appen + Hjälp), Skapad av, Hjälp-meny.
- **13-02:** Ikonassets (assets/icons/), resources.qrc, pyside6-rcc, applicera ikoner i UI (app, fönster, toolbar, menyer).
- **13-03:** Windows .ico och build-icon-konfiguration.

---

## Beroenden

- Phase 6 (Manual Validation UI) – MainWindow, meny.
- Phase 12 (UI Polish) – tema; About och ikoner följer samma look.

---

*Context uppdaterad 2026-01-24 – /gsd:discuss-phase 13*
