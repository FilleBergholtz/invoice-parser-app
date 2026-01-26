---
status: gaps_found
phase: 19
goal: "Alla belopp parsas konsekvent som Decimal med svensk notation."
requirements: [NUM-01, NUM-02, NUM-03, NUM-04]
---

# Verifiering — Phase 19: Svensk talnormalisering

## Status
gaps_found

## Must-haves
- NUM-01: Gaps found — normalizer används, men belopp materialiseras som `float` i pipeline (ej konsekvent `Decimal` utåt).
- NUM-02: Passed — mellanslag som tusentalsseparator tas bort i normalisering.
- NUM-03: Passed — punkt tas bort endast vid tusentalsformat (tre siffror efter).
- NUM-04: Passed — kommatecken konverteras till punkt före Decimal-parsning.

## Evidens
- Gemensam normaliseringsfunktion som returnerar `Decimal` finns: `src/pipeline/number_normalizer.py` (normalize_swedish_decimal).
- Normalisering tar bort mellanslag och tusentalspunkt samt byter `,`→`.`: `src/pipeline/number_normalizer.py`.
- Pipeline använder normalizer men castar till `float` för line-amounts/quantities: `src/pipeline/invoice_line_parser.py` (`_parse_numeric_value`, `_extract_amount_from_row_text`).
- Validering använder normalizer för strängvärden, men summerar som `Decimal` och returnerar `float`: `src/pipeline/validation.py`.
- Tester för svenska format och negativa belopp finns: `tests/test_number_normalizer.py`.
- Parser-test täcker svensk separator i line-amounts (via normalizer): `tests/test_invoice_line_parser.py`.
- Valideringstest med svensk-formaterad totalsumma: `tests/test_validation.py`.

## Gaps
- NUM-01: Utdata i pipeline är fortfarande `float` (line amounts, quantities, unit_price, diff), vilket bryter målet “alla belopp parsas konsekvent som Decimal”.
