# Codebase Map: Stack

**Project:** EPG PDF Extraherare (invoice-parser-app)  
**Last updated:** 2026-01-25  
**Source:** map-codebase

## Runtime & Language

| Item | Version / choice | Notes |
|------|------------------|--------|
| Python | 3.11+ | `requires-python = ">=3.11"` in pyproject.toml |
| Package manager | setuptools + wheel | Build backend in pyproject.toml |

## Core Dependencies (pyproject.toml)

| Package | Min version | Role |
|---------|-------------|------|
| pdfplumber | 0.10.0 | PDF text/tables extraction, primary text path |
| pandas | 2.0.0 | DataFrames, Excel I/O |
| openpyxl | 3.1.0 | Excel read/write (xlsx) |
| PySide6 | 6.6.0 | Desktop GUI (Qt6) |
| pymupdf | 1.23.0 | PDF rendering (viewer, page images) |
| pytesseract | 0.3.10 | OCR (Tesseract wrapper) |
| pillow | 10.0.0 | Image handling for OCR/renders |
| openai | 1.0.0 | OpenAI API client (AI fallback) |
| anthropic | 0.18.0 | Claude API client (AI fallback) |
| pydantic | 2.0.0 | Data validation, AI request/response schemas |
| scikit-learn | 1.3.0 | Confidence calibration model |
| joblib | 1.3.0 | Model serialization (calibration_model.joblib) |
| PyYAML | 6.0 | Config profiles (configs/profiles/) |
| requests | 2.31.0 | HTTP (AI, optional) |

## Dev / Tooling

| Tool | Purpose | Config |
|------|---------|--------|
| pytest | Tests | testpaths = ["tests"], py311 |
| pytest-cov | Coverage | - |
| black | Formatting | line-length 100, py311 |
| mypy | Type checking | python_version 3.11 |
| ruff | Linting | line-length 100, py311 |
| pyinstaller | Build exe | EPG_PDF_Extraherare.spec, EPG_PDF_Extraherare_CLI.spec |

## External Systems (runtime)

| System | How used |
|--------|----------|
| Tesseract OCR | Must be installed; pytesseract invokes it |
| OpenAI or Anthropic API | When AI fallback is enabled and confidence < threshold |

## Optional / Implicit

| Item | Role |
|------|------|
| tomli | Load pyproject.toml for version (get_app_version); stdlib in 3.11+ |
| SQLite | Learning DB (data/learning.db), stdlib sqlite3 |

## Stack Summary

- **Text path:** pdfplumber (primary), Tesseract OCR (fallback / compare).
- **Rendering:** pymupdf (+ Pillow) for page images and OCR input.
- **GUI:** PySide6; app entry `run_gui.py`, engine subprocess via `run_engine.py`.
- **AI:** OpenAI or Anthropic via `src/ai/`; used only when confidence below threshold.
- **Learning:** SQLite (learning.db), corrections.json, scikit-learn calibration model.
