# 12-03: Engine runner UX — Summary

**Done:** 2026-01-24

## Objective

Standardise engine run states and signals, and improve UX: disable/enable controls during run, show progress and optional expandable log, and show a user-friendly error dialog with "Visa detaljer". See 12-DISCUSS.md §3, 12-03-PLAN.md.

## Completed tasks

1. **EngineRunner: states and signals**
   - **States:** `Idle`, `Running`, `Success`, `Warning`, `Error` (konstanter i engine_runner).
   - **stateChanged(str)** — emits when state changes (Running at start; Success/Warning/Error when done).
   - **progressChanged(str)** — step/short message (e.g. "Startar motor…"); **logLine(str)** — each stdout line.
   - **progress(str)** behålls för bakåtkompatibilitet (samma som logLine).
   - **finished(bool, object)** — `(success, paths)`. `paths` = `{"output_dir", "excel_path"}` or None.
   - I `run()`: `stateChanged("Running")` i start; vid avslut `stateChanged("Success"|"Warning"|"Error")`, därefter `finished(success, paths)`. Vid undantag: `stateChanged("Error")`, `error(msg)`, `finished(False, None)`.

2. **MainWindow: disable/enable and progress**
   - **Under körning:** Run-, Öppna- och Export-aktioner inaktiveras (`run_action`, `open_action`, `export_action.setEnabled(False)`).
   - **Efter körning:** Alla tre åter aktiveras i `processing_finished(success, paths)`.
   - Progress: `QProgressBar` indeterminat under körning; sätts till 100 och döljs inte när klar.
   - Anslutning till `stateChanged` → `_on_engine_state_changed` uppdaterar statusfältet.
   - `processing_finished(success, paths)` ersätter tidigare `(exit_code)`; tråd quit/wait, återaktivering av knappar, vid fel anropas `_show_run_error_dialog()`.

3. **Expandable log**
   - Knapp **"Visa logg"** / **"Dölj logg"** (checkable) ovanför loggområdet; loggen är *collapsed* som standard (`log_area.setVisible(False)`).
   - `_toggle_log_visibility()` växlar synlighet och knapptext.
   - Loggrader skickas via `logLine` (och `progress`) till `self.log()` som tidigare.

4. **Error dialog with "Visa detaljer"**
   - Vid `processing_finished(success=False)` anropas `_show_run_error_dialog()`.
   - **QMessageBox** med kort användartext: "Körningen misslyckades. Kontrollera att motorn är installerad och att PDF-filen är giltig."
   - **setDetailedText(details)** sätter den expanderbara detaljtexten; Qt visar "Visa detaljer" automatiskt.
   - Detaljer = alla meddelanden som samlats under körningen i `_run_error_details` (fylld av `_on_engine_error`). Inga rå tracebacks i huvudmeddelandet.

## Verify

- `python -c "from src.ui.services.engine_runner import EngineRunner; r=EngineRunner('',''); assert hasattr(r,'stateChanged'); assert hasattr(r,'logLine'); print('signals ok')"` → ok
- `MainWindow` startar med `log_toggle_btn`, `_show_run_error_dialog`, `_on_engine_state_changed` — ok
- Manuellt: starta körning → Run/Öppna/Export inaktiverade; vid fel → dialog med kort text + "Visa detaljer".

## Files changed

- **src/ui/services/engine_runner.py** — `stateChanged`, `progressChanged`, `logLine`; `finished(bool, object)`; tillståndslogik och paths i `run()`; konstanter `STATE_*`.
- **src/ui/views/main_window.py** — `open_action`/`export_action` sparade; disable under run, enable i `processing_finished`; `_on_engine_state_changed`, `_toggle_log_visibility`, `_show_run_error_dialog`; `_run_error_details`; expandable log med "Visa logg"-knapp; anslutning till `runner.logLine`, `runner.stateChanged`, `runner.finished(success, paths)`; import av `QMessageBox`.

## Success criteria (12-03-PLAN)

- EngineRunner emits stateChanged(state), progressChanged(step/msg), logLine(str), finished(success, paths) — **ja**
- While Running: Run/Open (and Export) disabled; progress and optional log visible — **ja**
- On Error: user-facing dialog with short message and expandable "Visa detaljer" — **ja**
- All changes in `src/ui/` — **ja**
