---
status: complete
phase: 01-document-normalization
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md, 01-04-SUMMARY.md, 01-05-SUMMARY.md]
started: "2026-01-24T23:15:00Z"
updated: "2026-01-25T00:20:00Z"
---

## Current Test

[testing complete]

## Tests

### 1. CLI visar hjälp
expected: |
  `python -m src.cli.main --help` visar usage, --input, --output m.fl. Inga PDF-filer krävs.
result: pass

### 2. CLI kräver --input
expected: |
  Kör utan --input (t.ex. bara `python -m src.cli.main --output out`): tydligt felmeddelande att --input krävs (såvida inte --validate-confidence eller pattern-kommandon).
result: pass

### 3. CLI vid mapp utan PDF-filer
expected: |
  Kör med `--input tests/fixtures/pdfs --output <dir>` (mapp utan .pdf): tydligt meddelande att inga PDF-filer hittades, ingen krasch.
result: skipped
reason: Användaren körde med mapp innehållande PDF-filer; separat "inga PDF-filer"-test ej genomfört.

### 4. CLI processar PDF och skapar Excel
expected: |
  Kör med `--input <mapp med minst en PDF> --output <dir>`: pipeline körs, Excel-fil skapas i output (t.ex. invoices_YYYY-MM-DD_HH-MM-SS.xlsx), sammanfattning skrivs ("Done: N processed...").
result: pass

### 5. Excel har svenska kolumnnamn
expected: |
  Öppnad export-Excel: kolumnerna har svenska namn (t.ex. Fakturanummer, Företag, Fakturadatum, Beskrivning, Antal, Enhet, Á-pris, Summa, Status).
result: pass

### 6. Excel en rad per radpost
expected: |
  Varje fakturarad (line item) = en rad i Excel. Metadata (fakturanummer, företag, etc.) upprepas per rad.
result: pass

### 7. Batch-förlopp och sammanfattning
expected: |
  Under körning: counter "Processing N/M...", per faktura "[N/M] fil.pdf... → STATUS", till slut "Done: N processed. OK=... PARTIAL=... REVIEW=... failed=..." samt Excel-sökväg.
result: pass

## Summary

total: 7
passed: 6
issues: 0
pending: 0
skipped: 1

## Gaps

