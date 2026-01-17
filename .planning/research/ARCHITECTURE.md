# Architecture Research

**Domain:** Invoice parsing system (PDF → structured data pipeline)
**Researched:** 2025-01-27
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Input Layer                               │
├─────────────────────────────────────────────────────────────┤
│  PDF Detection → Text Layer Check → Route to Pipeline       │
│  (searchable PDF) or (scanned → OCR pipeline)               │
├─────────────────────────────────────────────────────────────┤
│                    Extraction Layer                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Layout       │  │ Field        │  │ Line Item    │      │
│  │ Analysis     │→ │ Extraction   │→ │ Extraction   │      │
│  │ (spatial)    │  │ (header)     │  │ (table)      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                    Validation Layer                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Reconciliation + Status Assignment                  │    │
│  │  (sum validation, confidence scoring, hard gates)    │    │
│  └─────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│                    Output Layer                              │
├─────────────────────────────────────────────────────────────┤
│  Excel Export (with status, traceability columns)            │
│  Review Reports (PDF + metadata)                             │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| PDF Reader | Detect PDF type, extract text/spatial info | pdfplumber for searchable PDFs, pdf2image+pytesseract for scanned |
| Layout Analyzer | Understand document structure (header/footer/body, reading order) | pdfplumber spatial analysis + heuristics, OCR bbox grouping |
| Field Extractor | Identify invoice number, date, vendor, totals from header | Layout-aware extraction with scoring (position, keywords, patterns) |
| Table Parser | Extract line items from table structures | pdfplumber table detection or OCR-based table reconstruction |
| Validator | Check mathematical consistency, assign confidence | Sum reconciliation, tolerance checks (±1 SEK), confidence scoring |
| Status Assigner | Determine OK/PARTIAL/REVIEW based on validation | Hard gate logic: both invoice number and total must pass or REVIEW |
| Exporter | Generate Excel with structured data + status columns | pandas DataFrame → openpyxl Excel writer |
| Traceability Manager | Store spatial references (page, bbox) for critical fields | Metadata storage linked to extracted values |

## Recommended Project Structure

```
src/
├── pipeline/           # Core pipeline stages
│   ├── __init__.py
│   ├── reader.py       # PDF input detection & routing
│   ├── layout.py       # Layout analysis (segments, zones)
│   ├── extraction.py   # Field extraction (invoice number, total)
│   ├── tables.py       # Line item extraction
│   └── validation.py   # Reconciliation & status assignment
├── models/             # Data models
│   ├── __init__.py
│   ├── document.py     # Document, Page, Token models
│   ├── invoice.py      # InvoiceHeader, InvoiceLine models
│   └── validation.py   # Validation, Status models
├── export/             # Output generation
│   ├── __init__.py
│   ├── excel.py        # Excel export with status columns
│   └── review.py       # Review report generation
├── utils/              # Utilities
│   ├── __init__.py
│   ├── spatial.py      # Spatial operations (bbox, grouping)
│   └── traceability.py # Traceability metadata management
└── cli.py              # Command-line interface

tests/
├── fixtures/
│   └── pdfs/           # Test invoice PDFs
├── unit/               # Unit tests per module
└── integration/        # End-to-end pipeline tests
```

### Structure Rationale

- **pipeline/:** Modular stages enable testing each step independently, matches 12-step specification
- **models/:** Centralized data structures ensure consistency across pipeline stages
- **export/:** Separated output logic allows adding formats (JSON, CSV) without touching pipeline
- **utils/:** Reusable spatial/traceability logic shared across extraction stages

## Architectural Patterns

### Pattern 1: Pipeline Architecture

**What:** Sequential transformation stages (PDF → Document → Page → Tokens → Rows → ... → Export)
**When to use:** Data transformation pipelines with clear stages
**Trade-offs:** 
- ✅ Pros: Clear separation of concerns, testable stages, easy to debug
- ⚠️ Cons: Can be verbose, requires careful data model design

**Example:**
```python
# Each stage transforms input → output
document = reader.read_pdf("invoice.pdf")
pages = reader.extract_pages(document)
tokens = layout.tokenize_pages(pages)
rows = layout.group_tokens_to_rows(tokens)
segments = layout.identify_segments(rows)
header = extraction.extract_header(segments)
lines = extraction.extract_line_items(segments)
validation_result = validation.validate(header, lines)
export.export_excel(validation_result)
```

