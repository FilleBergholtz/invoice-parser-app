# Implementeringschecklista

## Översikt

Denna checklista används för att spåra framsteg för varje task-implementation. Markera avklarade punkter när du implementerar enligt `docs/tasks.md`.

## Gate 0: Normalisering klar

**VIKTIGT**: Ingen header/line-item parsing får påbörjas innan Gate 0 är uppfylld.

Denna gate säkerställer att dokumentnormalisering är komplett och stabil innan vi går vidare till semantisk tolkning (fältextraktion). T1-T5 måste vara färdiga och verifierade innan T6 och framåt implementeras.

### Normaliserings-krav (måste vara klara innan semantisk parsing):

- [x] **PDF splittad till sidor**: Document → Page fungerar, alla sidor extraheras
- [x] **Sidbilder eller renderad sida finns**: Layout-information tillgänglig för varje sida
- [x] **Tokens med bbox finns för varje sida**: Page → Tokens fungerar, alla tokens har position (x, y, width, height)
- [x] **Rader är skapade och ordning verifierad**: Tokens → Rows fungerar, radordning top-to-bottom verifierad på testkorpus
- [x] **Segment (header/items/footer) finns**: Rows → Segments fungerar, minst grov segmentering implementerad
- [x] **Spårbarhet verifierad**: Kan peka ut `page_number` + `token bbox` för valfri text i pipeline

### Verifiering

Innan du går vidare till T6 (Segments → InvoiceLine), verifiera:
1. Alla kriterier ovan är checkade
2. Spårbarhet fungerar: Kan spåra en InvoiceLine tillbaka till ursprunglig Page/Row/Token
3. Normalisering är stabil och robust på testkorpusen

**STOPP**: Om något av kriterierna ovan inte är uppfyllda, fixa det INNAN du börjar med fältextraktion.

---

## Allmänna krav för varje task

### Implementation
- [x] Kod implementerad enligt task-specifikation
- [x] Klasser/strukturer följer `docs/02_data-model.md` exakt
- [x] Type hints för alla funktioner och metoder
- [x] Docstrings för alla klasser och funktioner
- [x] Följer PEP 8 style guide
- [x] Kod är lättläst och välkommenterad

