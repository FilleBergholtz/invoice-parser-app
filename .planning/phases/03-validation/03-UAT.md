---
status: complete
phase: 03-validation
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md]
started: 2026-01-17
updated: 2026-01-17
---

## Current Test

[testing complete]

## Tests

### 1. Validation Status Assignment (OK/PARTIAL/REVIEW)
expected: |
  System correctly assigns status based on hard gates and mathematical validation:
  - Invoice with high confidence (≥0.95) on both invoice number and total, and line items sum correctly (diff ≤ ±1 SEK) → Status = OK
  - Invoice with high confidence on header fields but line items don't sum correctly (diff > ±1 SEK) → Status = PARTIAL
  - Invoice with low confidence (<0.95) on invoice number or total → Status = REVIEW
result: skipped
reason: No test data available (requires sample invoice PDF files)

### 2. Excel Control Columns - Presence and Format
expected: |
  Excel export includes control columns after existing columns:
  - Columns present: Status, Radsumma, Avvikelse, Fakturanummer-konfidens, Totalsumma-konfidens
  - Status column shows "OK", "PARTIAL", or "REVIEW" (text)
  - Radsumma and Avvikelse formatted as currency (2 decimals)
  - Confidence columns formatted as percentage (e.g., 95% instead of 0.95)
  - Avvikelse shows "N/A" when total amount is None (not extracted)
result: skipped
reason: No test data available (requires sample invoice PDF files)

### 3. Excel Control Columns - Values Per Invoice
expected: |
  Control column values repeat correctly for all rows of same invoice:
  - When processing batch with multiple invoices, each invoice's rows have same Status, Radsumma, Avvikelse, and confidence values
  - Validation data is correctly grouped per invoice (not mixed between invoices)
result: skipped
reason: No test data available (requires sample invoice PDF files)

### 4. Review Reports - Creation for REVIEW Status Only
expected: |
  Review reports are created only for invoices with REVIEW status:
  - Invoices with OK or PARTIAL status do NOT get review reports
  - Only REVIEW status invoices get review folder with PDF and metadata.json
result: skipped
reason: No test data available (requires sample invoice PDF files)

### 5. Review Reports - Folder Structure
expected: |
  Review folder structure is correct:
  - Folder created at: output_dir/review/{invoice_filename}/
  - Folder contains: {invoice_filename}.pdf (copy of original) and metadata.json
  - Folder name matches PDF filename (without extension)
result: skipped
reason: No test data available (requires sample invoice PDF files)

### 6. Review Reports - Metadata JSON Content
expected: |
  metadata.json in review folder contains complete validation data:
  - InvoiceHeader data (invoice_number, total_amount, confidence scores, supplier_name, invoice_date)
  - Traceability evidence for invoice_number and total (page_number, bbox, text_excerpt, tokens)
  - Validation results (status, lines_sum, diff, errors, warnings, line_count)
  - Timestamp
result: skipped
reason: No test data available (requires sample invoice PDF files)

### 7. Batch Processing - Status Output Per Invoice
expected: |
  CLI shows detailed status per invoice during batch processing:
  - Format: [N/total] filename.pdf → STATUS (additional info)
  - For REVIEW: Shows confidence scores (e.g., "InvoiceNoConfidence=0.62, TotalConfidence=0.91")
  - For PARTIAL: Shows diff amount (e.g., "Diff=15.50 SEK")
  - Shows line count: "(X rader)"
result: skipped
reason: No test data available (requires sample invoice PDF files)

### 8. Batch Processing - Final Summary
expected: |
  Final summary after batch processing shows validation statistics:
  - Format: "Done: N processed. OK=X, PARTIAL=Y, REVIEW=Z, failed=W."
  - If review reports created: "Review reports: Z invoice(s) in review/ folder"
  - Shows Excel output path: "Excel: path/to/invoices_TIMESTAMP.xlsx"
  - Shows errors path if errors occurred: "Errors: path/to/errors_TIMESTAMP.json"
result: skipped
reason: No test data available (requires sample invoice PDF files)

### 9. Mathematical Validation - Lines Sum Calculation
expected: |
  System calculates lines_sum correctly:
  - lines_sum = SUM of all InvoiceLine.total_amount values
  - Calculated even when total_amount is None (shows what we extracted)
result: skipped
reason: No test data available (requires sample invoice PDF files)

### 10. Mathematical Validation - Diff Calculation
expected: |
  System calculates diff correctly (signed difference):
  - diff = total_amount - lines_sum (can be negative if lines_sum > total_amount)
  - Shows exact difference, not absolute value
  - diff = "N/A" in Excel when total_amount is None
result: skipped
reason: No test data available (requires sample invoice PDF files)

## Summary

total: 10
passed: 0
issues: 0
pending: 0
skipped: 10

## Gaps

[none yet]
