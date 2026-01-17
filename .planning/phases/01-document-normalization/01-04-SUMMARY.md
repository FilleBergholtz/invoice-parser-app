---
phase: 01-document-normalization
plan: 04
subsystem: line-item-extraction
tags: [layout-driven, regex, numeric-parsing]

# Dependency graph
requires:
  - phase: 01-03
    provides: Row and Segment models, row grouping, segment identification
provides:
  - InvoiceLine model
  - Line item parser (layout-driven, extracts from items segment)
  - Multi-page support (combine items segments across pages)
affects: [01-05 - Excel export needs InvoiceLines]

# Tech tracking
tech-stack:
  added: []
  patterns: [Layout-driven extraction: tokens→rows→segments→InvoiceLines, regex for numeric parsing]

key-files:
  created:
    - src/models/invoice_line.py
    - src/pipeline/invoice_line_parser.py
    - tests/test_invoice_line_parser.py
  modified: []

key-decisions:
  - "Rule: 'rad med belopp = produktrad' - rows with amount become InvoiceLines"
  - "Layout-driven approach: Use spatial information (token positions) not table detection"
  - "Heuristic: Rightmost numeric before amount = unit_price, leftmost numeric = quantity"

patterns-established:
  - "Line item extraction: Iterate rows → find amount → extract fields using spatial layout"
  - "Numeric parsing: Handle Swedish formats (comma decimal separator), currency symbols"

# Metrics
duration: ~15min
completed: 2026-01-17
---

# Phase 01: Document Normalization - Plan 04 Summary

**Line item extraction implemented: layout-driven parser extracting InvoiceLines from items segment using 'rad med belopp = produktrad' rule**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-01-17 14:28
- **Completed:** 2026-01-17 14:43
- **Tasks:** 3 completed
- **Files modified:** 3 created

## Accomplishments

- InvoiceLine data model created with full traceability (rows is KÄLLSANING)
- Line item parser implementing "rad med belopp = produktrad" rule
- Layout-driven extraction using spatial information (token positions, column alignment)
- Unit tests created for line item extraction

## Task Commits

Each task was committed atomically:

1. **Task 1: Create InvoiceLine data model** - Current commit (feat)
2. **Task 2: Implement line item parser** - Current commit (feat)
3. **Task 3: Write unit tests** - Current commit (test)

## Files Created/Modified

- `src/models/invoice_line.py` - InvoiceLine model with rows (KÄLLSANING), description, quantity, unit, unit_price, total_amount, line_number
- `src/pipeline/invoice_line_parser.py` - Line item extraction from items segment (extract_invoice_lines)
- `tests/test_invoice_line_parser.py` - Unit tests for line item extraction

## Decisions Made

- **Layout-driven extraction:** Used spatial information (token positions, column alignment) to identify fields, not table detection. pdfplumber table detection could be helper, but not single point of failure.

- **Amount identification:** Rule "rad med belopp = produktrad" - rows containing numeric amounts become InvoiceLines. Search from right-to-left for amount (usually rightmost numeric column).

- **Field extraction heuristics:**
  - Description: Leftmost text before amount column
  - Quantity: Leftmost numeric (if integer-like)
  - Unit: Common unit strings (st, kg, h, m²) near quantity
  - Unit price: Rightmost numeric before amount
  - Total amount: Rightmost numeric (required)

- **Swedish number format:** Handle comma as decimal separator (e.g., "500,50") in addition to dot format.

- **Phase 1 scope:** In Phase 1, InvoiceLine.rows typically contains one Row (wrapped text handling comes in Phase 2).

## Deviations from Plan

None - plan executed exactly as written. All tasks completed as specified.

## Verification Status

- ✅ InvoiceLine model matches docs/02_data-model.md specification
- ✅ Line item parser uses layout-driven approach (not table-extractor-driven)
- ✅ Product rows identified by amount (rule: "rad med belopp = produktrad")
- ✅ Fields extracted: description, quantity, unit, unit_price, total_amount
- ✅ Full traceability: InvoiceLine→Row→Token→Page
- ✅ Unit tests created (basic structure tests, integration tests require actual PDFs)

## Next Steps

Plan 01-05 depends on this plan - will use InvoiceLines for Excel export.

---

*Plan completed: 2026-01-17*
