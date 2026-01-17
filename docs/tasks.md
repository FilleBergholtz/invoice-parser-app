# Atomiska Tasks

## Översikt

Varje task mappar 1:1 till en pipeline-övergång enligt `specs/invoice_pipeline_v1.md`. Tasks implementeras sekventiellt enligt roadmap-faserna i `docs/roadmap.md`.

## Task-format

Varje task följer strikt format:
- **[T#] Titel**
- **Input**: Input-typ från pipeline
- **Output**: Output-typ till pipeline
- **Files**: Filer som ska skapas/modifieras
- **DoD**: Definition of Done (kriterier för att task är klar)

## Fas 1: Vertical Slice Tasks

### [T1] PDF → Document

**Input**: Filväg till PDF-fil (str)

**Output**: Document-objekt

**Files**: 
- `src/document.py` (Document-klass)
- `src/reader.py` (PDF-läsning)
- `tests/test_document.py` (Unit tests)

**DoD**:
- [ ] Document-klass implementerad enligt `docs/02_data-model.md`
- [ ] Kan läsa PDF-fil och skapa Document
- [ ] Metadata (filename, filepath, page_count) extraheras korrekt
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`

---

### [T2] Document → Page

**Input**: Document-objekt

**Output**: List[Page]

**Files**:
- `src/page.py` (Page-klass)
- `src/reader.py` (Page-extraktion)
- `tests/test_page.py` (Unit tests)

**DoD**:
- [ ] Page-klass implementerad enligt `docs/02_data-model.md`
- [ ] Kan extrahera alla sidor från Document
- [ ] Sidnumrering börjar på 1
- [ ] Varje Page har korrekt width/height
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`

---

### [T3] Page → Tokens

**Input**: Page-objekt

**Output**: List[Token]

**Files**:
- `src/token.py` (Token-klass)
- `src/tokenizer.py` (Tokenisering med pdfplumber eller OCR)
- `tests/test_tokenizer.py` (Unit tests)

**DoD**:
- [ ] Token-klass implementerad enligt `docs/02_data-model.md`
- [ ] Kan extrahera tokens med positioner (x, y, width, height)
- [ ] Alla tokens har text och spatial information
- [ ] Token-ordning bevaras
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`

---

### [T4] Tokens → Rows

**Input**: List[Token]

**Output**: List[Row]

**Files**:
- `src/row.py` (Row-klass)
- `src/row_grouping.py` (Token-gruppering till rader)
- `tests/test_row_grouping.py` (Unit tests)

**DoD**:
- [ ] Row-klass implementerad enligt `docs/02_data-model.md`
- [ ] Kan gruppera tokens i rader baserat på Y-position
- [ ] Tolerans för Y-position fungerar korrekt
- [ ] Radordning bevaras (top-to-bottom)
- [ ] Regel: "rad med belopp = produktrad" dokumenterad
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`

---

### [T5] Rows → Segments

**Input**: List[Row]

**Output**: List[Segment]

**Files**:
- `src/segment.py` (Segment-klass)
- `src/segment_identification.py` (Segment-identifiering)
- `tests/test_segment_identification.py` (Unit tests)

**DoD**:
- [ ] Segment-klass implementerad enligt `docs/02_data-model.md`
- [ ] Kan identifiera header, items, footer baserat på position
- [ ] Segment-typer är korrekt satta
- [ ] Header-område: övre 20-30% identifieras
- [ ] Footer-område: nedre del identifieras
- [ ] Items-område: mittdel identifieras
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`

---

### [T6] Segments → InvoiceLine

**Input**: Segment (typ "items") med List[Row]

**Output**: List[InvoiceLine]

**Files**:
- `src/invoice_line.py` (InvoiceLine-klass)
- `src/invoice_line_parser.py` (Produktrad-parsing)
- `tests/test_invoice_line_parser.py` (Unit tests)

**DoD**:
- [ ] InvoiceLine-klass implementerad enligt `docs/02_data-model.md`
- [ ] Kan identifiera produktrader från items-segment
- [ ] Regel: "rad med belopp = produktrad" implementerad
- [ ] Beskrivning, kvantitet, pris, total extraheras
- [ ] Enklaste implementation (ingen wrap-hantering ännu)
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`

---

### [T7] InvoiceLine → Export (CSV)

**Input**: InvoiceSpecification (placeholder), List[InvoiceLine]

**Output**: CSV-fil

**Files**:
- `src/export.py` (CSV-export)
- `src/main.py` (CLI-entry point)
- `tests/test_export.py` (Unit tests)

**DoD**:
- [ ] Kan exportera InvoiceLine till CSV
- [ ] CSV innehåller kolumner: description, quantity, unit_price, total_amount
- [ ] UTF-8 kodning fungerar korrekt
- [ ] CLI-entry point fungerar: `python -m src.main input.pdf output.csv`
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`
- [ ] **Fas 1 komplett**: End-to-end pipeline fungerar

---

## Fas 2: Header + Wrap Tasks

### [T8] Segments → Zoner

**Input**: List[Segment]

**Output**: List[Zone]

**Files**:
- `src/zone.py` (Zone-klass)
- `src/zone_identification.py` (Spatial zonering)
- `tests/test_zone_identification.py` (Unit tests)

**DoD**:
- [ ] Zone-klass implementerad enligt `docs/02_data-model.md`
- [ ] Kan skapa spatiala zoner baserat på position
- [ ] Olika zon-typer identifieras (header, date, amount, items)
- [ ] Zoner hjälper till att identifiera kontext
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`

---

### [T9] Zoner → Header

**Input**: List[Zone], Segment (typ "header")

**Output**: InvoiceHeader

**Files**:
- `src/invoice_header.py` (InvoiceHeader-klass)
- `src/header_identification.py` (Header-scoring och identifiering)
- `tests/test_header_identification.py` (Unit tests)

**DoD**:
- [ ] InvoiceHeader-klass implementerad enligt `docs/02_data-model.md`
- [ ] Header-scoring fungerar baserat på position och nyckelord
- [ ] Konfidenspoäng beräknas korrekt
- [ ] Header-segment identifieras korrekt
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`

---

### [T10] Header → Specifikation

**Input**: InvoiceHeader

**Output**: InvoiceSpecification

**Files**:
- `src/invoice_specification.py` (InvoiceSpecification-klass)
- `src/header_parser.py` (Metadata-extraktion från header)
- `tests/test_header_parser.py` (Unit tests)

**DoD**:
- [ ] InvoiceSpecification-klass implementerad enligt `docs/02_data-model.md`
- [ ] Fakturanummer extraheras (via nyckelord + värde)
- [ ] Datum extraheras (stödjer flera datumformat)
- [ ] Leverantörsnamn extraheras
- [ ] Kundnamn extraheras (om tillgängligt)
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`

---

### [T11] Förbättring: Fortsättningsrader (Wrap)

**Input**: List[Row] (med wraps), List[InvoiceLine]

**Output**: List[InvoiceLine] (med kopplade wraps)

**Files**:
- `src/invoice_line_parser.py` (Uppdaterad wrap-hantering)
- `tests/test_invoice_line_wrap.py` (Unit tests)

**DoD**:
- [ ] Fortsättningsrader identifieras korrekt
- [ ] Wrapped text kopplas till rätt InvoiceLine
- [ ] Beskrivning konsolideras från alla rader i InvoiceLine
- [ ] Belopp finns bara på sista raden i wrapped text
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf` (om den har wraps)
- [ ] **Fas 2 komplett**: Header + wrap fungerar

---

## Fas 3: Validering Tasks

### [T12] InvoiceLine → Reconciliation

**Input**: List[InvoiceLine], Segment (typ "footer")

**Output**: Reconciliation

**Files**:
- `src/reconciliation.py` (Reconciliation-klass)
- `src/reconciliation_calculator.py` (Summa-beräkning)
- `tests/test_reconciliation.py` (Unit tests)

**DoD**:
- [ ] Reconciliation-klass implementerad enligt `docs/02_data-model.md`
- [ ] Beräknar subtotal från InvoiceLine-totals
- [ ] Extraherar subtotal/tax/total från footer
- [ ] Beräknar skillnader mellan beräknade och extraherade summor
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf`

---

### [T13] Reconciliation → Validation

**Input**: Reconciliation

**Output**: Validation

**Files**:
- `src/validation.py` (Validation-klass)
- `src/validator.py` (Valideringsregler enligt `docs/05_validation.md`)
- `tests/test_validation.py` (Unit tests)

**DoD**:
- [ ] Validation-klass implementerad enligt `docs/02_data-model.md`
- [ ] Status sätts korrekt: OK/Warning/Review
- [ ] Valideringsregler implementerade enligt `docs/05_validation.md`
- [ ] Meddelanden genereras för fel/varningar
- [ ] Saknade fält identifieras
- [ ] Unit tests passerar
- [ ] Testat med `sample_invoice_1.pdf` och edge cases

---

### [T14] Validation → Export (med status)

**Input**: InvoiceSpecification, List[InvoiceLine], Reconciliation, Validation

**Output**: CSV-fil (med metadata och valideringsstatus)

**Files**:
- `src/export.py` (Uppdaterad export med metadata)
- `src/main.py` (Uppdaterad CLI)
- `tests/test_export.py` (Uppdaterade tests)

**DoD**:
- [ ] CSV inkluderar header-rad med metadata (fakturanummer, datum, leverantör)
- [ ] CSV inkluderar produktrader
- [ ] CSV inkluderar footer med summor
- [ ] Valideringsstatus inkluderas i export
- [ ] Excel-export fungerar (valfritt)
- [ ] Unit tests passerar
- [ ] **Fas 3 komplett**: Fullständig pipeline med validering

---

## Nästa task

Börja med **[T1] PDF → Document** enligt roadmap Fas 1.

## Implementation-regler

- Implementera EN task i taget
- Markera DoD-kriterier innan du går vidare
- Testa varje task med `sample_invoice_1.pdf`
- Följ datamodellen i `docs/02_data-model.md` exakt
- Referera till `docs/checklist.md` för varje implementation
