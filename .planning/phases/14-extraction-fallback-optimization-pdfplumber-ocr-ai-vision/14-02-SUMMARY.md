# 14-02: pdfplumber tokenizer improvements — Summary

**Done:** 2026-01-25

## Objective

Improve pdfplumber tokenizer: use_text_flow=True, optional extra_attrs=["fontname","size"] with safe fallback, and better reading order via line clustering. Per 14-CONTEXT §3 and 14-DISCUSS implementation task 2.

## Completed tasks

1. **use_text_flow=True** (`src/pipeline/tokenizer.py`)
   - All extract_words calls use `use_text_flow=True` to improve reading order for multi-column and complex layouts.

2. **extra_attrs with safe fallback**
   - First attempt: `extract_words(..., use_text_flow=True, extra_attrs=["fontname","size"])`.
   - On exception or if that returns no words, fall back to `extract_words(..., use_text_flow=True)` without extra_attrs.
   - Font size/name still taken from `word.get('size')` and `word.get('fontname')` when present.

3. **Reading order via line clustering**
   - Added `_tokens_reading_order(tokens)` that groups tokens by similar y (line threshold = 0.5 * median(token.height), clamped to 2–15 pt).
   - Lines sorted by y; tokens within each line sorted by x. Replaces simple (y, x) sort to avoid mixing lines when vertical spacing is uneven.
   - `extract_tokens_from_page` uses `_tokens_reading_order(tokens)` before returning.

## Files changed

- `src/pipeline/tokenizer.py` — use_text_flow, extra_attrs + fallback, _tokens_reading_order, line-clustered sort

## Verification

- extract_words uses use_text_flow=True. extra_attrs tried first, fallback on exception or empty result.
- Token order follows reading order via line clustering.
- tests/test_tokenizer, test_segment_identification, test_row_grouping, test_invoice_line_parser, test_header_extractor: 25 passed, 4 skipped.
