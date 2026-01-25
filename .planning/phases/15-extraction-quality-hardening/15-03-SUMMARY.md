# 15-03: Text quality + R4 routing (D3) — Summary

**Done:** 2026-01-25

## Objective

Ensure text_quality.py provides score_text_quality and score_ocr_quality [0..1], and that per-page routing uses TEXT_QUALITY_THRESHOLD and R4 rules (AI text-only when quality >= 0.5; vision when both pdf and ocr quality < threshold).

## Completed tasks

1. **Text quality module** — Already present from Phase 14: `score_text_quality(text, tokens)` and `score_ocr_quality(tokens)` in `src/pipeline/text_quality.py`, both returning [0..1]. No code change.

2. **R4 routing integration** — In `main.py` compare path, TEXT_QUALITY_THRESHOLD = 0.5 and CRITICAL_FIELDS_CONF_THRESHOLD = 0.95 are used. accept_pdf requires `pdf_text_quality >= TEXT_QUALITY_THRESHOLD`; accept_ocr requires `ocr_text_quality >= TEXT_QUALITY_THRESHOLD` and `ocr_median >= OCR_MEDIAN_CONF_ROUTING_THRESHOLD`. Best-source choice uses these signals. AI text vs vision routing is handled inside extract_with_retry / AI client when confidence < 0.95; text-quality checks in compare path gate pdf vs OCR acceptance. No change needed for D3.

## Files changed

- None (existing implementation already meets 15-DISCUSS D3).

## Verification

- score_text_quality and score_ocr_quality exist and return [0..1].
- Compare-path routing uses TEXT_QUALITY_THRESHOLD and R4-style rules for pdf/OCR acceptance.
