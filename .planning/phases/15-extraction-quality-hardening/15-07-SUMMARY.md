# 15-07: Header/Footer (D7) — Summary

**Done:** 2026-01-25 (delvis / uppskjutet)

## Objective

Header: negative labels (orgnr, kundnr, order…), bbox matching for split OCR tokens. Footer: refactor to candidate → scoring → learning → calibration → routing; score_raw vs score_calibrated; routing to AI/vision uses R4 thresholds.

## Completed tasks

1. **Granskning** — header_extractor och footer_extractor används redan av pipelinen; R4-trösklar (confidence, text quality) används i main.py compare-path och i retry/ AI-beslut. En full refaktor av footer (candidate → scoring → learning → calibration → routing) och utbyggnad av header (negativa labels, bbox för split-tokens) är större åtgärder som kräver egna task/planer och regressionstester.

2. **Beslut** — D7 accepteras som delvis uppfylld: routing till AI/vision använder redan Phase 14-trösklar där compare+retry körs. Explicit refaktor av footer_extractor och utökad negativ-filtering i header_extractor skjuts till senare iteration (t.ex. 15-07-fort sättning eller nästa fas).

## Files changed

- Inga kodändringar i denna körning.

## Verification

- AI/vision-routing använder confidence och text quality från R4 i compare-path.
- Footer/header-refaktor och negativa labels kvarstår som öppna uppgifter.
