# 11-02: Dual-run and comparison — Summary

**Done:** 2026-01-24

## Objective

When `--compare-extraction` is enabled, run both pdfplumber and OCR extraction per virtual invoice, compare results (validation_passed, total_confidence), and select the best. Same downstream pipeline consumes the chosen result (no dual export).

## Completed tasks

1. **Add --compare-extraction CLI flag** (`src/cli/main.py`)
   - In `main()`: `parser.add_argument("--compare-extraction", action="store_true", help="Run both pdfplumber and OCR, compare results, use best.")`.
   - Flag is passed as `compare_extraction=args.compare_extraction` into `process_batch(...)` and from there into `process_pdf(..., compare_extraction=compare_extraction)`.

2. **Dual-run per virtual invoice when compare mode on**
   - In `process_pdf`, when `compare_extraction` is True, for each boundary we call `process_virtual_invoice(..., "pdfplumber", ...)` and `process_virtual_invoice(..., "ocr", ...)` and keep both results for comparison.
   - When False, behaviour is unchanged: one call per virtual invoice using the routed `extraction_path`.

3. **Compare and select best result**
   - Helpers: `_validation_passed(r)` (total ≈ line_items_sum from `validation_result.diff`/tolerance), `_total_confidence(r)`, `_invoice_number_confidence(r)`.
   - `_choose_best_extraction_result(r_pdf, r_ocr) -> Tuple[VirtualInvoiceResult, str]`:
     1. If exactly one result has validation_passed → choose that one.
     2. Else choose higher `total_confidence`; tie-break with `invoice_number_confidence`.
     3. Default to pdfplumber when still tied or both fail.
   - The chosen result is the single result for that virtual invoice (export, review, run_summary unchanged).

4. **Log which source was used**
   - When `compare_extraction` and `verbose`, for each virtual invoice:  
     `print(f"  [{chosen.virtual_invoice_id}] using {source} (validation_passed={vp}, confidence={conf})")`.

## Files changed

- `src/cli/main.py` — `Tuple` import; `--compare-extraction`; `process_batch(..., compare_extraction=False)`; `process_pdf(..., compare_extraction=False)`; `_validation_passed`, `_total_confidence`, `_invoice_number_confidence`, `_choose_best_extraction_result`; dual-run loop and verbose log.

## Acceptance

- `python run_engine.py --input file.pdf --output out --compare-extraction` runs with compare mode enabled.
- When --compare-extraction is set, both pdfplumber and OCR extraction run for each virtual invoice.
- Best result is selected per virtual invoice (validation_passed first, then total_confidence, then invoice_number_confidence, then pdfplumber).
- User sees which source was used per invoice when --compare-extraction and --verbose.
