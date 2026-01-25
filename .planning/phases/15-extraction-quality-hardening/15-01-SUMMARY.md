# 15-01: Token confidence plumbing (D1) — Summary

**Done:** 2026-01-25

## Objective

Ensure D1 per 15-DISCUSS: Token.confidence, ocr_abstraction (TSV→Token, conf<0 excluded), OCR metrics (median/mean/low_conf_fraction), and confidence_scoring uses actual token confidence (no placeholder 1.0).

## Completed tasks

1. **Token and ocr_abstraction** — Already compliant from Phase 14: Token has `confidence: Optional[float]` (0–100); ocr_abstraction stores TSV word conf, excludes conf < 0, provides `ocr_page_metrics()` and `OCRPageMetrics` (mean_conf, median_conf, low_conf_fraction). No code change.

2. **confidence_scoring.py** — Replaced placeholder in `_average_token_confidence`: when tokens have `confidence` set (OCR path), compute mean and normalize 0–100 → 0..1; when none have confidence (pdfplumber), return 1.0. Removed TODO and fixed "return 1.0" for OCR tokens.

## Files changed

- `src/pipeline/confidence_scoring.py` — `_average_token_confidence` now uses `Token.confidence` when available.

## Verification

- Token.confidence is set from OCR TSV; conf < 0 excluded in ocr_abstraction.
- OCR metrics (mean/median/low_conf_fraction) available via ocr_page_metrics.
- confidence_scoring uses real confidence for OCR tokens; no placeholder 1.0 when data exists.
