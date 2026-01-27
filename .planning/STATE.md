# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

**Current focus:** v2.1 milestone komplett, UAT skapad och redo för execution.

## Current Position

Milestone: **v2.1 Parsing robustness / EDI** (komplett, UAT pending).
Phase: **22** — Valideringsdriven om-extraktion (klar).
Plan: 22-01 genomförd (validering, mode B, debug artifacts).
Status: v2.1 milestone komplett - alla phases 16-22 genomförda, UAT skapad.
Last activity: 2026-01-26 — Created v2.1-UAT.md för milestone acceptance testing.

Progress: █████████████████████ 78/78 (100%) — v1.0 (Phase 1–3) + v2.0 (Phase 5–15) + v2.1 (Phase 16-22) alla genomförda.

## Accumulated Context

### Decisions

Se PROJECT.md Key Decisions. v2.0-beslut: AI fallback endast vid confidence < 0,95; inlärning SQLite och leverantörsspecifika mönster; manuell validering med klickbar PDF och kandidatval; dual extraction och fallback-kedja pdfplumber → OCR → AI → vision. Nya beslut i Phase 17: AI-policybeslut baseras på EDI-lik signal (text-layer, ankare, tabellmönster) och sparas i extraction_detail.ai_policy; deterministisk fallback körs före AI. Phase 18: fakturanummer är primär boundary-signal; sidnumrering används endast som kontinuitetsstöd när fakturanummer saknas.

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-01-26
Stopped at: v2.1 milestone komplett, UAT skapad (.planning/milestones/v2.1-UAT.md)
Next step: UAT execution eller milestone completion
Resume file: None
