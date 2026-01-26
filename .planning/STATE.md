# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-26)

**Core value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

**Current focus:** v2.1 Parsing robustness / EDI planerad och klar för start.

## Current Position

Milestone: **v2.1 Parsing robustness / EDI** (planerad).
Phase: **16** — Text-layer routing (OCR-skip).
Plan: ROADMAP.md skapad, Traceability uppdaterad i REQUIREMENTS.md.
Status: Planerad, ej påbörjad.
Last activity: 2026-01-26 — v2.1 ROADMAP/STATE/REQUIREMENTS uppdaterade.

Progress: v1.0 (Phase 1–3) + v2.0 (Phase 5–15) genomförda och arkiverade.

## Accumulated Context

### Decisions

Se PROJECT.md Key Decisions. v2.0-beslut: AI fallback endast vid confidence < 0,95; inlärning SQLite och leverantörsspecifika mönster; manuell validering med klickbar PDF och kandidatval; dual extraction och fallback-kedja pdfplumber → OCR → AI → vision.

### Pending Todos

None.

### Blockers/Concerns

None.

## Session Continuity

Last session: 2026-01-26
Stopped at: v2.0 complete-milestone executed.
Resume file: None