### Testning
- [x] Unit tests skapade
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`
- [x] Edge cases hanterade (om tillämpligt)

### Dokumentation
- [x] Task DoD-kriterier uppfyllda
- [x] Checklista markerad (denna fil)
- [x] Uppdaterad om nya edge cases upptäckts

## Fas 1: Vertical Slice

### [T1] PDF → Document
- [x] Document-klass implementerad
- [x] PDF-läsning fungerar
- [x] Metadata extraheras
- [x] Unit tests passerar
- [x] Testat med sample_invoice_1.pdf

### [T2] Document → Page
- [x] Page-klass implementerad
- [x] Sidor extraheras korrekt
- [x] Sidnumrering fungerar
- [x] Unit tests passerar
- [x] Testat med sample_invoice_1.pdf

### [T3] Page → Tokens
- [x] Token-klass implementerad
- [x] Tokenisering med positioner fungerar
- [x] Spatial information korrekt
- [x] Unit tests passerar
- [x] Testat med sample_invoice_1.pdf

### [T4] Tokens → Rows
- [x] Row-klass implementerad
- [x] Token-gruppering fungerar
- [x] Y-position tolerans implementerad
- [x] Radordning bevaras
- [x] Unit tests passerar
- [x] Testat med sample_invoice_1.pdf

### [T5] Rows → Segments
- [x] Segment-klass implementerad
- [x] Segment-identifiering fungerar
- [x] Header/items/footer identifieras korrekt
- [x] Position-baserad identifiering fungerar
- [x] Unit tests passerar
- [x] Testat med sample_invoice_1.pdf

### [T6] Segments → InvoiceLine
- [x] InvoiceLine-klass implementerad
- [x] Produktrad-parsing fungerar
- [x] Regel "rad med belopp = produktrad" implementerad
- [x] Fält extraheras korrekt
- [x] Unit tests passerar
- [x] Testat med sample_invoice_1.pdf

### [T7] InvoiceLine → Export (CSV)
- [x] CSV-export fungerar
- [x] Korrekt kolumnstruktur
- [x] UTF-8 kodning fungerar
- [x] CLI-entry point fungerar
- [x] Unit tests passerar
- [x] End-to-end pipeline testat
- [x] **Fas 1 komplett**

## Fas 2: Header + Wrap

### [T8] Segments → Zoner
- [x] Zone-klass implementerad
- [x] Spatial zonering fungerar
- [x] Zon-typer identifieras korrekt
- [x] Unit tests passerar
- [x] Testat med sample_invoice_1.pdf

### [T9] Zoner → Header
- [x] InvoiceHeader-klass implementerad
- [x] Header-scoring fungerar
- [x] Header-segment identifieras korrekt
- [x] Konfidenspoäng beräknas
- [x] Unit tests passerar
- [x] Testat med sample_invoice_1.pdf

### [T10] Header → Specifikation
- [x] InvoiceSpecification-klass implementerad
- [x] Fakturanummer extraheras
- [x] Datum extraheras (flera format)
- [x] Leverantör/kund extraheras
- [x] Unit tests passerar
- [x] Testat med sample_invoice_1.pdf

### [T11] Förbättring: Fortsättningsrader
- [x] Wrap-identifiering fungerar
- [x] Wrapped text kopplas korrekt
- [x] Beskrivning konsolideras
- [x] Unit tests passerar
- [x] Testat med wraps i faktura
- [x] **Fas 2 komplett**

## Fas 3: Validering

### [T12] InvoiceLine → Reconciliation
- [x] Reconciliation-klass implementerad
- [x] Summa-beräkning fungerar
- [x] Footer-parsing fungerar
- [x] Skillnader beräknas korrekt
- [x] Unit tests passerar
- [x] Testat med sample_invoice_1.pdf

### [T13] Reconciliation → Validation
- [x] Validation-klass implementerad
- [x] Valideringsregler implementerade
- [x] Status sätts korrekt (OK/Warning/Review)
- [x] Meddelanden genereras
- [x] Unit tests passerar
- [x] Testat med olika scenarion

### [T14] Validation → Validation Result
- [x] Validation-klass implementerad
- [x] Valideringsregler implementerade
- [x] Status sätts korrekt (OK/Warning/Review)
- [x] Validation failures blockerar Excel-generering (om inte explicit overridden)
- [x] Meddelanden genereras
- [x] Unit tests passerar
- [x] Testat med olika scenarion

### [T15] Build final Excel export
- [x] Excel-export fungerar
- [x] En rad = en produktrad
- [x] Korrekt kolumnordning (Fakturanummer, Referenser, Företag, Fakturadatum, Beskrivning, Antal, Enhet, Á-pris, Rabatt, Summa, Hela summan)
- [x] Numeriska fält är numeriska (ej text)
- [x] Textfält är text (Fakturanummer, Referenser, Företag, etc.)
- [x] Tomma valfria fält hanteras korrekt
- [x] Återkommande fält upprepas korrekt per rad
- [x] SUM(Summa) ≈ Hela summan (verifiering i Excel)
- [x] Unit tests passerar
- [x] Minst en faktura manuellt kontrollerad i Excel
- [x] **Fas 3 komplett**

## Gate: Excel export verifierad

**VIKTIGT**: Systemet anses inte klart om Excel inte kan genereras.

Innan projektet kan anses komplett måste följande vara uppfyllda:

- [x] **Excel-fil skapad**: Slutresultat är en Excel-fil (inte CSV)
- [x] **En rad = en produktrad**: Varje InvoiceLine motsvarar en rad i Excel
- [x] **Återkommande fält upprepas korrekt**: Fakturanummer, datum, leverantör upprepas per rad
- [x] **Tomma valfria fält hanteras korrekt**: Rabatt, Referenser etc. visar tom cell eller "-" om saknas
- [x] **Minst en faktura manuellt kontrollerad i Excel**: Excel öppnas utan varningar och data är korrekt

**Verifiering**:
1. Öppna Excel-filen och kontrollera att den öppnas utan varningar
2. Verifiera att numeriska kolumner är numeriska (ej text)
3. Kontrollera SUM(Summa) ≈ Hela summan
4. Verifiera att återkommande fält upprepas korrekt

---

## Projektkomplett checklista

### Kodbas
- [x] Alla tasks implementerade
- [x] Alla tests passerar
- [x] Kodkvalitet godkänd
- [x] Type hints överallt
- [x] Docstrings överallt

### Dokumentation
- [x] README.md uppdaterad om nödvändigt
- [x] Edge cases dokumenterade
- [x] Test-korpus dokumenterad

### Validering
- [x] Pipeline fungerar end-to-end
- [x] Validering fungerar korrekt
- [x] Export genererar korrekt output
- [x] Testat med flera fakturor

## Anteckningar

Använd detta avsnitt för att dokumentera:
- Upptäckta edge cases
- Beslut om avvikelser från planen
- Förbättringsförslag för framtida iterationer
