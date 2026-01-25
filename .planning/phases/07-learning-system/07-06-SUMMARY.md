---
phase: 07-learning-system
plan: 06
subsystem: learning, ui
tags: [validation-ui, validation_queue, multi-pdf, gap-closure]
gap_closure: true

# Dependency graph
requires:
  - plan: 06-manual-validation-ui
    provides: _show_validation_ui, processing_result, validation payload
provides:
  - RunSummary.validation_queue; GUI visar flera REVIEW-fakturor i tur med "Nästa faktura"
affects: [07-UAT – gap "Validation UI supports multiple PDFs" closable]

# Tech tracking
tech-stack:
  added: [validation_queue]
  patterns: [queue från REVIEW-invoices, refresh view vs advance]

key-files:
  created: []
  modified: [src/run_summary.py, src/cli/main.py, src/ui/views/main_window.py]

key-decisions:
  - "validation_queue: List[Dict] med pdf_path, invoice_id, candidates, traceability, extraction_source; summary.validation = queue[0] för bakåtkompatibilitet"
  - "GUI: _validation_queue, _validation_queue_index, _current_validation_invoice_id; _refresh_validation_view() laddar aktuell blob; _advance_to_next_validation() eller _close_validation_ui()"
  - "Efter Skip/Bekräfta: _finish_current_validation_and_continue() → nästa eller stäng; sparad korrigering använder _current_validation_invoice_id"

# Metrics
duration: ~45 min
completed: "2026-01-24"
---

# Phase 07: Learning System - Plan 06 (Gap Closure) Summary

**Flera PDF:er i validerings-UI – 07-UAT gap closed**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-01-24
- **Tasks:** 1 (RunSummary + CLI + GUI)
- **Files modified:** 3

## Accomplishments

### RunSummary och CLI
- `RunSummary` har `validation_queue: Optional[List[Dict[str, Any]]] = None`.
- I CLI byggs `validation_queue`: för varje REVIEW i `invoice_results` läggs en blob in med `pdf_path`, `invoice_id` (= virtual_invoice_id), `candidates`, `traceability`, `extraction_source`.
- Vid icke-tom kö: `summary.validation_queue = validation_queue`, `summary.validation = validation_queue[0]` (bakåtkompatibilitet).

### GUI (main_window)
- Kö-state: `_validation_queue`, `_validation_queue_index`, `_current_validation_invoice_id`.
- Vid `_show_validation_ui`: init av kön från `processing_result["validation_queue"]`, index 0, sedan `_refresh_validation_view()` och `_update_next_button_visibility()`.
- `_refresh_validation_view()`: laddar aktuell `processing_result["validation"]` (PDF, kandidater, traceability) i viewer och candidate selector.
- `_update_next_button_visibility()`: visar "Nästa faktura" när `len(queue) > 1` och `index < len(queue)-1`.
- `_advance_to_next_validation()`: ökar index, sätter nästa som `processing_result["validation"]`, nollställer val/sparad-status, anropar `_refresh_validation_view()` och uppdaterar knapp; annars `_close_validation_ui()`.
- `_finish_current_validation_and_continue()`: efter Skip eller Bekräfta – anropar antingen `_advance_to_next_validation()` eller `_close_validation_ui()`.
- I `_load_candidates_from_result` sätts `self._current_validation_invoice_id = validation.get("invoice_id")`.
- I `_confirm_correction` används `invoice_id = self._current_validation_invoice_id or (Path(self.input_path).stem if self.input_path else "unknown")` vid `save_correction`; efter lyckad sparning anropas `_finish_current_validation_and_continue()`.
- `_skip_validation` anropar `_finish_current_validation_and_continue()`.

## Files Modified

- `src/run_summary.py` – fältet `validation_queue`.
- `src/cli/main.py` – byggande av `validation_queue` från REVIEW-invoices, sättning av `summary.validation`/`validation_queue`.
- `src/ui/views/main_window.py` – kö-init, `_refresh_validation_view`, `_update_next_button_visibility`, `_advance_to_next_validation`, `_close_validation_ui`, `_finish_current_validation_and_continue`, korrekt `invoice_id` vid sparning, knappen "Nästa faktura".

## Verification

- Run med flera REVIEW-fakturor: första visas; efter Skip eller Bekräfta visas nästa tills kön är tom.
- Korrigering sparas per `invoice_id` (virtual_invoice_id) så att flera fakturor inte skriver över varandra.

---
*Plan 07-06 (gap closure) completed: 2026-01-24*
