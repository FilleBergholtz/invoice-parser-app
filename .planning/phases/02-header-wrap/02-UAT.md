---
status: complete
phase: 02-header-wrap
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md, 02-04-SUMMARY.md, 02-05-SUMMARY.md]
started: 2026-01-17T16:30:00Z
updated: 2026-01-17T16:35:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Extract invoice number with confidence scoring
expected: When processing a PDF invoice, the system extracts invoice number from header section. If confidence ≥ 0.95, invoice number is stored. If confidence < 0.95 or multiple candidates are tied (within 0.03), value is set to None and status is REVIEW. Invoice number extraction works with keywords like "Fakturanummer", "Invoice number", "Nr" followed by alphanumeric values.
result: skipped
reason: No test data available (requires sample PDF invoices)

### 2. Extract total amount with confidence scoring and validation
expected: When processing a PDF invoice, the system extracts total amount from footer section using keywords like "Att betala", "Totalt", "Total". System validates total against sum of line item amounts with ±1 SEK tolerance. If confidence ≥ 0.95 and validation passes, total is stored. Otherwise, status is REVIEW. Mathematical validation provides strong signal (0.35 weight) for confidence scoring.
result: skipped
reason: No test data available (requires sample PDF invoices)

### 3. Extract vendor name and invoice date
expected: When processing a PDF invoice, the system extracts vendor/company name from header (company name only, not address). System extracts invoice date and normalizes to ISO format (YYYY-MM-DD). Both vendor and date can be None if not found (no hard gate). Date parsing supports Swedish formats: DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY.
result: skipped
reason: No test data available (requires sample PDF invoices)

### 4. Hard gate evaluation (OK vs REVIEW status)
expected: System evaluates hard gate: invoice_number_confidence ≥ 0.95 AND total_confidence ≥ 0.95. If both pass, invoice status is OK. If either fails, status is REVIEW. Hard gate prevents exporting uncertain data as OK, ensuring 100% accuracy for approved invoices.
result: skipped
reason: No test data available (requires sample PDF invoices)

### 5. Traceability evidence storage
expected: For invoice number and total amount, system stores traceability evidence: page number, bounding box (bbox), row index, text excerpt (max 120 chars), and token information. Evidence is stored in Traceability objects linked to InvoiceHeader. Evidence enables verification and trust by linking extracted values back to source PDF locations.
result: skipped
reason: No test data available (requires sample PDF invoices)

### 6. Wrap detection for multi-line items
expected: System detects when invoice line item descriptions wrap across multiple rows. Wrap detection uses spatial X-position tolerance (±2% of page width). Max 3 wraps per line item. Wrapped rows are grouped to same InvoiceLine, description is consolidated with space separator (Excel-friendly). Wrapped rows are included in InvoiceLine.rows for full traceability.
result: skipped
reason: No test data available (requires sample PDF invoices)

### 7. Integration in CLI pipeline
expected: When running `invoice-parser --input <pdf> --output <dir>`, the CLI processes invoice, extracts header fields (invoice number, vendor, date), extracts total amount from footer, performs wrap detection on line items, stores traceability, and outputs results. All Phase 2 features are integrated and work together in the pipeline.
result: skipped
reason: No test data available (requires sample PDF invoices)

## Summary

total: 7
passed: 0
issues: 0
pending: 0
skipped: 7

## Gaps

[none yet]
