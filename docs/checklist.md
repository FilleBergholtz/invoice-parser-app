# Implementeringschecklista

## Översikt

Denna checklista används för att spåra framsteg för varje task-implementation. Markera avklarade punkter när du implementerar enligt `docs/tasks.md`.

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

### [T14] Validation → Export (med status)
- [ ] CSV med metadata fungerar
- [ ] Header-rad inkluderas
- [ ] Footer med summor inkluderas
- [ ] Valideringsstatus inkluderas
- [ ] Unit tests passerar
- [ ] Fullständig pipeline testat
- [ ] **Fas 3 komplett**

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
