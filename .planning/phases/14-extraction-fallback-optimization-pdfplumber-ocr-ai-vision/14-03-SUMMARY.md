# 14-03: Text quality module — Summary

**Done:** 2026-01-25

## Objective

Implement deterministic text quality scoring [0..1] per page for routing (pdfplumber vs OCR vs AI). Separate scores for pdf-text and OCR-text; used by orchestration with TEXT_QUALITY_THRESHOLD (e.g. 0.5). Per 14-CONTEXT §4 and 14-DISCUSS implementation task 3.

## Completed tasks

1. **`src/pipeline/text_quality.py`**
   - `score_text_quality(text: str, tokens: List[Token]) -> float` — for pdfplumber-derived text. Returns float in [0.0, 1.0].
   - `score_ocr_quality(tokens: List[Token]) -> float` — for OCR tokens; blends content-based score with median(token.confidence)/100 when confidence is present. Returns float in [0.0, 1.0].
   - Internal `_content_score(text, tokens)` factors: nonempty_ratio, weird_char_ratio (allowing normal punctuation `.,-/ :;`), alpha_num_ratio, token-length sanity (median 2–20 chars), optional keyword bonus (Total, Moms, Faktura, Bankgiro, etc.). Weighted blend with keyword bonus cap 0.2.

2. **Pipeline exports**
   - `src/pipeline/__init__.py` exports `score_text_quality` and `score_ocr_quality`. Import: `from src.pipeline import score_text_quality, score_ocr_quality` or `from src.pipeline.text_quality import ...`.

## Files changed

- `src/pipeline/text_quality.py` — new module (score_text_quality, score_ocr_quality, _content_score)
- `src/pipeline/__init__.py` — added imports and __all__ for text_quality

## Verification

- `score_text_quality(text, tokens)` and `score_ocr_quality(tokens)` exist and return float in [0.0, 1.0].
- Module is importable; docstrings document usage for orchestration (routing thresholds).
