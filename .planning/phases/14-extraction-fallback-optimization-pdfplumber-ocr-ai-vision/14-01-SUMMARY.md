# 14-01: Token model + OCR confidence — Summary

**Done:** 2026-01-25

## Objective

Add optional confidence to Token and persist OCR word confidence from Tesseract TSV. Exclude conf < 0 (layout rows) from tokens; compute per-page OCR metrics (mean_conf, median_conf, low_conf_fraction) for routing. Document mean vs median per 14-RESEARCH Recommendation B.

## Completed tasks

1. **Add Optional[float] confidence to Token** (`src/models/token.py`)
   - Added `confidence: Optional[float] = None` (0–100 scale for OCR; None for pdfplumber).
   - Documented in docstring. All existing Token(...) calls remain valid (default None).

2. **Persist OCR conf into Token and exclude conf < 0** (`src/pipeline/ocr_abstraction.py`)
   - In TesseractOCREngine.extract_tokens: after parsing `conf` from TSV, skip rows where `conf < 0`.
   - Create Token with `confidence=confidence` (0–100). Comment added: "Mean is used for DPI retry sensitivity, median for routing robustness."

3. **Add OCR confidence aggregation** (`src/pipeline/ocr_abstraction.py`)
   - Introduced `OCRPageMetrics` dataclass: mean_conf, median_conf, low_conf_fraction.
   - `ocr_page_metrics(tokens: List[Token]) -> OCRPageMetrics` includes only tokens with confidence is not None and >= 0; low_conf_fraction = fraction with confidence < 50.
   - Constants: OCR_EXCLUDE_CONF_BELOW=0, OCR_MEDIAN_CONF_ROUTING_THRESHOLD=70, OCR_LOW_CONF_FRACTION_THRESHOLD=0.25, OCR_LOW_CONF_WORD_THRESHOLD=50.

## Files changed

- `src/models/token.py` — confidence field
- `src/pipeline/ocr_abstraction.py` — skip conf < 0, pass confidence to Token, OCRPageMetrics + ocr_page_metrics(), R2 constants

## Verification

- Token has confidence; OCR path sets it for word rows (conf >= 0). Rows with conf < 0 produce no token.
- ocr_page_metrics(tokens) returns mean_conf, median_conf, low_conf_fraction; tested with sample tokens.
- Relevant tests (test_segment_identification, test_row_grouping, test_tokenizer) pass.
