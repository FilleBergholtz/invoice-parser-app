# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

**Current focus:** v2.1 milestone komplett, redo för nästa milestone.

## Current Position

Milestone: **v2.1 Parsing robustness / EDI** (komplett).
Phase: **23** — Confidence calibration robustness (komplett).
Plan: 23-01 genomförd (CAL-01 to CAL-06).
Status: v2.1 milestone komplett med alla phases 16-23 genomförda.
Last activity: 2026-01-28 — Implemented CAL-01 to CAL-06 calibration improvements.

Progress: █████████████████████ 79/79 (100%) — v1.0 (Phase 1–3) + v2.0 (Phase 5–15) + v2.1 (Phase 16-23) alla genomförda.

## Accumulated Context

### Decisions

Se PROJECT.md Key Decisions. v2.0-beslut: AI fallback endast vid confidence < 0,95; inlärning SQLite och leverantörsspecifika mönster; manuell validering med klickbar PDF och kandidatval; dual extraction och fallback-kedja pdfplumber → OCR → AI → vision. Nya beslut i Phase 17: AI-policybeslut baseras på EDI-lik signal (text-layer, ankare, tabellmönster) och sparas i extraction_detail.ai_policy; deterministisk fallback körs före AI. Phase 18: fakturanummer är primär boundary-signal; sidnumrering används endast som kontinuitetsstöd när fakturanummer saknas.

### Roadmap Evolution

- Phase 23 added: Confidence calibration robustness (equal-frequency binning, sample weights, supplier-global models, safe filenames, adaptive thresholds)
- Phase 23 completed: 2026-01-28 (CAL-01 to CAL-06 implemented)

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-01-28
Stopped at: Phase 23 komplett, v2.1 milestone fullständig
Next step: UAT update eller ny milestone (v2.2)
Resume file: None
