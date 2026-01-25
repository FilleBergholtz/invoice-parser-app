# Codebase Map: Concerns

**Project:** EPG PDF Extraherare  
**Last updated:** 2026-01-25  
**Source:** map-codebase

## Technical Debt and Risks

### 1. CLI size and coupling

- **Where:** `src/cli/main.py` is very large (~1800+ lines).
- **Risk:** Harder to maintain, test, and refactor; routing, compare logic, AI, Excel, and run_summary all live in one module.
- **Mitigation:** Extract helpers (e.g. “build validation_queue”, “run compare for one invoice”) or move orchestration into a dedicated runner module; keep main.py as a thin CLI harness.

### 2. GUI dependency on run_summary shape

- **Where:** `main_window.py` assumes `processing_result` has `validation_queue`, `validation`, `excel_path`, and that each validation blob has `invoice_id`, `invoice_number`, `supplier_name`, `candidates`, `traceability`, `extraction_source`.
- **Risk:** Changes to run_summary or validation_queue format can break the GUI silently or with runtime errors.
- **Mitigation:** Document the contract (e.g. in INTEGRATIONS or a small “GUI contract” doc); consider a thin parsing layer that validates shape and maps to UI model.

### 3. Tesseract as external dependency

- **Where:** `pipeline/ocr_abstraction.py` calls Tesseract via pytesseract.
- **Risk:** Fails if Tesseract is not installed or not on PATH; behaviour and error codes (e.g. exit 4) are platform-dependent.
- **Mitigation:** `check_deps.py` and docs describe the requirement; keep error messages and logging explicit (e.g. “Tesseract not found” / “OCR exit code 4”) so support is easier.

### 4. Learning DB and corrections.json duplication

- **Where:** Corrections are stored in both `data/corrections.json` and `data/learning.db` (e.g. from GUI “Bekräfta”).
- **Risk:** Divergence if one path fails or if logic is updated in only one place; two sources of truth.
- **Mitigation:** Treat one as primary (e.g. DB) and the other as export/backup, or document clearly which is authoritative and when each is written/read.

### 5. Excel column and format drift

- **Where:** `export/excel_export.py` defines columns (e.g. Fakturatotal, Totalsumma-konfidens, Extraktionskälla); `apply_corrections_to_excel` assumes certain column names and types.
- **Risk:** Downstream tools or manual workflows break when columns change; old Excel files may lack new columns (e.g. Fakturatotal).
- **Mitigation:** Document the “current” Excel schema (e.g. in CONVENTIONS or export doc); `apply_corrections_to_excel` already adds missing columns when possible and uses name-based lookups to reduce index fragility.

### 6. AI key and config exposure

- **Where:** AI key and endpoint come from `configs/ai_config.json` and env (e.g. AI_KEY, AI_ENDPOINT).
- **Risk:** Accidental commit of secrets if config is ever tracked; key in memory when AI is used.
- **Mitigation:** Keep ai_config.json out of version control or use placeholders; prefer env for keys in production; avoid logging request/response bodies that contain sensitive data.

## Product / Domain

### 7. 100% accuracy promise

- **Principle:** All output marked OK must be correct on invoice number and total; uncertain cases go to REVIEW.
- **Risk:** Edge cases (layout, OCR quality, multi-invoice PDFs) can still produce wrong totals or invoice ids that are marked OK.
- **Mitigation:** Conservative confidence thresholds, calibration, and manual validation for REVIEW; periodic checks on real PDFs and ground truth (e.g. `data/ground_truth.json`).

### 8. Compare vs default path

- **Where:** Compare mode (pdfplumber vs OCR, choose best) is optional and may not be the default in all entry points (e.g. GUI engine call).
- **Risk:** Users may see “pdfplumber” in Excel or assume compare is always on, while the run might have used a single path.
- **Mitigation:** `extraction_source` / `extraction_detail.method_used` now reflect the actual method; docs and UI can state when compare is enabled and how output dir/Excel are produced.

## Operational

### 9. Output directory and “frozen” behaviour

- **Where:** `get_default_output_dir()` uses `sys.frozen` to choose “out” (dev) vs Documents/… (frozen).
- **Risk:** Any other “frozen” build or environment that sets `sys.frozen` gets the “production” paths; tests or secondary tools might assume “out” and fail.
- **Mitigation:** Document behaviour in config/conventions; tests that rely on output dir should set it explicitly or mock config.

### 10. No automated E2E tests

- **Where:** No test in `tests/` runs a full pipeline on a real PDF and asserts on Excel/run_summary.
- **Risk:** Refactors in CLI or pipeline can break end-to-end behaviour without failing tests.
- **Mitigation:** Add a small E2E test (e.g. one fixture PDF, run engine, assert status and presence of Excel/run_summary) and run it in CI if available.

## Summary Table

| Id | Concern | Area | Severity |
|----|---------|------|----------|
| 1 | Large, coupled CLI | Maintainability | Medium |
| 2 | GUI depends on run_summary shape | Integration | Medium |
| 3 | Tesseract external dependency | Environment | Low–Medium |
| 4 | Dual storage of corrections | Data consistency | Medium |
| 5 | Excel schema/format drift | Compatibility | Low–Medium |
| 6 | AI config/key exposure | Security | Medium |
| 7 | 100% accuracy in practice | Domain | Ongoing |
| 8 | Compare vs default path clarity | Product | Low |
| 9 | Output dir in frozen vs dev | Config | Low |
| 10 | No E2E tests | Quality | Medium |
