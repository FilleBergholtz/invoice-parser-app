# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2025-01-27)

**Core value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

**Current focus:** Phase 1: Document Normalization

## Current Position

Phase: 1 of 3 (Document Normalization)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2025-01-27 — Roadmap created

Progress: ░░░░░░░░░░ 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: -
- Trend: -

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Initialization]: Hard gates on invoice number + total — OK status only when both are certain (≥0.95 confidence), otherwise REVIEW
- [Initialization]: Layout-driven line item extraction (tokens→rows→segments), not table-extractor-driven
- [Initialization]: OCR abstraction layer allows switching engines without pipeline changes

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

None yet.

## Session Continuity

Last session: 2025-01-27
Stopped at: Roadmap created, ready to begin planning Phase 1
Resume file: None
