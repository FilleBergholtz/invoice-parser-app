---
status: complete
phase: 06-manual-validation-ui
source: [06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md, 06-04-SUMMARY.md]
started: "2026-01-25T00:42:00Z"
updated: "2026-01-24T23:59:00Z"
---

## Current Test

[testing complete]

## Tests

### 1. GUI startar och visar huvudfönster
expected: |
  `python run_gui.py` startar GUI. Fönster med "EPG PDF Extraherare", Input PDF, Output, Kör. Ingen krasch.
result: pass

### 2. Valideringssektion visas efter process med REVIEW
expected: |
  Välj PDF, kör process. Om resultat har REVIEW: valideringssektion visas ("Validering: Välj korrekt totalsumma"), PDF-viewer, kandidatlista, Bekräfta val, Hoppa över.
result: pass

### 3. PDF visas i viewer vid validering
expected: |
  När valideringssektion visas: PDF laddas i viewer, första sidan synlig.
result: pass

### 4. Kandidatlista visar belopp och konfidens
expected: |
  När kandidater finns: lista med belopp (SEK-format) och konfidens. Ett klick = val. (Skippas om tom pga begränsad integration.)
result: pass

### 5. Zoom i PDF-viewer (Ctrl+scroll)
expected: |
  I valideringsvyn: Ctrl+scroll zoomar in/ut i PDF-viewern (ca 0,5x–4x). (Levererat i 06-04.)
result: pass

### 6. Tangentbordsval (piltangenter, Enter)
expected: |
  Fokus på kandidatlistan: piltangenter byter vald kandidat, Enter bekräftar. (Levererat i 06-04.)
result: pass

### 7. Hoppa över döljer validering
expected: |
  Klick "Hoppa över": valideringssektion döljs, ingen korrigering sparas.
result: pass

### 8. Bekräfta val sparar och visar feedback
expected: |
  Välj kandidat, klick "Bekräfta val": korrigering sparas, status "✓ Korrigering sparad" eller liknande. (Skippas om inga kandidater.)
result: pass

### 9. Korrigering i data/corrections.json
expected: |
  Efter Bekräfta val med giltigt val: ny post i data/corrections.json (invoice_id, corrected_total, etc.). (Skippas om Bekräfta inte kunde köras.)
result: pass

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
