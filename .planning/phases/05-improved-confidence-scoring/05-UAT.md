---
status: complete
phase: 05-improved-confidence-scoring
source: [05-01-SUMMARY.md, 05-02-SUMMARY.md, 05-03-SUMMARY.md]
started: "2026-01-25T00:25:00Z"
updated: "2026-01-25T00:38:00Z"
---

## Current Test

[testing complete]

## Tests

### 1. CLI --validate-confidence utan --input
expected: |
  `python -m src.cli.main --validate-confidence` körs utan --input. Tydligt meddelande om ground truth (används default eller "not found"). Ingen krasch.
result: pass

### 2. CLI --validate-confidence, ingen ground truth-fil
expected: |
  Samma som 1 när data/ground_truth.json och data/ground_truth.csv saknas: tydligt felmeddelande (t.ex. "Ground truth data file not found"), ingen krasch.
result: pass

### 3. Excel export innehåller konfidenskolumner
expected: |
  Efter pipeline-körning mot PDF: Excel har kolumner Totalsumma-konfidens, Fakturanummer-konfidens, Status. Kolumnerna har värden (tal eller N/A).
result: pass

### 4. --validate-confidence --ground-truth med giltig fil
expected: |
  Kör med `--validate-confidence --ground-truth <sökväg>` där filen är giltig JSON/CSV: valideringsrapport skrivs (bins, drift, ev. "recalibration suggested"). Ingen krasch.
result: pass

### 5. --validate-confidence --train med ground truth
expected: |
  Kör med `--validate-confidence --train --ground-truth <sökväg>`: modell tränas, validering körs, rapport skrivs. Kräver giltig ground truth-fil.
result: pass

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0

## Gaps

