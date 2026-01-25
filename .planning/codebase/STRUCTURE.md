# Codebase Map: Structure

**Project:** EPG PDF Extraherare  
**Last updated:** 2026-01-25  
**Source:** map-codebase

## Repository Layout

```
invoice-parser-app/
├── run_gui.py              # GUI entry
├── run_engine.py           # CLI entry (used by GUI as subprocess)
├── pyproject.toml          # Deps, pytest/black/mypy/ruff
├── configs/
│   ├── calibration_model.joblib
│   └── profiles/
│       └── default.yaml
├── data/
│   ├── corrections.json    # User corrections (learning)
│   ├── ground_truth.json
│   └── learning.db         # SQLite learning DB
├── src/
│   ├── config.py           # App/config, output dirs, AI, calibration, learning paths
│   ├── run_summary.py      # RunSummary model + save
│   ├── ai/                 # AI client, providers, schemas, fallback
│   ├── analysis/          # Data loader, query parser/executor (Excel-based)
│   ├── batch/              # Batch runner, batch summary
│   ├── cli/                # main.py, check_deps
│   ├── config/             # profile_loader, profile_manager
│   ├── debug/              # artifact_index, artifact_manifest
│   ├── export/             # excel_export, review_report
│   ├── learning/           # correction_collector, database, pattern_*
│   ├── models/             # document, page, token, row, segment, invoice_*, validation_*, virtual_invoice_result
│   ├── pipeline/           # reader, tokenizer, ocr_abstraction, row_grouping, segment_identification, wrap_detection,
│   │                       # header_extractor, footer_extractor, invoice_line_parser, invoice_boundary_detection,
│   │                       # validation, confidence_scoring, confidence_calibration, pdf_detection, pdf_renderer,
│   │                       # text_quality, retry_extraction
│   ├── quality/            # score, model
│   ├── review/             # review_package
│   ├── ui/                 # app, views/, services/, theme/, assets/
│   └── versioning/         # compat (artifact compatibility)
├── tests/                  # test_*.py (pytest)
├── .planning/              # STATE, ROADMAP, phases, codebase map
├── specs/                  # Invoice pipeline spec, analysis
├── docs/                   # Data model, heuristics, validation, deployment
├── installer/              # NSIS installer script
└── build_*.py / *.spec     # PyInstaller / packaging
```

## Source Tree (src/)

| Path | Purpose |
|------|---------|
| `config.py` | Central config: output dirs, AI, calibration, learning, app name/version |
| `run_summary.py` | RunSummary dataclass, JSON save, validation_queue / validation blob |
| `ai/` | OpenAI/Claude clients, request/response schemas, fallback orchestration |
| `analysis/` | Load Excel invoices, parse/execute natural-language queries |
| `batch/` | Run multiple PDFs, aggregate results, batch summary |
| `cli/main.py` | CLI entry: args, routing, boundaries, process_virtual_invoice, Excel, run_summary |
| `cli/check_deps.py` | Dependency checks (Tesseract, etc.) |
| `config/` | YAML profile loading and profile manager |
| `debug/` | Artifact manifest/index for a run |
| `export/excel_export.py` | export_to_excel, apply_corrections_to_excel |
| `export/review_report.py` | create_review_report (folder + metadata) |
| `learning/` | correction_collector, database (SQLite), pattern_extractor, pattern_matcher, pattern_consolidator |
| `models/` | Document, Page, Token, Row, Segment, InvoiceHeader, InvoiceLine, ValidationResult, VirtualInvoiceResult, traceability |
| `pipeline/` | Full extraction pipeline (reader → tokens → segments → header/footer → validation), OCR, text quality, calibration |
| `quality/` | calculate_quality_score for run_summary |
| `review/review_package.py` | create_review_package (folder layout, copy Excel/run_summary, README) |
| `ui/app.py` | QApplication, styles, main window |
| `ui/views/` | main_window, pdf_viewer, candidate_selector, about_dialog, ai_settings_dialog |
| `ui/services/engine_runner.py` | Run engine process, read run_summary, emit result_ready |
| `ui/theme/` | QSS and theme application |
| `ui/assets/icons/` | app.svg, open, run, export, settings, about; app.ico |
| `versioning/compat.py` | check_artifacts_compatibility (RunSummary/artifact compatibility) |

## Test Layout (tests/)

- `test_*.py` for: ai_client, artifact_manifest, backward_compat, batch_runner, cli, correction_dedup, document, excel_export, footer_extractor, header_extractor, invoice_header, invoice_line_parser, page, pdf_detection, pdf_renderer, profile_loader, quality_score, review_package, review_report, row_grouping, run_summary, segment_identification, tokenizer, traceability, validation, wrap_detection.
- `fixtures/pdfs/` for test PDFs (see README there).

## Build / Deploy

- **PyInstaller:** `EPG_PDF_Extraherare.spec` (GUI), `EPG_PDF_Extraherare_CLI.spec` (CLI).
- **Installer:** `installer/installer.nsi` (NSIS).
- **Scripts:** `build_installer.py`, `build_package.py`, `build_windows.py`.

## Planning and Docs

- **.planning/** : STATE.md, ROADMAP.md, PROJECT.md, REQUIREMENTS.md, phases/ (01–15), research/, codebase/.
- **docs/** : Data model, heuristics, validation, test corpus, deployment.
- **specs/** : Invoice pipeline spec, SPEC_ANALYSIS.
