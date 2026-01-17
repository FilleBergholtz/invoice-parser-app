# Implementeringsroadmap

## Översikt

Roadmapen är indelad i tre faser som bygger på varandra. Varje fas implementeras sekventiellt innan nästa fas påbörjas.

## Primary Output: Excel (Single Table)

**Slutmål**: Projektets primära output är en Excel-fil med strukturerad faktura-data.

**Excel-struktur**:
- Slutresultatet ska alltid vara en Excel-fil
- En rad = en produktrad (InvoiceLine)
- Återkommande fakturafält upprepas per rad (fakturanummer, datum, leverantör)
- Excel används som verifierbar leverans, även om andra exporter tillkommer senare

**Design-krav**:
- All upstream design (datamodell, heuristik, validering) ska stödja korrekt Excel-export utan manuell efterbearbetning
- Validering blockerar Excel-generering om kritiska fel finns
- Excel-kolumner: Fakturanummer, Referenser, Företag, Fakturadatum, Beskrivning, Antal, Enhet, Á-pris, Rabatt, Summa, Hela summan

---

## Fas 1: Document Normalization

**Mål**: Skapa en stabil representation av PDF-dokumentet med full spårbarhet. Fas 1 fokuserar på **Document normalization** - att transformera PDF till en robust, strukturerad representation innan vi försöker tolka specifika fält.

**Fokus**: Fas 1 är **inte** "snabb parsing", utan **"stabil representation + spårbarhet"**. Vi bygger en solid grund innan vi lägger till komplex tolkning.

**Pipeline-steg**:
- PDF → Document
- Document → Page
- Page → Tokens
- Tokens → Rows
- Rows → Segments
- Segments → InvoiceLine
- InvoiceLine → Export (Excel)

**Principer för Fas 1**:
- **Alltid splitta PDF till sidor**: Varje sida bearbetas separat med tydlig sidnumrering
- **All text ska bli tokens med position**: Varje text-enhet måste ha exakt spatial information (x, y, width, height)
- **Row/Segment måste vara robust innan vi försöker tolka fält**: Identifiering av rader och segment måste vara stabil och korrekt innan vi börjar extrahera specifika fält
- **Målet är korrekt reading-order och spårbarhet**: Varje element (token, row, segment) måste kunna spåras tillbaka till ursprunglig sida och position

**Krav**:
- Stabil och robust tokenisering med korrekt positioner
- Robust rad-gruppering baserat på Y-position
- Korrekt segment-identifiering (header/items/footer)
- Full spårbarhet: varje InvoiceLine kan spåras tillbaka till Page/Row/Token
- Grundläggande produktrad-identifiering (regel: "rad med belopp = produktrad")
- Ingen header-extraktion ännu (placeholder-data)
- Ingen validering ännu (direct export)
- Testa med `sample_invoice_1.pdf`

**Definition of Done**:
- Alla steg implementerade och testade
- Kan läsa PDF och producera Excel med produktrader
- Grundläggande parsing fungerar för enkel faktura
- **Kan återskapa en 'komprimerad representation' per sida (rader top-to-bottom) med bibehållen spårbarhet**
- Varje InvoiceLine har spårbarhet tillbaka till ursprunglig Page/Row/Token

---

## Fas 2: Header + Wrap

**Mål**: Förbättra parsing med header-extraktion och hantering av fortsättningsrader.

**Pipeline-steg**:
- Segments → Zoner
- Zoner → Header
- Header → Specifikation
- Förbättring: Fortsättningsrader (wrapped text) kopplas till InvoiceLine

**Krav**:
- Header-scoring för att identifiera fakturahuvud
- Extraktion av metadata (fakturanummer, datum, leverantör)
- Spatial zonering för kontextuell analys
- Hantering av produktrader som är uppdelade på flera rader

**Definition of Done**:
- Header-extraktion fungerar korrekt
- Metadata (datum, nummer, leverantör) extraheras
- Fortsättningsrader kopplas till rätt produktrad
- Testa med `sample_invoice_1.pdf` och edge cases

---

## Fas 3: Validering

**Mål**: Lägg till kvalitetskontroll och validering av extraherad data.

**Pipeline-steg**:
- InvoiceLine → Reconciliation
- Reconciliation → Validation
- Validation → Export (med status)

**Krav**:
- Beräkning av totalsummor
- Jämförelse mellan beräknade och extraherade summor
- Status-bestämning (OK/Warning/Review)
- Validering av obligatoriska fält
- Felhantering och rapportering

**Definition of Done**:
- Reconciliation beräknar summor korrekt
- Validation-status sätts korrekt baserat på avvikelser
- Export inkluderar valideringsstatus
- Testa med olika faktura-typer och edge cases

---

## Implementeringsordning

1. **Fas 1: Document Normalization** (PDF → tokens → rows → segments → CSV)
   - Implementera alla grundläggande steg
   - Fokus på stabil representation och spårbarhet
   - Robust tokenisering, rad-gruppering och segment-identifiering
   - Korrekt reading-order med full spårbarhet till ursprunglig PDF

2. **Fas 2: Header + wrap** (Zoner, Header scoring, Fortsättningsrader)
   - Lägg till header-extraktion
   - Förbättra produktrad-identifiering med wraps
   - Spatial analys med zoner

3. **Fas 3: Validering** (Reconciliation, Status OK/Warning/Review)
   - Lägg till kvalitetskontroll
   - Summa-validering
   - Status-hantering

## Task-sekvens

Varje fas är uppdelad i atomiska tasks enligt `docs/tasks.md`. Tasks implementeras sekventiellt inom varje fas.

### Fas 1 Tasks:
- T1-T7: Grundläggande pipeline-steg

### Fas 2 Tasks:
- T8-T11: Header och wrap-funktionalitet

### Fas 3 Tasks:
- T12-T14: Validering och reconciliation

## Testning

Varje fas testas med:
- `sample_invoice_1.pdf` (test-korpus)
- Edge cases dokumenterade i `docs/06_test-corpus.md`
- Unit tests för varje pipeline-steg
- Integrationstester för varje fas

## Nästa steg

Börja med Fas 1, Task T1 enligt `docs/tasks.md`.
