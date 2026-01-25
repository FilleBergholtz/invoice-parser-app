# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-01-24)

**Core value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

**Current focus:** Alla planerade faser (v1 + v2) genomförda. Status och roadmap uppdaterade 2026-01-25.

## Current Position

Milestone: v2.0 Features + polish
Phase: **Phase 14 (nästa)** — Extraction fallback optimization (pdfplumber → OCR → AI → vision)
Plans: 14-01 … 14-06 (planerade 2026-01-25)
Status: Phase 13 klar. **Phase 14 planerad** — 6 planer, 4 waves.
Last activity: 2026-01-25 — Phase 14 plan-phase: 14-01…14-06 skapade.

Progress: Phase 1–3 (v1) + Phase 5–13 (v2) genomförda. **Phase 14** planerad, redo för execute-phase.

## Performance Metrics

**Velocity:**
- Total plans completed: 48 (Phase 1–3, 5–13; Phase 4 borttagen)
- v2.0 phases 5–13: alla genomförda (5→6→7→8→9→10→11→12→13)

**By Phase (v2.0):**

| Phase | Plans | Status |
|-------|-------|--------|
| 5. Confidence Scoring | 3/3 | ✓ |
| 6. Manual Validation UI | 4/4 | ✓ |
| 7. Learning System | 6/6 | ✓ |
| 8. AI Integration | 3/3 | ✓ |
| 9. AI Data Analysis | 3/3 | ✓ |
| 10. AI Fallback Fixes | 2/2 | ✓ |
| 11. Pdfplumber/OCR compare | 3/3 | ✓ |
| 12. UI Polish | 5/5 | ✓ |
| 13. About + icons | 3/3 | ✓ |

*Uppdaterad 2026-01-25 — progress/roadmap-synk*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [v2.0]: AI fallback pattern — AI only when confidence < 0.95 (avoid over-reliance)
- [v2.0]: Learning system — SQLite database, supplier-specific patterns, local storage
- [v2.0]: Manual validation — Clickable PDF with candidate selection, one-click workflow
- [v2.0]: Confidence calibration — Map confidence to actual accuracy from start

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Roadmap Evolution

- Phase 10 added: AI Fallback Fixes and Verification — document fixes, address gaps, verify AI fallback works well.
- Phase 11 added: Pdfplumber och OCR: kör båda, jämför, använd bästa — dual extraction, compare results, use best.
- Phase 11 planned: 11-01 (OCR wiring), 11-02 (dual-run compare), 11-03 (use best downstream).
- Phase 13 added: About page + app icons (branding & help) — Om-dialog, Hjälp-meny, fönsterikoner. Discuss-phase 13: 13-DISCUSS.md with tabbed About (Om appen + Hjälp), QRC/icons, Windows .ico. Plans: 13-01 (About + Help menu), 13-02 (QRC + apply icons), 13-03 (Windows .ico + build).
- Phase 14 added: Extraction fallback optimization (pdfplumber → OCR → AI → vision) — optimera fallback-kedjan för textextraktion.
- Phase 14 discussed: 14-DISCUSS.md + 14-CONTEXT.md. Beslut: per-page routing, text quality scoring, Token.confidence, AI text vs vision, artifacts; redo för plan-phase.
- Phase 14 discuss uppdaterad: mål "robust, accurate, cost-efficient"; steg 3 uttryckligen "AI (text-only)"; fyra begränsade research-uppgifter R1–R4 (OCR-rendering, OCR-confidence, AI vision-gränser, AI-routing) med leverabler och constraints; implementation post-research (6 uppgifter); run_summary ska förklara *varför* OCR/AI användes.
- Phase 14 research R1–R4 genomförd (14-RESEARCH.md): R1 baseline 300 DPI, retry 400 vid mean_conf<55; R2 median_conf, exkl. conf<0, tröskel 70; R3 vision PNG/JPEG max 4096px 20MB; R4 routing-tabell + text_quality 0.5 + retry-regler. Konstanter klara för implementation.
- Phase 14 planerad: 6 planer (14-01…14-06). Wave 1: Token+OCR confidence, pdfplumber tokenizer. Wave 2: text_quality, rendering DPI. Wave 3: AI vision+retry. Wave 4: orchestration + run_summary/vision_reason.

### Blockers/Concerns

[Issues that affect future work]

None yet.

## Session Continuity

Last session: 2026-01-25
Stopped at: Phase 13 executed (About dialog, Help menu, icons QRC, Windows app.ico + spec).
Resume file: None
