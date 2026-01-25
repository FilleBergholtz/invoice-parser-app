# 15-08: Traceability (D8) — Summary

**Done:** 2026-01-25

## Objective

run_summary (per virtual-invoice extraction_detail) ska innehålla method_used, metrics (pdf_text_quality, ocr_text_quality, ocr_median_conf, ocr_mean_conf, low_conf_fraction), reason_flags, artifact paths, och vision_reason när method_used är ai_vision.

## Completed tasks

1. **extraction_detail utökad i compare-path** — I main.py, när vi sätter r_pdf.extraction_detail, r_ocr.extraction_detail och chosen.extraction_detail, lägger vi till: ocr_mean_conf, low_conf_fraction, dpi_used, reason_flags. reason_flags sätts från tröskelvillkor (t.ex. "pdf_text_quality<0.5", "ocr_median_conf<70", "text_quality<0.5") när vi inte accepterar pdf/ocr. vision_reason finns redan som nyckel (None när ej ai_vision).

2. **dpi_used** — Följer från 15-04: extra_ocr.get("dpi_used") skrivs in i extraction_detail när OCR eller choose_best används.

3. **RunSummary** — extraction_details listan fylls redan från virtual result.extraction_detail; inga ändringar i run_summary.py behövdes. Serialisering via asdict inkluderar de nya fälten.

## Files changed

- `src/cli/main.py` — extraction_detail för pdfplumber/ocr/choose_best innehåller ocr_mean_conf, low_conf_fraction, dpi_used, reason_flags (och befintliga method_used, pdf_text_quality, ocr_text_quality, ocr_median_conf, vision_reason).

## Verification

- extraction_detail innehåller method_used, metrics (inkl. ocr_mean_conf, low_conf_fraction), dpi_used, reason_flags.
- vision_reason kvarstår för ai_vision (sätts i AI/retry-sökväg när den används).
