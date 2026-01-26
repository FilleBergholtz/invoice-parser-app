# Invoice Parser App

## Status 2026-01-26

**Var vi är:** v1.0 och v2.0 är genomförda och arkiverade. v2.0 slutförd 2026-01-26. Nästa steg: `/gsd:discuss-milestone` → `/gsd:new-milestone` för att planera nästa version. Arkiv: `.planning/milestones/`, sammanfattning: `.planning/MILESTONES.md`.

---

## What This Is

Ett system som automatiskt läser, förstår och strukturerar svenska PDF-fakturor – oavsett layout, namn på fält eller antal sidor – och sammanställer resultatet i en tydlig Excel-tabell. Varje rad i Excel är en produktrad, fakturainformation (fakturanummer, företag, datum, total) upprepas korrekt, och summeringar samt belopp är validerade och pålitliga. Systemet har manuell validering i desktop-GUI (klickbar PDF, kandidatval), inlärning från korrigeringar (SQLite), AI-fallback vid låg confidence, och dual extraction (pdfplumber + OCR med val av bästa källa). CLI och PySide6-GUI för batch och interaktiv validering.

## Core Value

**100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status.** Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

## Requirements

### Validated

**v1.0 (shipped 2026-01-17):**

- [x] PDF → Excel pipeline, hard gates, fakturanummer/totalsumma-extraktion med konfidensscoring
- [x] Summa-validering, status OK/PARTIAL/REVIEW, spårbarhet, Excel-kontrollkolumner, review-rapport
- [x] Desktop GUI (PySide6) och CLI för batch

**v2.0 (shipped 2026-01-26):**

- [x] Förbättrad confidence-scoring för totalsumma — v2.0
- [x] Manuell validering i GUI med kandidatval — v2.0
- [x] Inlärning/databas från manuella valideringar — v2.0
- [x] AI-integration för confidence-förbättring och fallback — v2.0
- [x] AI för ovanliga mönster och dataanalys — v2.0
- [x] Dual extraction (pdfplumber + OCR), fallback pdfplumber → OCR → AI → vision — v2.0
- [x] UI-polish, About + ikoner — v2.0

### Active

**Nästa milstolpe (ej ännu definierad):**

- [ ] Krav att läggas in via `/gsd:new-milestone` och requirements-definition

### Out of Scope

- Web-UI — desktop-GUI (Phase 6) används; Phase 4 borttagen
- Realtidsflöde — batch (några till hundratals per vecka)
- Allmänna PDF:er — fokus svenska fakturor; hard gates och REVIEW för okända format
- Automatisk korrigering — osäkra fall till REVIEW, inga tysta gissningar

## Context

**Problemet:** Fakturor är inkonsekventa i layout och benämningar, svåra att hantera manuellt i volym.

**Lösningen:** Strukturerad, spårbar och verifierbar data med Excel-export, manuell validering där behov finns, och inlärning + AI-fallback för att minska REVIEW.

**Teknisk kontext:** Python 3.11+, pdfplumber, PySide6, pytest, SQLite (learning). Pipeline: Document → Tokens → Rows → Segments → Line/Header/Footer → Validation → Export. v2.0 tillförde dual extraction, text quality scoring, OCR confidence, DPI-retry och AI vision i fallback-kedjan.

## Constraints

- Tech stack: Python 3.11+, pdfplumber, pandas, pytest, PySide6
- Svenska fakturor; batch-körning; ±1,00 SEK tolerans; quality gate kvar

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hard gates på fakturanummer + totalsumma | Garanterar 100% korrekthet för OK-export | ✓ Good |
| Tolerans ±1,00 SEK | Hanterar öresavrundning och frakt/rabatt | ✓ Good |
| Excel med kontrollkolumner | Snabb batchgranskning | ✓ Good |
| Spårbarhet för kritiska fält | Klickbar PDF-navigering | ✓ Good |
| Desktop-GUI, ingen Web-UI | Fokus på stabilitet; Phase 4 borttagen | ✓ Good |
| AI endast vid confidence < 0,95 | Undviker over-reliance på AI | ✓ Good |
| Inlärning leverantörsspecifik, lokal SQLite | Integritet och enkel drift | ✓ Good |
| Dual extraction, välj bästa källa | Bättre täckning för skannade/sökbara mix | ✓ Good |

## Milestone History

### v2.0: Features + polish (Completed 2026-01-26)
- Confidence scoring, manuell validering, inlärning, AI-fallback, dual extraction
- UI-polish, About + ikoner, extraction fallback och quality hardening
- Se `.planning/MILESTONES.md` och `.planning/milestones/v2.0-ROADMAP.md`

### v1.0: Invoice Parser App (Completed 2026-01-17)
- PDF-bearbetning, fakturanummer/totalsumma-extraktion, validering, Excel, GUI, CLI
- 96.7% korrekt extraktion för vanliga fakturor

---
*Last updated: 2026-01-26 — v2.0 milestone complete*
