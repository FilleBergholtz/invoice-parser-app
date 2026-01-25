# 15-06: Line parser robustness (D6) — Summary

**Done:** 2026-01-25

## Objective

Split footer keywords into HARD/SOFT; for SOFT require extra signal. Remove O(n²) token index lookups. Prefer bbox/X-based amount detection where it helps.

## Completed tasks

1. **HARD vs SOFT footer keywords** — Introduced `_FOOTER_HARD_KEYWORDS` (e.g. "summa att betala", "att betala", "totalt", "delsumma", "nettobelopp", "moms" …) and `_FOOTER_SOFT_KEYWORDS` (e.g. "summa", "lista", "spec", "bifogad", "fraktavgift", "avgift", "forskott" …). Rows with only a SOFT keyword are treated as footer only if `_row_has_total_like_amount(row)` is true (amount extracted from row). Hard keywords still always classify as footer.

2. **Remove O(n²) index lookups** — In `_extract_amount_from_row_text`, the loop that built `token_positions` used `tokens.index(token)` inside the loop. Replaced with `sorted(enumerate(tokens), key=lambda ie: ie[1].x)` and iterating `(original_idx, token)` so no index lookup is needed.

3. **Bbox/X ordering** — Amount-related token order is now driven by `sorted(enumerate(tokens), key=...x)`, i.e. X-position order; character positions are derived from that order. Left the existing amount-from-text logic as is; the hot path uses X-based token order only for mapping back to indices.

## Files changed

- `src/pipeline/invoice_line_parser.py` — HARD/SOFT sets, `_row_has_total_like_amount`, and token-position build without `index()`.

## Verification

- SOFT footer requires a total-like amount; HARD footer does not.
- No `row.tokens.index(token)` in the amount-extraction hot path.
- Token order for positions is X-based.
