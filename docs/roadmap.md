# Implementeringsroadmap

## Översikt

Roadmapen är indelad i tre faser som bygger på varandra. Varje fas implementeras sekventiellt innan nästa fas påbörjas.

## Fas 1: Vertical Slice

**Mål**: Skapa en komplett pipeline från PDF till CSV med grundläggande funktionalitet.

**Pipeline-steg**:
- PDF → Document
- Document → Page
- Page → Tokens
- Tokens → Rows
- Rows → Segments
- Segments → InvoiceLine
- InvoiceLine → Export (CSV)

**Krav**:
- Enklaste möjliga implementation som fungerar end-to-end
- Fokuserar på grundläggande produktrad-identifiering
- Ingen header-extraktion ännu (placeholder-data)
- Ingen validering ännu (direct export)
- Testa med `sample_invoice_1.pdf`

**Definition of Done**:
- Alla steg implementerade och testade
- Kan läsa PDF och producera CSV med produktrader
- Grundläggande parsing fungerar för enkel faktura

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

1. **Fas 1: Vertical slice** (PDF → tokens → rows → segments → CSV)
   - Implementera alla grundläggande steg
   - Fokus på produktrad-identifiering
   - Minimal men fungerande implementation

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
