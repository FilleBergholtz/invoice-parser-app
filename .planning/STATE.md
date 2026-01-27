# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

**Current focus:** v2.1 Phase 22 planerad, redo för implementation.

## Current Position

Milestone: **v2.1 Parsing robustness / EDI** (pågående).
Phase: **22** — Valideringsdriven om-extraktion (klar).
Plan: 22-01 genomförd (validering, mode B, debug artifacts).
Status: Phase 22 komplett - alla krav uppfyllda och verifierade.
Last activity: 2026-01-26 — Completed 22-01 implementation, verification, och SUMMARY.md.

Progress: █████████████████████ 71/71 (100%) — v1.0 (Phase 1–3) + v2.0 (Phase 5–15) + v2.1 Phase 16-21 genomförda.

## Accumulated Context

### Decisions

Se PROJECT.md Key Decisions. v2.0-beslut: AI fallback endast vid confidence < 0,95; inlärning SQLite och leverantörsspecifika mönster; manuell validering med klickbar PDF och kandidatval; dual extraction och fallback-kedja pdfplumber → OCR → AI → vision. Nya beslut i Phase 17: AI-policybeslut baseras på EDI-lik signal (text-layer, ankare, tabellmönster) och sparas i extraction_detail.ai_policy; deterministisk fallback körs före AI. Phase 18: fakturanummer är primär boundary-signal; sidnumrering används endast som kontinuitetsstöd när fakturanummer saknas.

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-01-26 23:45 UTC
Stopped at: Completed 21-01-PLAN.md + implementation + tests
Resume file: None
