# 15-05: Invoice boundary hardening (D5) — Summary

**Done:** 2026-01-25

## Objective

Harden invoice_boundary_detection so "faktura" + random alphanumeric is not sufficient alone; require additional signal (label match, strong candidate score, or date/amount). Reuse existing scoring.

## Completed tasks

1. **Require extra signal beyond faktura+alphanumeric** — The previous fallback returned True on any row containing "faktura" and an alphanumeric token. Now we only accept when we also have: (a) at least one invoice-number candidate with score ≥ 0.6 (strong candidate score), or (b) a date pattern or amount pattern on the same row. Track `best_candidate_score` from the existing candidate loop and use it in the fallback.

2. **Reuse existing scoring** — No new regex-only logic; we use `score_invoice_number_candidate` and existing patterns. Date/amount patterns used only as an extra gate in the fallback.

## Files changed

- `src/pipeline/invoice_boundary_detection.py` — Updated `_has_strong_invoice_header`: fallback requires `best_candidate_score >= 0.6` or date/amount on row.

## Verification

- "Faktura" + alphanumeric alone no longer yields a boundary.
- Multi-invoice PDFs still detect boundaries when invoice-number score ≥ 0.95 or when fallback has extra signal.
