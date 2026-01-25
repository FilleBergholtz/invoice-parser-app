# 15-02: pdfplumber tokenizer (D2) — Summary

**Done:** 2026-01-25

## Objective

Complete D2 per 15-DISCUSS: use_text_flow=True, extra_attrs with safe fallback, reading order via line clustering. Remove unused chars extraction if not needed.

## Completed tasks

1. **use_text_flow and extra_attrs** — Already in place: `extract_words(..., use_text_flow=True)`, `extra_attrs=["fontname","size"]` with try/except; on exception or empty result, retry without extra_attrs. No unused chars extraction present. No code change.

2. **Reading order** — `_tokens_reading_order` clusters by similar y (line threshold from median height), sorts lines by y and tokens within line by x. Used after extraction (line 129). No code change.

## Files changed

- None (tokenizer already compliant with 15-DISCUSS D2 from Phase 14).

## Verification

- use_text_flow=True used; extra_attrs with safe fallback.
- Token order follows reading order via line clustering.
