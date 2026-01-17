# Invoice Parser App

## Arbetsregler för Claude Code

### Allmänna regler
- Följ EXAKT den strukturerade planen i `docs/roadmap.md` och `docs/tasks.md`
- Implementera EN task i taget enligt `docs/tasks.md` specifikation
- Använd datamodellen i `docs/02_data-model.md` - ändra INTE fältnamn eller strukturer
- Testa varje pipeline-steg med test-korpusen i `tests/fixtures/pdfs/`
- Validera mot specifikationerna i `specs/invoice_pipeline_v1.md`
- Följ heuristikerna i `docs/04_heuristics.md` för parsing-logik
- Använd valideringsreglerna i `docs/05_validation.md` för kvalitetskontroll

### Implementeringsordning
1. Följ roadmap-faserna i ordning: Vertical slice → Header + wrap → Validering
2. Implementera tasks sekventiellt enligt `docs/tasks.md`
3. Markera DoD (Definition of Done) innan du går vidare till nästa task
4. Referera till checklist i `docs/checklist.md` för varje implementation

### Kodstandard
- Python 3.11+
- Type hints för alla funktioner
- Docstrings för alla klasser och funktioner
- Unit tests för varje pipeline-steg
- Följ PEP 8 style guide

### Viktigt
- Ändra INTE fältnamn i datamodellen utan att först diskutera med användaren
- Implementera INTE flera tasks parallellt - en i taget
- Testa varje steg med sample_invoice_1.pdf innan du går vidare
- Uppdatera test-korpus dokumentation om nya edge cases upptäcks

## Projektbeskrivning

Invoice Parser App är ett Python-projekt som extraherar strukturerad data från faktura-PDF:er. Projektet använder en 12-stegs pipeline för att transformera PDF:er till strukturerad tabell-data (CSV/Excel).

### Pipeline-översikt

1. **PDF → Document**: Läs PDF-fil
2. **Document → Page**: Extrahera sidor
3. **Page → Tokens**: OCR/tokenisering med positioner
4. **Tokens → Rows**: Gruppera tokens i rader
5. **Rows → Segments**: Identifiera logiska segment (header, items, footer)
6. **Segments → Zoner**: Spatial zonering för kontext
7. **Zoner → Header**: Identifiera fakturahuvud
8. **Header → Specifikation**: Extrahera metadata (datum, nummer, leverantör)
9. **Segments → InvoiceLine**: Identifiera produktrader
10. **InvoiceLine → Reconciliation**: Beräkna totalsummor och validera
11. **Reconciliation → Validation**: Kvalitetskontroll (OK/Warning/Review)
12. **Validation → Export**: Generera slutlig tabell (CSV/Excel)

### Teknisk stack
- Python 3.11+
- PDF parsing (PyPDF2/pdfplumber)
- OCR (pytesseract eller pdfplumber)
- Data processing (pandas)
- Testing (pytest)

## Starta GSD (Guided Software Development)

1. **Läs planen**: Börja med `docs/roadmap.md` för att förstå faser
2. **Välj task**: Se `docs/tasks.md` för aktuell task
3. **Implementera**: Följ specifikationen i `specs/invoice_pipeline_v1.md`
4. **Testa**: Använd test-korpusen i `tests/fixtures/pdfs/`
5. **Validera**: Kontrollera mot `docs/05_validation.md`
6. **Checklist**: Markera avklarade delar i `docs/checklist.md`

### Första steg
Börja med första task i `docs/tasks.md` som är märkt som nästa i roadmap-fasen "Vertical slice".

## Projektstruktur

```
invoice-parser-app/
├── README.md                    # Denna fil
├── pyproject.toml              # Python-projektkonfiguration
├── specs/
│   └── invoice_pipeline_v1.md  # Pipeline-specifikation (12 steg)
├── docs/
│   ├── roadmap.md              # Implementeringsfaser
│   ├── tasks.md                # Atomiska tasks
│   ├── checklist.md            # Implementeringschecklista
│   ├── 02_data-model.md        # Datamodell
│   ├── 04_heuristics.md        # Parsing-heuristiker
│   ├── 05_validation.md        # Valideringsregler
│   └── 06_test-corpus.md       # Test-korpus beskrivning
├── src/                        # Python-källkod
└── tests/
    └── fixtures/
        └── pdfs/               # Test-PDF:er
```

## Installation

```bash
pip install -r requirements.txt
```

## Användning

```bash
python -m src.main input.pdf output.csv
```
