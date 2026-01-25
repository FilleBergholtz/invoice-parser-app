# Codebase Map: Testing

**Project:** EPG PDF Extraherare  
**Last updated:** 2026-01-25  
**Source:** map-codebase, refreshed by gsd-codebase-mapper

## Framework and Config

| Item | Choice |
|------|--------|
| Runner | pytest |
| Config | pyproject.toml: testpaths = ["tests"], python_files = "test_*.py", python_functions = "test_*", python_classes = "Test*" |
| Coverage | pytest-cov (dependency present) |

## Test Layout

- **Directory:** `tests/`
- **Naming:** `test_<module_or_feature>.py` (e.g. `test_footer_extractor.py`, `test_excel_export.py`).
- **Fixtures:** `tests/fixtures/pdfs/` for test PDFs (see README there).

## Coverage by Area

Tests are grouped by component; each file typically targets one package or feature:

| Test file | Target area |
|-----------|-------------|
| test_ai_client.py | AI client / API interaction |
| test_artifact_manifest.py | Debug artifact manifest |
| test_backward_compat.py | Backward compatibility (run_summary, etc.) |
| test_batch_runner.py | Batch runner |
| test_cli.py | CLI entry / arguments / flow |
| test_correction_dedup.py | Learning correction deduplication |
| test_document.py | Document model |
| test_excel_export.py | Excel export, apply_corrections_to_excel |
| test_footer_extractor.py | Footer / total extraction |
| test_header_extractor.py | Header extraction |
| test_invoice_header.py | InvoiceHeader model |
| test_invoice_line_parser.py | Line parser |
| test_page.py | Page model |
| test_pdf_detection.py | PDF type detection, routing |
| test_pdf_renderer.py | PDF rendering (pymupdf) |
| test_profile_loader.py | Config profile loading |
| test_quality_score.py | Quality scoring |
| test_review_package.py | Review package creation |
| test_review_report.py | Review report creation |
| test_row_grouping.py | Row grouping |
| test_run_summary.py | RunSummary serialization / structure |
| test_segment_identification.py | Segment identification |
| test_tokenizer.py | Tokenization (pdfplumber/OCR path) |
| test_traceability.py | Traceability model |
| test_validation.py | Validation logic (OK/PARTIAL/REVIEW) |
| test_wrap_detection.py | Wrap detection |

About 117 test functions/classes across these 26 files (pytest discovery: test_* functions and Test* classes).

## Running Tests

```bash
# From repo root
pytest

# With coverage (if wired in)
pytest --cov=src --cov-report=...
```

## Gaps and Conventions

- **GUI:** No automated tests under `tests/` for PySide6 views; UI is exercised manually.
- **Integration:** No end-to-end test driver that runs a full pipeline on a real PDF and asserts on Excel/run_summary; coverage is mainly unit/component.
- **Fixtures:** PDF fixtures are referenced from `tests/fixtures/pdfs/`; other fixtures (e.g. JSON, small PDFs) are built in test code or via helpers.
- **Mocks:** AI and external services are mocked in tests (e.g. test_ai_client) to avoid network and API keys.
