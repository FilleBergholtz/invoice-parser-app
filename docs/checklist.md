# Implementeringschecklista

## Översikt

Denna checklista används för att spåra framsteg för varje task-implementation. Markera avklarade punkter när du implementerar enligt `docs/tasks.md`.

## Gate 0: Normalisering klar

**VIKTIGT**: Ingen header/line-item parsing får påbörjas innan Gate 0 är uppfylld.

Denna gate säkerställer att dokumentnormalisering är komplett och stabil innan vi går vidare till semantisk tolkning (fältextraktion). T1-T5 måste vara färdiga och verifierade innan T6 och framåt implementeras.

### Normaliserings-krav (måste vara klara innan semantisk parsing):

- [ ] **PDF splittad till sidor**: Document → Page fungerar, alla sidor extraheras
- [ ] **Sidbilder eller renderad sida finns**: Layout-information tillgänglig för varje sida
- [ ] **Tokens med bbox finns för varje sida**: Page → Tokens fungerar, alla tokens har position (x, y, width, height)
- [ ] **Rader är skapade och ordning verifierad**: Tokens → Rows fungerar, radordning top-to-bottom verifierad på testkorpus
- [ ] **Segment (header/items/footer) finns**: Rows → Segments fungerar, minst grov segmentering implementerad
- [ ] **Spårbarhet verifierad**: Kan peka ut `page_number` + `token bbox` för valfri text i pipeline

### Verifiering

Innan du går vidare till T6 (Segments → InvoiceLine), verifiera:
1. Alla kriterier ovan är checkade
2. Spårbarhet fungerar: Kan spåra en InvoiceLine tillbaka till ursprunglig Page/Row/Token
3. Normalisering är stabil och robust på testkorpusen

**STOPP**: Om något av kriterierna ovan inte är uppfyllda, fixa det INNAN du börjar med fältextraktion.

---

## Allmänna krav för varje task

### Implementation
- [ ] Kod implementerad enligt task-specifikation
- [ ] Klasser/strukturer följer `docs/02_data-model.md` exakt
- [ ] Type hints för alla funktioner och metoder
- [ ] Docstrings för alla klasser och funktioner
- [ ] Följer PEP 8 style guide
- [ ] Kod är lättläst och välkommenterad

