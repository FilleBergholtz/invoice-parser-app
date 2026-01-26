# Project Milestones: Invoice Parser App

## v2.0 Features + polish (Shipped: 2026-01-26)

**Delivered:** Förbättrad confidence-scoring, manuell validering med inlärning, AI-integration som fallback, dual extraction (pdfplumber + OCR), UI-polish, About + ikoner, samt extraction fallback-optimering och quality hardening (OCR confidence, routing, parser robustness).

**Phases completed:** 5–15 (46 plans total)

**Key accomplishments:**

- Förbättrad multi-factor confidence scoring och kalibrering för totalsumma (Phase 5)
- Klickbar PDF-validering med kandidatval och one-click-workflow (Phase 6)
- Inlärningssystem med SQLite och leverantörsspecifika mönster (Phase 7)
- AI-fallback vid confidence < 0,95 och strukturerade AI-svar (Phase 8)
- Dual extraction: pdfplumber + OCR, jämförelse och val av bästa källa (Phase 11, 14)
- Fallback-kedja pdfplumber → OCR → AI text → AI vision med text quality och DPI-retry (Phase 14, 15)
- UI-polish, tema, layout, engine-tillstånd och About-dialog + ikoner (Phase 12, 13)
- Traceability i run_summary: method_used, metrics, reason_flags, vision_reason (Phase 15)

**Stats:**

- 11 phases, 46 plans
- Python 3.11+, pdfplumber, PySide6, pytest
- Git range: phases 5–15 (flera commits 2026-01-24–2026-01-26)

**What's next:** Planera nästa milstolpe med `/gsd:discuss-milestone` och `/gsd:new-milestone`.

---

## v1.0 MVP (Shipped: 2026-01-17)

**Delivered:** PDF → Excel-pipeline med 100 % korrekthet på fakturanummer och totalsumma eller tydlig REVIEW-status.

**Phases completed:** 1–3 (14 plans total)

**Key accomplishments:**

- PDF-bearbetning (sökbara och skannade)
- Fakturanummer och totalsumma-extraktion med konfidensscoring
- Matematisk validering och status-tilldelning
- Excel-export med kontrollkolumner
- Desktop GUI (PySide6) och CLI
- 96.7% korrekt extraktion för vanliga fakturor

**What's next:** v2.0 Features + polish (completed above).

---
