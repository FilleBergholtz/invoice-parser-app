# Invoice Parser App

## Status 2026-01-25

**Var vi är:** v1.0 (Phase 1–3) och v2.0 (Phase 5–13) är genomförda. Alla planerade faser klara. Senaste: Phase 13 (About-dialog, Hjälp-meny, ikoner, Windows .ico). Verifiering av Phase 9, 10 och 11 gjord 2026-01-25. Nästa steg: `/gsd:complete-milestone` eller planera nya faser. Detaljer: `.planning/STATE.md`, `.planning/ROADMAP.md`.

---

## What This Is

Ett system som automatiskt läser, förstår och strukturerar svenska PDF-fakturor – oavsett layout, namn på fält eller antal sidor – och sammanställer resultatet i en tydlig Excel-tabell. Varje rad i Excel är en produktrad, fakturainformation (fakturanummer, företag, datum, total) upprepas korrekt, och summeringar samt belopp är validerade och pålitliga. Det är inte "OCR till text", utan OCR + layoutanalys + semantisk tolkning + kontroll. Systemet är ett CLI/script för batch-körning av några till hundratals fakturor per vecka, med möjlighet att lägga till web-UI senare.

## Core Value

**100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status.** Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

## Current Milestone: v2.0 Features

**Goal:** Förbättra totalsumma-confidence, lägga till manuell validering med inlärning, och integrera AI för att minska REVIEW-status och hantera ovanliga mönster.

**Target features:**
- Förbättrad confidence-scoring för totalsumma (färre REVIEW-status)
- Manuell validering i GUI: användare kan klicka på totalsumma i PDF och välja rätt alternativ
- Inlärning/databas: systemet lär sig från manuella valideringar för framtida förbättringar
- AI-integration: AI aktiveras när confidence < 0.95 för att förbättra extraktion
- AI för ovanliga mönster: ställa frågor om fakturdata, hämta och presentera information

## Requirements

### Validated

**v1.0 Requirements (shipped 2026-01-17):**

- [x] PDF → Excel pipeline: Transformera PDF-fakturor (1–n sidor) till Excel-tabell med en rad per produktrad
- [x] Hard gates på fakturanummer och totalsumma: Ingen export som OK om inte båda är 100% säkra
- [x] Fakturanummer-extraktion: Extrahera flera kandidater, välj med scoring (position i header, närhet till "Faktura…", unikhet). Exakt ett finalt värde med hög confidence, eller REVIEW om osäkerhet
- [x] Totalsumma-extraktion: Hitta "Att betala / Total / Summa att betala / Totalt", validera mot summa exkl + moms (+ avrundning). Måste passera matematisk kontroll, annars REVIEW
- [x] Produktrad-extraktion: Best effort extraktion av produktrader med beskrivning, kvantitet, enhetspris, totalt belopp
- [x] Summa-validering: Beräkna lines_sum = SUM(radbelopp), diff = total - lines_sum, klassificera som OK (diff inom ±1,00 SEK tolerans), PARTIAL (diff större men header säker), eller REVIEW (diff stor eller radbelopp saknas)
- [x] Status-hantering: Sätt status OK/PARTIAL/REVIEW baserat på fakturanummer, totalsumma och summa-validering
- [x] Spårbarhet: För fakturanummer och totalsumma spara sida, rad-index (eller bbox), källtext (kort utdrag) för klickbar navigering till PDF-markering
- [x] Excel-export med kontrollkolumner: Fakturanummer, Totalsumma, LinesSum, Diff, Status, InvoiceNoConfidence, TotalConfidence
- [x] Review-rapport: Skapa review-mapp med PDF + markeringar/metadata och enkel JSON/CSV-rapport med sida + bbox + textutdrag för felsökning
- [x] Desktop GUI (PySide6) för enkel användning
- [x] CLI för batch-bearbetning

### Active

**v2.0 Requirements (to be defined):**

- [ ] Förbättrad confidence-scoring för totalsumma
- [ ] Manuell validering i GUI med alternativ
- [ ] Inlärning/databas från manuella valideringar
- [ ] AI-integration för confidence-förbättring och fallback
- [ ] AI för ovanliga mönster och dataanalys

### Out of Scope

- Web-UI i v1 — CLI/script räcker för batch-körning, web-UI kan komma senare
- Realtidsflöde — v1 dimensioneras för batch-körning (några till hundratals per vecka)
- Allmänna PDF:er — fokus på svenska fakturor från test-korpus, men systemet ska tåla okända format genom hard gates och REVIEW-status
- Automatisk korrigering — systemet ska inte göra tysta gissningar, osäkra fall går till REVIEW

## Context

**Problemet:** Fakturor är inkonsekventa i layout och benämningar, svåra att hantera manuellt i volym, och tidskrävande att kontrollera rad för rad. Manuellt arbete eller enkla OCR-lösningar leder till fel i summeringar, missade rader, och låg tillit till datan.

**Lösningen:** Ett system som skapar strukturerad, spårbar och verifierbar data som kan användas direkt i Excel, uppföljning, ekonomi och analys.

**Befintlig dokumentation:** Projektet har redan dokumentation i `docs/` med roadmap, tasks, datamodell, heuristiker, valideringsregler och test-korpus. Specifikation för 12-stegs pipeline finns i `specs/invoice_pipeline_v1.md`. Systemet ska starta med befintliga fakturor (test-korpus) för snabb stabilitet, men ska samtidigt tåla okända format.

**Teknisk kontext:** Python 3.11+, pdfplumber för PDF-parsing, pandas för datahantering, pytest för testning, PySide6 för GUI. Pipeline genomgår Document → Page → Tokens → Rows → Segments → InvoiceLine → Header → Footer → Validation → Export (10 steg, se `specs/invoice_pipeline_v1.md`).

## Constraints

- **Tech stack**: Python 3.11+, pdfplumber, pandas, pytest — redan etablerat i projektet
- **Svenska fakturor**: Systemet är optimerat för svenska fakturor med svenska fältnamn och format
- **Batch-körning**: Dimensionerat för batch-bearbetning, inte realtidsflöde
- **Tolerans**: ±1,00 SEK för summa-validering (öresavrundning, frakt/rabatt-rader)
- **Quality gate**: Ingen export som OK om fakturanummer eller totalsumma saknas/är osäkra

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hard gates på fakturanummer + totalsumma | Garanterar 100% korrekthet för allt som exporteras som OK. Osäkra fall går till REVIEW istället för tysta gissningar. | — Pending |
| Tolerans ±1,00 SEK för summa-validering | Hanterar öresavrundning och frakt/rabatt-rader utan att flagga falska varningar. | — Pending |
| Excel med kontrollkolumner i v1 | Gör batchgranskning mycket snabbare genom att visa LinesSum, Diff, Status, Confidence direkt i tabellen. | — Pending |
| Spårbarhet för kritiska fält | Möjliggör klickbar navigering till PDF-markering för fakturanummer och totalsumma, vilket är grunden för 100% korrekthet i praktiken. | — Pending |
| CLI för v1, web-UI senare | Fokuserar på core-funktionalitet först, lägger till UI senare när grundflödet är stabilt. | — Pending |

## Milestone History

### v1.0: Invoice Parser App (Completed 2026-01-17)
- PDF-bearbetning (sökbara och skannade)
- Fakturanummer och totalsumma-extraktion med konfidensscoring
- Matematisk validering och status-tilldelning
- Excel-export med kontrollkolumner
- Desktop GUI (PySide6) och CLI
- 96.7% korrekt extraktion för vanliga fakturor

---
*Last updated: 2026-01-24 — Started v2.0 milestone*
