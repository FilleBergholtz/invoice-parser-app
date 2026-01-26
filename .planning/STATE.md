# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

**Current focus:** v2.1 Phase 17 planerad efter verifierad Phase 16.

## Current Position

Milestone: **v2.1 Parsing robustness / EDI** (pågående).
Phase: **17** — AI-policy fallback only (klar).
Plan: 17-02 genomförd (compare-path AI-policy gating).
Status: Phase 17 klar, redo för nästa fas (Phase 18).
Last activity: 2026-01-26 — Completed 17-02-PLAN.md.

Progress: ███████████████████░ 66/67 (98%) — v1.0 (Phase 1–3) + v2.0 (Phase 5–15) genomförda och arkiverade; Phase 17 klar.

## Accumulated Context

### Decisions

Se PROJECT.md Key Decisions. v2.0-beslut: AI fallback endast vid confidence < 0,95; inlärning SQLite och leverantörsspecifika mönster; manuell validering med klickbar PDF och kandidatval; dual extraction och fallback-kedja pdfplumber → OCR → AI → vision. Nya beslut i Phase 17: AI-policybeslut baseras på EDI-lik signal (text-layer, ankare, tabellmönster) och sparas i extraction_detail.ai_policy; deterministisk fallback körs före AI.

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-01-26 18:54 UTC
Stopped at: Completed 17-02-PLAN.md
Resume file: None
