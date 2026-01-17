# Invoice Parser App

## What This Is

Ett system som automatiskt läser, förstår och strukturerar svenska PDF-fakturor – oavsett layout, namn på fält eller antal sidor – och sammanställer resultatet i en tydlig Excel-tabell. Varje rad i Excel är en produktrad, fakturainformation (fakturanummer, företag, datum, total) upprepas korrekt, och summeringar samt belopp är validerade och pålitliga. Det är inte "OCR till text", utan OCR + layoutanalys + semantisk tolkning + kontroll. Systemet är ett CLI/script för batch-körning av några till hundratals fakturor per vecka, med möjlighet att lägga till web-UI senare.

## Core Value

**100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status.** Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW (ingen tyst gissning).

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] PDF → Excel pipeline: Transformera PDF-fakturor (1–n sidor) till Excel-tabell med en rad per produktrad
- [ ] Hard gates på fakturanummer och totalsumma: Ingen export som OK om inte båda är 100% säkra
- [ ] Fakturanummer-extraktion: Extrahera flera kandidater (OCR + AI), välj med scoring (position i header, närhet till "Faktura…", unikhet). Exakt ett finalt värde med hög confidence, eller REVIEW om osäkerhet
- [ ] Totalsumma-extraktion: Hitta "Att betala / Total / Summa att betala / Totalt", validera mot summa exkl + moms (+ avrundning). Måste passera matematisk kontroll, annars REVIEW
- [ ] Produktrad-extraktion: Best effort extraktion av produktrader med beskrivning, kvantitet, enhetspris, totalt belopp
- [ ] Summa-validering: Beräkna lines_sum = SUM(radbelopp), diff = total - lines_sum, klassificera som OK (diff inom ±1,00 SEK tolerans), PARTIAL (diff större men header säker), eller REVIEW (diff stor eller radbelopp saknas)
- [ ] Status-hantering: Sätt status OK/PARTIAL/REVIEW baserat på fakturanummer, totalsumma och summa-validering
- [ ] Spårbarhet: För fakturanummer och totalsumma spara sida, rad-index (eller bbox), källtext (kort utdrag) för klickbar navigering till PDF-markering
- [ ] Excel-export med kontrollkolumner: Fakturanummer, Totalsumma, LinesSum, Diff, Status, InvoiceNoConfidence, TotalConfidence (eller HeaderConfidence om kombinerad)
- [ ] Review-rapport: Skapa review-mapp med PDF + markeringar/metadata och enkel JSON/CSV-rapport med sida + bbox + textutdrag för felsökning

### Out of Scope

- Web-UI i v1 — CLI/script räcker för batch-körning, web-UI kan komma senare
- Realtidsflöde — v1 dimensioneras för batch-körning (några till hundratals per vecka)
- Allmänna PDF:er — fokus på svenska fakturor från test-korpus, men systemet ska tåla okända format genom hard gates och REVIEW-status
- Automatisk korrigering — systemet ska inte göra tysta gissningar, osäkra fall går till REVIEW

## Context

**Problemet:** Fakturor är inkonsekventa i layout och benämningar, svåra att hantera manuellt i volym, och tidskrävande att kontrollera rad för rad. Manuellt arbete eller enkla OCR-lösningar leder till fel i summeringar, missade rader, och låg tillit till datan.

**Lösningen:** Ett system som skapar strukturerad, spårbar och verifierbar data som kan användas direkt i Excel, uppföljning, ekonomi och analys.

**Befintlig dokumentation:** Projektet har redan dokumentation i `docs/` med roadmap, tasks, datamodell, heuristiker, valideringsregler och test-korpus. Specifikation för 12-stegs pipeline finns i `specs/invoice_pipeline_v1.md`. Systemet ska starta med befintliga fakturor (test-korpus) för snabb stabilitet, men ska samtidigt tåla okända format.

**Teknisk kontext:** Python 3.11+, pdfplumber för PDF-parsing, pandas för datahantering, pytest för testning. Pipeline genomgår Document → Page → Tokens → Rows → Segments → Zoner → Header → Specifikation → InvoiceLine → Reconciliation → Validation → Export.

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

---
*Last updated: 2025-01-27 after initialization*
