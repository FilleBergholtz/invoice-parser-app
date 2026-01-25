---
status: incomplete
phase: 07-learning-system
source: [07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md]
started: "2026-01-24T23:59:00Z"
updated: "2026-01-24T23:59:00Z"
---

## Current Test

[testing paused – gaps loggade för plan-phase --gaps]

## Tests

### 1. Learning-databas skapas vid användning
expected: |
  När learning används (t.ex. process med learning på eller CLI --consolidate-patterns): data/learning.db skapas under data/ om den inte fanns. Ingen krasch.
result: pass

### 2. CLI --consolidate-patterns körs och rapporterar
expected: |
  python -m src.cli.main --consolidate-patterns ger rapport typ "✓ Consolidated N patterns" eller "Patterns consolidated: N". Ingen krasch.
result: pass

### 3. CLI --cleanup-patterns körs och rapporterar
expected: |
  python -m src.cli.main --cleanup-patterns rapporterar borttagna eller att inget togs bort. Ev. --max-age-days 90 används som default. Ingen krasch.
result: pass

### 4. CLI --supplier begränsar consolidate/cleanup
expected: |
  python -m src.cli.main --consolidate-patterns --supplier "Leverantörsnamn" kör konsolidering endast för den leverantören. (Skippas om du inte vill testa med specifik leverantör.)
result: pass

### 5. Korrigeringar kan importeras till learning-databasen
expected: |
  Efter sparade korrigeringar i data/corrections.json: dessa kan föras över till learning.db (t.ex. via kod/API som anropar import_corrections_from_json). Efter import finns rader i corrections-tabellen. (Skippas om import inte är tillgänglig via CLI.)
result: pass
note: "Gap stängd av 07-04: python -m src.cli.main --import-corrections; användaren bekräftade att 4 patterns sparades."

### 6. Konfidensboost vid matchande mönster
expected: |
  När learning är aktiverat och det finns inlärda mönster för en leverantör: vid process av ny PDF från samma leverantör kan totalsumma-kandidater få högre konfidens. Observable: samma PDF ger högre confidence eller färre REVIEW när learning är på (jämfört med av). (Skippas om ingen testdata med mönster.)
result: issue
reported: "Den får inte högre resultat och sedan verkar vi bara spara 1 pdf's mönster och vi får bara svara på 1 pdf i viewer men de finns pdfer som har sämre confidence"
severity: major

## Summary

total: 6
passed: 5
issues: 1
pending: 0
skipped: 0
**UAT complete:** Nej – gaps kvar (konfidensboost, flera PDF:er i viewer).

## Gaps

- truth: "Corrections from data/corrections.json can be imported to learning.db; after import, rows exist in corrections table"
  status: resolved
  reason: "User reported: inget ligger i db"
  resolution: "07-04: CLI --import-corrections; user verified 4 patterns saved."
  severity: major
  test: 5
- truth: "When learning is on and patterns exist for a supplier, total-amount confidence increases for similar invoices"
  status: failed
  reason: "User reported: Den får inte högre resultat"
  severity: major
  test: 6
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
- truth: "Validation UI supports multiple PDFs with low confidence; user can validate more than one invoice"
  status: failed
  reason: "User reported: vi bara sparar 1 pdf's mönster och vi får bara svara på 1 pdf i viewer men de finns pdfer som har sämre confidence"
  severity: major
  test: 6
  root_cause: ""
  artifacts: []
  missing: []
  debug_session: ""
  note: "Överlappar Phase 6 (Manual Validation UI) – viewer/validering visar idag bara en REVIEW-PDF; fler med sämre confidence får inte valideras."
