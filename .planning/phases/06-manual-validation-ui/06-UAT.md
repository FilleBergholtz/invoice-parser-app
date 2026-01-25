---
status: incomplete
phase: 06-manual-validation-ui
source: [06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md]
started: "2026-01-25T00:42:00Z"
updated: "2026-01-25T00:58:00Z"
---

## UAT-status

**Vi är inte klara med Phase 6 UAT.** Det finns öppna gaps (zoom, tangentbordsval, kandidatlista). Gap-åtgärder har planerats (06-04-PLAN) och delvis verkställts, men full verifiering återstår. UAT ska köras igen efter att gapen är stängda och ev. ytterligare fixar är på plats.

## Current Test

[testing paused – återuppta efter gap-åtgärder]

## Tests

### 1. GUI startar och visar huvudfönster
expected: |
  `python run_gui.py` startar GUI. Fönster med "EPG PDF Extraherare", Input PDF, Output, Kör. Ingen krasch.
result: pass

### 2. Valideringssektion visas efter process med REVIEW
expected: |
  Välj PDF, kör process. Om resultat har REVIEW: valideringssektion visas ("Validering: Välj korrekt totalsumma"), PDF-viewer, kandidatlista, Bekräfta val, Hoppa över.
result: issue
reported: "Det är lite svårt att se, så hade varit bra om man kunde zooma och sedan kan jag inte välja nåt med piltangenterna eller nåt annat ändå"
severity: major

### 3. PDF visas i viewer vid validering
expected: |
  När valideringssektion visas: PDF laddas i viewer, första sidan synlig.
result: pass

### 4. Kandidatlista visar belopp och konfidens
expected: |
  När kandidater finns: lista med belopp (SEK-format) och konfidens. Ett klick = val. (Skippas om tom pga begränsad integration.)
result: issue
reported: "nej"
severity: major

### 5. Hoppa över döljer validering
expected: |
  Klick "Hoppa över": valideringssektion döljs, ingen korrigering sparas.
result: pass

### 6. Bekräfta val sparar och visar feedback
expected: |
  Välj kandidat, klick "Bekräfta val": korrigering sparas, status "✓ Korrigering sparad" eller liknande. (Skippas om inga kandidater.)
result: skipped
reason: Inga kandidater – kan inte välja eller spara.

### 7. Korrigering i data/corrections.json
expected: |
  Efter Bekräfta val med giltigt val: ny post i data/corrections.json (invoice_id, corrected_total, etc.). (Skippas om Bekräfta inte kunde köras.)
result: skipped
reason: Inga kandidater – Bekräfta kunde inte köras.

## Summary

total: 7
passed: 3
issues: 2
pending: 0
skipped: 2
**UAT complete:** Nej – återstår att stänga gaps och köra om testerna.

## Gaps

- truth: "PDF viewer supports zoom for better visibility"
  status: failed
  reason: "User reported: Det är lite svårt att se, så hade varit bra om man kunde zooma"
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "User can select candidate with arrow keys and Enter in validation UI"
  status: failed
  reason: "User reported: kan inte välja nåt med piltangenterna eller nåt annat"
  severity: major
  test: 2
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Candidate list shows amounts (SEK) and confidence; one click = select"
  status: failed
  reason: "User reported: nej"
  severity: major
  test: 4
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""

