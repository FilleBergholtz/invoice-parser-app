---
phase: 20-tabellsegment-kolumnregler
plan: 01
subsystem: parsing
tags: [table, column-rules, parsing]

# Dependency graph
requires:
  - phase: 19-svensk-talnormalisering
    provides: Decimal-normalisering för belopp
provides:
  - Tabellblock-avgränsning för items-rader
  - Moms%-styrd nettobeloppsextraktion (sista belopp efter moms)
affects: [tabellsegment, parsing, line-items]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tabellblock filtreras mellan rubrikrad och slutrad"
    - "Nettobelopp kräver moms% och tas efter moms-kolumnen"

key-files:
  created: []
  modified:
    - src/pipeline/invoice_line_parser.py
    - tests/test_invoice_line_parser.py

key-decisions:
  - "Tabellblock avgörs av rubrikrad + 'Nettobelopp exkl. moms'"

patterns-established:
  - "Tabellrader parsas endast inom blocket"

# Metrics
duration: n/a
completed: 2026-01-26
---

# Phase 20 Plan 01: Tabellsegment & kolumnregler Summary

**Tabellblock avgränsas och nettobelopp tas efter moms%-kolumnen.**

## Accomplishments
- Filtrerar items‑rader till tabellblocket mellan rubrikrad och slutrad.
- Kräver moms% (25,00/25.00) och väljer sista belopp efter moms som nettobelopp.
- Lägger regressionstest för tabellblock och moms%-kolumnregel.

## Tests
- `python -m pytest tests/test_invoice_line_parser.py`

## Task Commits
- Pending manual commit (PowerShell).

## Files Created/Modified
- `src/pipeline/invoice_line_parser.py` - Tabellblock + moms%-kolumnregel.
- `tests/test_invoice_line_parser.py` - Testfall för block och moms-regel.

## Decisions Made
None.

## Deviations from Plan
None.

## Issues Encountered
None.

## Known Limitations

**CRITICAL:** Single VAT rate only (25%)
- Rader med 12% eller 6% moms identifieras inte som line items
- Måste addresseras i Phase 21/22
- Se: `20-LIMITATIONS.md` för fullständig dokumentation

**MEDIUM:** Swedish-only footer keywords
- Internationella fakturor kan extrahera footer-rader som line items

**MINOR:** Multi-page tables utan header-upprepning
- Phase 21 scope (multi-line items)

## Next Phase Readiness
Phase 20 klar; redo för Phase 21 (multi-line items).

**Handoff to Phase 21:**
- ✅ Tabellblock-avgränsning fungerar
- ✅ VAT%-anchored parsing implementerad
- ⚠️ Multipla momssatser måste addresseras (kritisk begränsning)
- 📋 Se `20-LIMITATIONS.md` för detaljer

---
*Phase: 20-tabellsegment-kolumnregler*
*Completed: 2026-01-26*
