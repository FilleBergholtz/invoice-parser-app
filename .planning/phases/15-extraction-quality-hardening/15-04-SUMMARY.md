# 15-04: OCR DPI retry R1 (D4) — Summary

**Done:** 2026-01-25

## Objective

After OCR at BASELINE_DPI, if ocr_mean_conf < OCR_MEAN_CONF_RETRY_THRESHOLD (55), re-render that page at RETRY_DPI and re-run OCR once. Max one retry per page. Artifacts/extraction_detail reflect which DPI was used.

## Completed tasks

1. **DPI retry in process_virtual_invoice** — In the OCR branch, after `render_page_to_image(page, dir, dpi=BASELINE_DPI)` and `extract_tokens_with_ocr(page)`, we compute `ocr_page_metrics(tokens)`. If `metrics.mean_conf < OCR_MEAN_CONF_RETRY_THRESHOLD`, we call `render_page_to_image(page, dir, dpi=RETRY_DPI)` and `extract_tokens_with_ocr(page)` again and set `ocr_dpi_used = RETRY_DPI`. Otherwise `ocr_dpi_used = BASELINE_DPI`. Per-page, max one retry.

2. **dpi_used in artifacts** — When `return_last_page_tokens` and `extraction_path == "ocr"`, the returned extra dict includes `dpi_used` (300 or 400). The compare path passes this into `extraction_detail["dpi_used"]` for OCR and choose_best results.

## Files changed

- `src/cli/main.py` — Imports BASELINE_DPI, RETRY_DPI, OCR_MEAN_CONF_RETRY_THRESHOLD from pdf_renderer; OCR loop in process_virtual_invoice implements R1 retry; return extra includes dpi_used; extraction_detail in compare path includes dpi_used.

## Verification

- DPI retry runs when mean_conf < 55; max 1 retry per page.
- extraction_detail contains dpi_used when OCR was used (compare path).