### Testning
- [ ] Unit tests skapade
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`
- [ ] Edge cases hanterade (om tillämpligt)

### Dokumentation
- [ ] Task DoD-kriterier uppfyllda
- [ ] Checklista markerad (denna fil)
- [ ] Uppdaterad om nya edge cases upptäckts

## Fas 1: Vertical Slice

### [T1] PDF → Document
- [ ] Document-klass implementerad
- [ ] PDF-läsning fungerar
- [ ] Metadata extraheras
- [ ] Unit tests passerar
- [ ] Testat med sample_invoice_1.pdf

### [T2] Document → Page
- [ ] Page-klass implementerad
- [ ] Sidor extraheras korrekt
- [ ] Sidnumrering fungerar
- [ ] Unit tests passerar
- [ ] Testat med sample_invoice_1.pdf

### [T3] Page → Tokens
- [ ] Token-klass implementerad
- [ ] Tokenisering med positioner fungerar
- [ ] Spatial information korrekt
- [ ] Unit tests passerar
- [ ] Testat med sample_invoice_1.pdf

### [T4] Tokens → Rows
- [ ] Row-klass implementerad
- [ ] Token-gruppering fungerar
- [ ] Y-position tolerans implementerad
- [ ] Radordning bevaras
- [ ] Unit tests passerar
- [ ] Testat med sample_invoice_1.pdf

### [T5] Rows → Segments
- [ ] Segment-klass implementerad
- [ ] Segment-identifiering fungerar
- [ ] Header/items/footer identifieras korrekt
- [ ] Position-baserad identifiering fungerar
- [ ] Unit tests passerar
- [ ] Testat med sample_invoice_1.pdf

### [T6] Segments → InvoiceLine
- [ ] InvoiceLine-klass implementerad
- [ ] Produktrad-parsing fungerar
- [ ] Regel "rad med belopp = produktrad" implementerad
- [ ] Fält extraheras korrekt
- [ ] Unit tests passerar
- [ ] Testat med sample_invoice_1.pdf

### [T7] InvoiceLine → Export (CSV)
- [ ] CSV-export fungerar
- [ ] Korrekt kolumnstruktur
- [ ] UTF-8 kodning fungerar
- [ ] CLI-entry point fungerar
- [ ] Unit tests passerar
- [ ] End-to-end pipeline testat
- [ ] **Fas 1 komplett**

## Fas 2: Header + Wrap

### [T8] Segments → Zoner
- [ ] Zone-klass implementerad
- [ ] Spatial zonering fungerar
- [ ] Zon-typer identifieras korrekt
- [ ] Unit tests passerar
- [ ] Testat med sample_invoice_1.pdf

### [T9] Zoner → Header
- [ ] InvoiceHeader-klass implementerad
- [ ] Header-scoring fungerar
- [ ] Header-segment identifieras korrekt
- [ ] Konfidenspoäng beräknas
- [ ] Unit tests passerar
- [ ] Testat med sample_invoice_1.pdf

### [T10] Header → Specifikation
- [ ] InvoiceSpecification-klass implementerad
- [ ] Fakturanummer extraheras
- [ ] Datum extraheras (flera format)
- [ ] Leverantör/kund extraheras
- [ ] Unit tests passerar
- [ ] Testat med sample_invoice_1.pdf

### [T11] Förbättring: Fortsättningsrader
- [ ] Wrap-identifiering fungerar
- [ ] Wrapped text kopplas korrekt
- [ ] Beskrivning konsolideras
- [ ] Unit tests passerar
- [ ] Testat med wraps i faktura
- [ ] **Fas 2 komplett**

## Fas 3: Validering

### [T12] InvoiceLine → Reconciliation
- [ ] Reconciliation-klass implementerad
- [ ] Summa-beräkning fungerar
- [ ] Footer-parsing fungerar
- [ ] Skillnader beräknas korrekt
- [ ] Unit tests passerar
- [ ] Testat med sample_invoice_1.pdf

### [T13] Reconciliation → Validation
- [ ] Validation-klass implementerad
- [ ] Valideringsregler implementerade
- [ ] Status sätts korrekt (OK/Warning/Review)
- [ ] Meddelanden genereras
- [ ] Unit tests passerar
- [ ] Testat med olika scenarion

### [T14] Validation → Validation Result
- [ ] Validation-klass implementerad
- [ ] Valideringsregler implementerade
- [ ] Status sätts korrekt (OK/Warning/Review)
- [ ] Validation failures blockerar Excel-generering (om inte explicit overridden)
- [ ] Meddelanden genereras
- [ ] Unit tests passerar
- [ ] Testat med olika scenarion

### [T15] Build final Excel export
- [ ] Excel-export fungerar
- [ ] En rad = en produktrad
- [ ] Korrekt kolumnordning (Fakturanummer, Referenser, Företag, Fakturadatum, Beskrivning, Antal, Enhet, Á-pris, Rabatt, Summa, Hela summan)
- [ ] Numeriska fält är numeriska (ej text)
- [ ] Textfält är text (Fakturanummer, Referenser, Företag, etc.)
- [ ] Tomma valfria fält hanteras korrekt
- [ ] Återkommande fält upprepas korrekt per rad
- [ ] SUM(Summa) ≈ Hela summan (verifiering i Excel)
- [ ] Unit tests passerar
- [ ] Minst en faktura manuellt kontrollerad i Excel
- [ ] **Fas 3 komplett**

## Gate: Excel export verifierad

**VIKTIGT**: Systemet anses inte klart om Excel inte kan genereras.

Innan projektet kan anses komplett måste följande vara uppfyllda:

- [ ] **Excel-fil skapad**: Slutresultat är en Excel-fil (inte CSV)
- [ ] **En rad = en produktrad**: Varje InvoiceLine motsvarar en rad i Excel
- [ ] **Återkommande fält upprepas korrekt**: Fakturanummer, datum, leverantör upprepas per rad
- [ ] **Tomma valfria fält hanteras korrekt**: Rabatt, Referenser etc. visar tom cell eller "-" om saknas
- [ ] **Minst en faktura manuellt kontrollerad i Excel**: Excel öppnas utan varningar och data är korrekt

**Verifiering**:
1. Öppna Excel-filen och kontrollera att den öppnas utan varningar
2. Verifiera att numeriska kolumner är numeriska (ej text)
3. Kontrollera SUM(Summa) ≈ Hela summan
4. Verifiera att återkommande fält upprepas korrekt

---

## Projektkomplett checklista

### Kodbas
- [ ] Alla tasks implementerade
- [ ] Alla tests passerar
- [ ] Kodkvalitet godkänd
- [ ] Type hints överallt
- [ ] Docstrings överallt

### Dokumentation
- [ ] README.md uppdaterad om nödvändigt
- [ ] Edge cases dokumenterade
- [ ] Test-korpus dokumenterad

### Validering
- [ ] Pipeline fungerar end-to-end
- [ ] Validering fungerar korrekt
- [ ] Export genererar korrekt output
- [ ] Testat med flera fakturor

## Anteckningar

Använd detta avsnitt för att dokumentera:
- Upptäckta edge cases
- Beslut om avvikelser från planen
- Förbättringsförslag för framtida iterationer
