# Phase 12: UI Polish (PySide6) – Context

**Tillagd:** 2026-01-25  
**Status:** Planned

**Implementation spec:** Se **12-DISCUSS.md** för CONTEXT (desktop, subprocess+files, no HTTP), FILES, HARD CONSTRAINTS, DELIVERABLES (1–5), NON-GOALS och DONE/ACCEPTANCE.

---

## Mål

Förbättra desktop-GUI (run_gui.py, PySide6) med enhetlig **tema**, tydligare **layout**, och tydlig visning av **engine-tillstånd** så att användaren alltid vet vad som händer och får en konsekvent, professionell upplevelse. Arkitektur oförändrad: subprocess + filer, inga tjänster/HTTP.

---

## Scope

### 1. Theme

- Konsistent utseende: färger, teckensnitt, kontraster.
- Styling styrd via QSS (Qt Style Sheets) och/eller QPalette.
- Önskvärt: stöd för mörkt/ljust tema eller följ system (QStyle / palette).
- Ingen funktionell förändring av logik – endast visuell polish.

### 2. Layout

- Tydligare uppdelning av paneler: input/output, PDF-viewer, valideringssektion.
- Resizable paneler (QSplitter eller QLayout) där det ger nytta.
- Möjligtvis sparad layout (splitter-storlekar, fönsterstorlek) mellan sessioner.
- Mindre “läckage” av placeholders eller trånga etiketter.

### 3. Engine states

- UI visar tydligt pipeline-tillstånd, t.ex.:
  - **Redo** – väntar på val av PDF och klick på Kör
  - **Kör …** – pipeline pågår (med ev. progress/spinner)
  - **Klar** – körning färdig, resultat tillgängliga
  - **Fel** – något gick fel, med kort feedback
- Knappar och relevanta fält **disable/enable** per tillstånd så att:
  - användaren inte startar dubbelkörningar under “Kör …”,
  - feedback (statusrad, ikon eller text) alltid matchar aktuellt tillstånd.

---

## Befintlig kod

- **run_gui.py** – app-start, PySide6.
- **src/ui/app.py** – QApplication-setup.
- **src/ui/views/main_window.py** – huvudfönster, input/output, validering, PDF-viewer.
- **src/ui/views/pdf_viewer.py** – PDF-visning.
- **src/ui/views/candidate_selector.py** – kandidatlista för validering.
- **src/ui/services/engine_runner.py** – körning av pipeline (batch/process), ev. signaller för tillstånd.

Nuläge: GUI finns och fungerar (Phase 6); denna fas fokuserar på polish, inte ny funktion.

---

## Success criteria (krav som ska vara sanna)

1. **Theme:** Ett genomgående tema (t.ex. en QSS-fil eller palette) appliceras; fönstret ser enhetligt och genomtänkt ut.
2. **Layout:** Paneler är logiskt indelade och kan anpassas (splitters/布局) där det passar; ingen kritisk text klipps bort eller döljs i standardförstoring.
3. **Engine states:** Minst tre tillstånd (t.ex. Redo / Kör / Klar eller Fel) är definierade och synliga för användaren; “Kör”-knappen (eller motsv.) är inaktiverad under körning; statusrad eller tydlig plats visar aktuellt tillstånd.

---

## Planer (TBD)

Enligt 12-DISCUSS.md:

- **12-01:** Global theme – `src/ui/theme/` (tokens, app_style.qss, apply_theme), applicera i app.py.
- **12-02:** MainWindow layout – toolbar (Open/Run/Export/Settings), QSplitter, status bar, empty state, Ctrl+O/Ctrl+R/Ctrl+E.
- **12-03:** Engine runner UX – states/signals, progress, expandable log, error-dialog med “Show details”.
- **12-04:** PDF viewer polish – zoom/fit/prev/next, sidindikator, tema.
- **12-05:** AI settings dialog – grupperade inställningar, hjälptexter, “Test connection”-stub, tema.

Planerna kan skrivas ut i egna PLAN-filer när fasen prioriteras.

---

## Beroenden

- Phase 6 (Manual Validation UI) – GUI och engine_runner finns.
- Phase 11 – inte strikt nödvändig för theme/layout/states, men Phase 12 bygger på nuvarande run_gui + main_window.

---

*Context skapad: 2026-01-25 – /gsd:add-phase UI Polish (PySide6)*
