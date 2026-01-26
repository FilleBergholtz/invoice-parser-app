# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

**Current focus:** v2.1 Phase 17 planerad efter verifierad Phase 16.

## Current Position

Milestone: **v2.1 Parsing robustness / EDI** (pågående).
Phase: **16** — Text-layer routing (OCR-skip) (klar).
Plan: 16-01 genomförd; verifiering passerad.
Status: Phase 16 klar, redo för Phase 17 (AI-policy fallback).
Last activity: 2026-01-26 — Phase 16 verifierad (runtime OK, compare-path utan crash).

Progress: ████████████████████ 65/65 (100%) — v1.0 (Phase 1–3) + v2.0 (Phase 5–15) genomförda och arkiverade; Phase 16 klar.

## Accumulated Context

### Decisions

Se PROJECT.md Key Decisions. v2.0-beslut: AI fallback endast vid confidence < 0,95; inlärning SQLite och leverantörsspecifika mönster; manuell validering med klickbar PDF och kandidatval; dual extraction och fallback-kedja pdfplumber → OCR → AI → vision. Inga nya beslut i Phase 16.

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-01-26 18:43 UTC
Stopped at: Phase 16 verifierad och klar
Resume file: None
