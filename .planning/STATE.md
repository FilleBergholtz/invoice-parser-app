# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

**Current focus:** v2.1 Phase 21 planerad efter verifierad Phase 20.

## Current Position

Milestone: **v2.1 Parsing robustness / EDI** (pågående).
Phase: **20** — Tabellsegment & kolumnregler (klar).
Plan: 20-01 genomförd (tabellblock + moms%-kolumnregel).
Status: Phase 20 klar, redo för nästa fas (Phase 21).
Last activity: 2026-01-26 — Completed 20-01-PLAN.md.

Progress: ████████████████████░ 70/71 (99%) — v1.0 (Phase 1–3) + v2.0 (Phase 5–15) genomförda och arkiverade; Phase 20 klar.

## Accumulated Context

### Decisions

Se PROJECT.md Key Decisions. v2.0-beslut: AI fallback endast vid confidence < 0,95; inlärning SQLite och leverantörsspecifika mönster; manuell validering med klickbar PDF och kandidatval; dual extraction och fallback-kedja pdfplumber → OCR → AI → vision. Nya beslut i Phase 17: AI-policybeslut baseras på EDI-lik signal (text-layer, ankare, tabellmönster) och sparas i extraction_detail.ai_policy; deterministisk fallback körs före AI. Phase 18: fakturanummer är primär boundary-signal; sidnumrering används endast som kontinuitetsstöd när fakturanummer saknas.

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-01-26 21:25 UTC
Stopped at: Completed 20-01-PLAN.md
Resume file: None
