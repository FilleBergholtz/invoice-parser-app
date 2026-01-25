# Codebase Map: Architecture

**Project:** EPG PDF Extraherare  
**Last updated:** 2026-01-25  
**Source:** map-codebase, refreshed by gsd-codebase-mapper

## High-Level Overview

The app extracts structured invoice data from Swedish PDFs: invoice number, totals, line items, dates. It combines **pdfplumber** and **OCR (Tesseract)** with optional **AI fallback** and a **learning system** that uses user corrections. Output is Excel and review packages; the GUI runs the engine as a subprocess and offers manual validation (candidate selection, corrections).

## Main Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  Entry points: run_gui.py (PySide6) / run_engine.py (CLI)        │
├─────────────────────────────────────────────────────────────────┤
│  UI: main_window, pdf_viewer, candidate_selector, engine_runner  │
├─────────────────────────────────────────────────────────────────┤
│  CLI orchestration: main.py (routing, compare, AI, Excel, run_summary) │
├─────────────────────────────────────────────────────────────────┤
│  Pipeline: reader → tokenizer → segments → header/footer →       │
│            validation → (optional AI fallback, optional compare) │
├─────────────────────────────────────────────────────────────────┤
│  Models: Document, Page, Token, Row, Segment, InvoiceHeader,     │
│          InvoiceLine, ValidationResult, VirtualInvoiceResult     │
├─────────────────────────────────────────────────────────────────┤
│  Supporting: ai/, learning/, export/, review/, quality/, config  │
└─────────────────────────────────────────────────────────────────┘
```

## Flow (Per Invoice)

1. **PDF read** (`reader.read_pdf`) → `Document` with `Page`s.
2. **Routing** (`pdf_detection.route_extraction_path`) → "pdfplumber" or "ocr".
3. **Boundaries** (`invoice_boundary_detection.detect_invoice_boundaries`) → `(page_start, page_end)` per virtual invoice.
4. **Per virtual invoice** (`process_virtual_invoice` in main.py):
   - **Tokens:** pdfplumber or OCR (`tokenizer`, `ocr_abstraction`).
   - **Rows / segments:** `row_grouping`, `segment_identification`, `wrap_detection`.
   - **Header / footer:** `header_extractor`, `footer_extractor` (totals, candidates, traceability).
   - **Validation:** `validation.validate_invoice` → status OK/PARTIAL/REVIEW/FAILED.
   - **AI fallback:** If confidence below threshold and AI enabled, `ai/fallback` enriches header/lines/total.
   - **Compare mode:** If enabled, run both pdfplumber and OCR, choose best (e.g. by confidence/text quality), set `extraction_source` / `extraction_detail.method_used`.
5. **Output:** Excel (consolidated + per-invoice in review), run_summary.json, review packages, optional artifacts.

## Key Design Choices

- **Single pipeline, two text sources:** One pipeline logic; tokenizer uses either pdfplumber or OCR. Compare mode runs both and picks one result.
- **Virtual invoices:** One PDF can yield multiple “virtual” invoices (e.g. by boundaries); each has `virtual_invoice_id`, own header/lines/validation.
- **Confidence-driven AI:** AI is used only when confidence is below a threshold (~0.95), not for every invoice.
- **Learning loop:** User confirms a candidate in the GUI → `save_correction` → learning DB + corrections.json; patterns feed into scoring; corrections can update Excel (Totalsumma-konfidens, Fakturatotal).
- **GUI ↔ engine split:** GUI starts the engine as a separate process, reads run_summary.json, drives validation UI and Excel updates from that.

## Module Roles

| Area | Module / package | Role |
|------|-------------------|------|
| Orchestration | `cli/main.py` | End-to-end run: routing, compare, AI, Excel, run_summary, validation_queue |
| Pipeline | `pipeline/` | Tokenization, segmentation, header/footer extraction, validation, OCR, text quality |
| Models | `models/` | Document, Page, Token, Row, Segment, InvoiceHeader, InvoiceLine, ValidationResult, VirtualInvoiceResult |
| AI | `ai/` | Client, providers, schemas, fallback orchestration |
| Learning | `learning/` | Correction collector, SQLite DB, pattern extractor/matcher/consolidator |
| Export | `export/` | Excel export, apply_corrections_to_excel, review_report |
| Review | `review/` | review_package (folder layout, README, copy of Excel/run_summary) |
| UI | `ui/` | Main window, PDF viewer, candidate selector, engine runner, themes, assets |
| Config | `config.py`, `config/` | App/config paths, AI, calibration, learning, profiles |
| Quality | `quality/` | Quality score used in run_summary |
| Debug | `debug/` | Artifact manifest/index for runs |

## Data Flow Highlights

- **Tokens** carry confidence (OCR path); used in text quality and routing.
- **InvoiceHeader** holds total_amount, total_confidence, total_candidates, total_traceability, supplier_name, invoice_number, etc.
- **ValidationResult** holds status, lines_sum, diff; with header used to decide OK/PARTIAL/REVIEW.
- **VirtualInvoiceResult** is the per-invoice result object; it gets `extraction_source` and `extraction_detail` set by the CLI.
- **run_summary** includes validation_queue (one blob per REVIEW invoice: pdf_path, invoice_id, invoice_number, supplier_name, candidates, traceability, extraction_source) for the GUI.