### Pattern 2: Hard Gate Validation

**What:** Strict validation gates that prevent false positives (100% or REVIEW)
**When to use:** Critical data accuracy requirements
**Trade-offs:**
- ✅ Pros: Guarantees correctness for approved outputs, builds trust
- ⚠️ Cons: Higher REVIEW rate, requires manual verification workflow

**Example:**
```python
def assign_status(invoice_no_conf: float, total_conf: float, sum_diff: float) -> Status:
    # Hard gate: both critical fields must pass
    if invoice_no_conf < 0.95 or total_conf < 0.95:
        return Status.REVIEW
    # Validation gate: sum must match within tolerance
    if abs(sum_diff) > 1.00:  # ±1 SEK tolerance
        return Status.PARTIAL if invoice_no_conf >= 0.95 else Status.REVIEW
    return Status.OK
```

### Pattern 3: Spatial Traceability

**What:** Store bounding boxes and page references for extracted values
**When to use:** Need to verify or debug extracted data
**Trade-offs:**
- ✅ Pros: Enables verification, clickable links to PDF source
- ⚠️ Cons: Increases memory/storage, adds complexity to data models

**Example:**
```python
@dataclass
class ExtractedField:
    value: str
    confidence: float
    traceability: TraceabilityInfo  # page, bbox, source_text

@dataclass
class TraceabilityInfo:
    page_number: int
    bbox: BoundingBox  # x, y, width, height
    source_text: str  # Original text snippet
```

## Data Flow

### Request Flow

```
PDF File
    ↓
[PDF Reader] → Detect type (searchable/scanned)
    ↓
[Layout Analyzer] → Extract spatial text (tokens with bbox)
    ↓
[Field Extractor] → Invoice number, total (with confidence)
    ↓
[Table Parser] → Line items
    ↓
[Validator] → Reconciliation (sum check)
    ↓
[Status Assigner] → OK/PARTIAL/REVIEW
    ↓
[Exporter] → Excel + Review Reports
```

### State Management

For batch processing, each invoice is processed independently:
- No shared state between invoices
- Each invoice has isolated pipeline execution
- Results aggregated at export stage

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 invoices/week | Single-threaded pipeline, sequential processing |
| 100-1000 invoices/week | Batch processing with parallel workers (multiprocessing) |
| 1000+ invoices/week | Queue-based system (Redis/Celery), distributed workers |

### Scaling Priorities

1. **First bottleneck:** PDF processing (I/O bound) → parallel workers
2. **Second bottleneck:** OCR processing (CPU bound) → dedicated OCR workers, caching

## Anti-Patterns

### Anti-Pattern 1: Template-Based Parsing

**What people do:** Create regex/template for each vendor
**Why it's wrong:** Breaks when vendor changes format, maintenance nightmare
**Do this instead:** Layout analysis + semantic rules (template-free)

### Anti-Pattern 2: Single-Pass Extraction

**What people do:** Extract all fields in one pass without validation
**Why it's wrong:** No feedback loop, errors propagate
**Do this instead:** Extract → Validate → Re-extract low-confidence fields → Final validation

### Anti-Pattern 3: Silent Failure on Low Confidence

**What people do:** Return best guess even when uncertain
**Why it's wrong:** Violates 100% accuracy requirement, erodes trust
**Do this instead:** Hard gates - REVIEW status for uncertain extractions

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Tesseract OCR | CLI via pytesseract wrapper | Requires system installation, not pure Python |
| File system | Direct file I/O | Batch processing reads from directory, writes to output directory |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| pipeline stages ↔ models | Direct Python objects | Data models passed between stages |
| extraction ↔ validation | ValidationResult objects | Structured validation output |

## Sources

- WebSearch 2025 — "invoice parsing architecture pipeline OCR layout analysis 2025 design patterns"
- Academic papers: Multi-stage document parsing pipelines
- Industry patterns: Commercial invoice parsing architecture
- Project specification: 12-step pipeline in specs/invoice_pipeline_v1.md

---
*Architecture research for: Invoice Parser App (Swedish invoices, hard gates, traceability)*
*Researched: 2025-01-27*
