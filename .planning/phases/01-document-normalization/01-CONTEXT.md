# Phase 1: Document Normalization - Context

**Gathered:** 2025-01-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Process PDF invoices (searchable or scanned) and create stable document representation with full spatial traceability, basic Excel export, and CLI for batch processing. This phase establishes the foundation - stable document representation with full traceability before attempting field extraction.

</domain>

<decisions>
## Implementation Decisions

### CLI Interface Design

- **Command syntax:** Named flags: `invoice-parser --input input_dir --output output_dir`
- **Input format:** Supports both directory (process all PDFs) and file list (specific PDF files) - flexible
- **Output structure:** One consolidated Excel file for all invoices + separate review folders per invoice when needed (review folders created in Phase 3, but structure defined here)
- **Error handling:** Flag-based (`--fail-fast` vs default). Default: continue processing and collect errors, don't stop batch

### Excel Output Format

- **Column names:** Swedish (matches Swedish invoices, business/accounting usage, reduces cognitive friction)
  - Standard columns: Fakturanummer, Referenser, Företag, Fakturadatum, Beskrivning, Antal, Enhet, Á-pris, Rabatt, Summa, Hela summan, Status, LinesSum, Diff, InvoiceNoConfidence, TotalConfidence
- **Metadata repetition:** All columns repeated per row (each row is self-contained, easy to filter/sum/pivot, robust for further export)
- **File naming:** Timestamp-based: `invoices_YYYY-MM-DD_HH-MM-SS.xlsx` (unique, traceable, batch-friendly, no overwrite risk)
- **Review folder structure:** One review folder per invoice: `review/{invoice_filename}/` containing:
  - Original PDF
  - Metadata (JSON/CSV with page, bbox, text excerpt, status)
  - Clear isolation per invoice, easy manual review, future-proof for UI

### Error Handling

- **Corrupt PDFs:** Move to `errors/{original_filename}.pdf` and continue (default). Log error cause and stacktrace in error report. Batch should not stop, corrupt files easy to collect and fix.
- **OCR failures / very low confidence:** Mark as REVIEW and continue (default). Create review folder for invoice, set status = REVIEW (critical gate), include reason: OCR_FAILED or OCR_LOW_CONFIDENCE. OCR problems are exactly the type of uncertainty that should go to review, not "silently disappear".
- **Partial failures in batch:** Create Excel with successful ones, log failed ones (default). Excel contains only rows for successful documents (OK/PARTIAL/REVIEW). Failed documents listed in error report. Always get value from batch even if some files fail.
- **Error reporting:** Structured error file (JSON) + terminal output (default)
  - `errors/errors_YYYY-MM-DD_HH-MM-SS.json`
  - Plus short summary in terminal
  - JSON contains per file: filename, error_type (PDF_READ_ERROR, OCR_FAILED, etc.), message, stage (ingest/render/ocr/layout/extract/export), stacktrace (optional depending on verbosity), timestamp
  - Terminal not enough in batch; JSON enables follow-up and statistics
  - Note: `--fail-fast` exists as global flag. Default above applies when `--fail-fast` not used.

### Progress Reporting

- **Status output format:** Detailed: `[1/10] invoice1.pdf → OK (5 rader) | LinesSum=... Diff=...` (provides sufficient signal for quality - rows + diff - without being too verbose)
- **Progress indicator:** Counter only: `Processing 8/10...` (stable in all terminals/logs - progressbar can be messy in CI/log files)
- **Verbosity levels:** Standard as default + `--verbose` flag for debug. Normal mode should be easy to read, but debug must exist.
- **Final summary:** Detailed output with:
  - Total summary (OK/PARTIAL/REVIEW/failed)
  - List of failed (filename + reason)
  - Path/filename to Excel output
  - Path to errors JSON (if exists)
  - Quick to act on result without opening log files

**Default output during execution (example):**
```
Processing 3/25...
[3/25] faktura_123.pdf → REVIEW (InvoiceNoConfidence=0.62, TotalConfidence=0.91) | Review saved: review/faktura_123/
...
Done: 25 processed. OK=18, PARTIAL=4, REVIEW=2, failed=1. Excel: invoices_2026-01-17_14-30-00.xlsx. Errors: errors/errors_2026-01-17_14-30-00.json
```

### Claude's Discretion

- Exact error message wording
- Internal file structure organization
- Implementation details for progress tracking
- Verbose mode output format details

</decisions>

<specifics>
## Specific Ideas

- Error handling should ensure batch never silently fails - always produce partial results
- Review folders structure designed for future UI integration (clear isolation per invoice)
- Swedish column names chosen for domain alignment (Swedish invoices, business users)
- Timestamp-based naming prevents overwrites and enables batch tracking

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---
*Phase: 01-document-normalization*
*Context gathered: 2025-01-27*
