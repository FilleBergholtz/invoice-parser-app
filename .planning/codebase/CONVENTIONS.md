# Codebase Map: Conventions

**Project:** EPG PDF Extraherare  
**Last updated:** 2026-01-25  
**Source:** map-codebase

## Code Style

| Tool | Config | Effect |
|------|--------|--------|
| Black | pyproject.toml: line-length 100, target py311 | Formatting |
| Ruff | pyproject.toml: line-length 100, py311 | Linting |
| mypy | pyproject.toml: python_version 3.11, warn_return_any, warn_unused_configs | Type checking |

Conventions are applied at 100 chars line length and Python 3.11 target across tools.

## Naming

- **Packages/modules:** `snake_case` (e.g. `invoice_line_parser`, `correction_collector`).
- **Classes:** `PascalCase` (e.g. `VirtualInvoiceResult`, `InvoiceHeader`).
- **Functions/methods:** `snake_case` (e.g. `extract_tokens_from_page`, `get_default_output_dir`).
- **Tests:** files `test_*.py`, classes `Test*`, functions `test_*` (pytest defaults in pyproject.toml).
- **Constants:** `UPPER_SNAKE` where used (e.g. routing/OCR constants in pipeline/cli).

## Project Layout

- **Entry points** at repo root: `run_gui.py`, `run_engine.py`.
- **Library code** under `src/`; top-level `config.py` and `run_summary.py` in `src/`.
- **Tests** in `tests/`; one test module per logical component (e.g. `test_footer_extractor.py`).
- **Config/data** in `configs/`, `data/`; output in `out/` (dev) or configurable output dir.

## Imports

- Prefer explicit package roots: `from ..models.invoice_header import InvoiceHeader`, `from ..pipeline.reader import read_pdf`.
- Absolute-style from project root is not used; the project is run as a package (e.g. `python run_engine.py` / `python run_gui.py` from repo root with `src` on path or equivalent).

## Types and Docstrings

- Type hints used in function signatures and important module-level APIs.
- Docstrings follow a “Args/Returns/Raises” style where present; not every helper is fully documented.
- Pydantic used for AI request/response and structured validation where applicable.

## Error Handling

- Custom exceptions (e.g. `PDFReadError`, `OCRException`, `AIClientError`) used for failure modes that callers should handle.
- Logging via `logging.getLogger(__name__)`; avoid print in library code except CLI progress.
- CLI uses `--verbose` to control extra output.

## UI (PySide6)

- Swedish labels in user-facing strings (“Öppna PDF”, “Kör”, “Export”, “Bekräfta”, etc.).
- Icons and assets under `src/ui/assets/`; QRC for resources; theme via QSS in `ui/theme/`.
- Engine run in background thread via `EngineRunner` and `QThread`; signals used for progress and result.

## Configuration

- Central entry: `src/config.py` (getters for output dir, AI, calibration, learning paths).
- Env vars override or supply AI/calibration/learning when set.
- Profile YAML in `configs/profiles/` loaded via `config/profile_loader` and `profile_manager`.

## Docs and Planning

- **.planning/** holds STATE.md, ROADMAP.md, PROJECT.md, phases (e.g. 15-CONTEXT, 15-01-PLAN), and this codebase map.
- **docs/** holds user/developer docs (data model, heuristics, validation, deployment).
- **specs/** holds pipeline and analysis specs.
