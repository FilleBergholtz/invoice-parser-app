# 11-03: Use best result downstream — Summary

**Done:** 2026-01-24

## Objective

Ensure export, review, and run_summary use the chosen extraction result (pdfplumber or OCR) only. No mixed sources per invoice. Optionally add extraction_source metadata when --compare-extraction was used.

## Completed tasks

1. **Verify export uses chosen result**
   - Data flow confirmed: `process_pdf` returns a list where each element is already the chosen result when compare_extraction is on. `process_batch` uses that single `virtual_result` for Excel (via `invoice_results` → `excel_invoice_results` → `export_to_excel`). No mixed use.
   - Comment added in `process_batch`: "when compare_extraction, each is already the chosen pdfplumber/ocr result".

2. **Verify review reports and validation use chosen result**
   - Review reports, review package, and `summary.validation` all consume the same `virtual_result` (and later `invoice_results` built from it). Confirmed: `create_review_report`, `export_to_excel` (per REVIEW invoice), and `create_review_package` use `virtual_result.invoice_header`, `virtual_result.validation_result`, `virtual_result.invoice_lines`. Validation UI uses `summary.validation`, which is built from `invoice_results`; that data comes from the chosen result.

3. **Optional metadata for compare runs**
   - **VirtualInvoiceResult:** `extraction_source: Optional[str] = None` ("pdfplumber" | "ocr" when set). Set in `process_pdf` on the chosen result when compare_extraction is on.
   - **RunSummary:** `compare_extraction_used: bool = False`. Set in `process_batch` from `compare_extraction`.
   - **quality_scores:** Each entry includes `"extraction_source": getattr(virtual_result, "extraction_source", None)`.
   - **invoice_results:** Each entry includes `"extraction_source"` for use in Excel and summary.validation.
   - **Excel:** `invoice_metadata` may include `extraction_source`; Excel export writes it as column "Extraktionskälla" when present (`src/export/excel_export.py`).
   - **summary.validation:** Includes `"extraction_source": ir.get("extraction_source")` for the single-PDF REVIEW case so the validation UI can show which source was used.

## Files changed

- `src/models/virtual_invoice_result.py` — added `extraction_source: Optional[str] = None`
- `src/cli/main.py` — set `chosen.extraction_source = source` in process_pdf; `summary.compare_extraction_used`, extraction_source in quality_scores and invoice_results; extraction_source in invoice_metadata for Excel and in summary.validation; comment on chosen result in loop
- `src/run_summary.py` — added `compare_extraction_used: bool = False`
- `src/export/excel_export.py` — read `extraction_source` from invoice_metadata, add column "Extraktionskälla" in batch mode

## Acceptance

- Export, review, and run_summary use the chosen extraction only (verified; no code path mixes sources).
- When compare mode was used, run_summary has `compare_extraction_used: true` and per-invoice `extraction_source` in quality_scores and in summary.validation; Excel has "Extraktionskälla" when applicable.
