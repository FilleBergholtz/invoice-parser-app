# 14-04: Rendering DPI — Summary

**Done:** 2026-01-25

## Objective

Support 300 DPI baseline and optional 400 DPI retry for OCR. Per 14-RESEARCH R1: baseline 300, retry 400 only when ocr_mean_conf < 55 after first OCR, max 1 retry per page. This plan adds the capability in the renderer; orchestration (14-06) will decide when to call with dpi=400.

## Completed tasks

1. **`dpi` parameter on `render_page_to_image`** (`src/pipeline/pdf_renderer.py`)
   - Signature: `render_page_to_image(page, output_dir, dpi: int = 300)`.
   - Zoom uses `dpi / 72.0`. Default 300 keeps existing callers unchanged.
   - Docstring notes that 400 is for OCR retry when mean_conf is low (R1).

2. **R1 constants for orchestration**
   - In `pdf_renderer`: `BASELINE_DPI = 300`, `RETRY_DPI = 400`, `OCR_MEAN_CONF_RETRY_THRESHOLD = 55`, `MAX_DPI_RETRIES_PER_PAGE = 1`.
   - Module docstring references 14-RESEARCH R1. Orchestration can import these when implementing retry logic in 14-06.

## Files changed

- `src/pipeline/pdf_renderer.py` — `dpi` parameter, zoom from dpi/72, R1 constants and doc updates.

## Verification

- `render_page_to_image(page, output_dir)` and `render_page_to_image(page, output_dir, dpi=300)` preserve current behaviour.
- `render_page_to_image(page, output_dir, dpi=400)` produces a larger (higher-resolution) image.
- R1 constants are defined in `pdf_renderer` and importable for orchestration.
