# Codebase Map: Integrations

**Project:** EPG PDF Extraherare  
**Last updated:** 2026-01-25  
**Source:** map-codebase

## External Integrations

### 1. Tesseract OCR

| Aspect | Detail |
|--------|--------|
| Where | `src/pipeline/ocr_abstraction.py` |
| Trigger | OCR extraction path or compare-extraction (pdfplumber vs OCR) |
| Config | System-installed Tesseract; no in-app path config |
| Failure mode | OCRException / exit code surfaced; DPI retry (e.g. 400) when mean confidence low |

### 2. OpenAI API

| Aspect | Detail |
|--------|--------|
| Where | `src/ai/client.py`, `src/ai/providers.py` |
| Trigger | AI fallback when total/invoice-number confidence < threshold (~0.95) |
| Config | `configs/ai_config.json`, env AI_KEY, AI_ENDPOINT, AI_PROVIDER, AI_MODEL |
| Usage | Structured extraction (totals, header, lines) via provider-specific clients |

### 3. Anthropic Claude API

| Aspect | Detail |
|--------|--------|
| Where | Same as OpenAI; `AI_PROVIDER` selects provider |
| Trigger | Same as OpenAI when provider is "claude" |
| Config | Same config namespace; provider-specific model/endpoint handling |

### 4. File System

| Aspect | Detail |
|--------|--------|
| Input | PDF paths from CLI `--input` or GUI file picker |
| Output | `get_default_output_dir()`: dev → `out/`, frozen → Documents/EPG PDF Extraherare/output (Win) or ~/.epg-pdf-extraherare/output |
| Subdirs | excel/, review/, errors/, temp/ via `get_output_subdirs()` |
| Learning | `data/learning.db`, `data/corrections.json`; paths via config / project root |

### 5. Subprocess (GUI → Engine)

| Aspect | Detail |
|--------|--------|
| Where | `src/ui/services/engine_runner.py` |
| Invocation | Dev: `sys.executable run_engine.py --input ... --output ... --verbose`; frozen: `invoice_engine.exe` alongside GUI exe |
| Contract | Engine writes `run_summary.json` in output dir; GUI reads it and shows validation_queue / excel_path etc. |

## Internal Integration Boundaries

### CLI ↔ Pipeline

- **Entry:** `src/cli/main.py` orchestrates runs.
- **Flow:** read_pdf → detect_pdf_type / route_extraction_path → detect_invoice_boundaries → per-invoice process_virtual_invoice (tokenizer, segments, header, footer, validation, optional AI, optional compare pdfplumber vs OCR).
- **Data:** Pipeline returns VirtualInvoiceResult; CLI builds invoice_results, run_summary, Excel, review packages.

### GUI ↔ Engine

- **Entry:** `main_window.py` starts EngineRunner in a QThread.
- **Contract:** EngineRunner runs engine process, parses `run_summary.json`, emits result_ready(summary). GUI uses summary for validation_queue, excel_path, and to drive validation UI and Excel updates after corrections.

### AI ↔ Pipeline

- **Entry:** `src/ai/fallback.py` used from CLI’s process_virtual_invoice path.
- **Trigger:** When critical-field confidence below threshold and AI enabled.
- **Data:** AIClient.build_request / get_enrichment; pipeline applies AI header/line/total results onto VirtualInvoiceResult.

### Learning ↔ Pipeline & GUI

- **Corrections:** `src/learning/correction_collector.py` (save_correction), `src/learning/database.py` (add_correction, get_corrections).
- **Trigger:** GUI “Bekräfta” in validation UI; optional CLI `--import-corrections`.
- **Usage:** Pattern extractor/matcher used for scoring/learning; corrections also drive Excel update (apply_corrections_to_excel) and validation blob (supplier_name in run_summary).

### Export ↔ CLI / GUI

- **Excel:** `src/export/excel_export.py` (export_to_excel, apply_corrections_to_excel). Called from CLI when writing consolidated and per-invoice Excel; from GUI indirectly by applying corrections to existing Excel files.
- **Review:** `create_review_report`, `create_review_package` from CLI for REVIEW-status invoices.

## Configuration Surfaces

| Surface | Role |
|---------|------|
| `src/config.py` | App name, version, default output dir, AI enabled/endpoint/provider/model/key, calibration/learning paths |
| `configs/ai_config.json` | Persisted AI settings (enabled, provider, model, api_key) |
| `configs/profiles/*.yaml` | Profile loader / manager (e.g. default.yaml) |
| Env vars | AI_*, CALIBRATION_*, LEARNING_* override or supplement config |
