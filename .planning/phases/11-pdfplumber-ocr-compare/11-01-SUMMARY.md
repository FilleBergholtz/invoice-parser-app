# 11-01: OCR path wiring — Summary

**Done:** 2026-01-25

## Objective

Wire OCR extraction path: scale OCR token coordinates to page space, render pages for OCR, and use OCR in process_invoice / process_virtual_invoice when extraction_path is "ocr".

## Completed tasks

1. **Scale OCR token coordinates to page points** (`src/pipeline/ocr_abstraction.py`)
   - After loading image, use `img.size` (pixels) and `page.width` / `page.height` (points).
   - Compute `scale_x = page.width / img_width`, `scale_y = page.height / img_height`.
   - Scale each token’s x, y, width, height from pixels to points before creating `Token`.
   - Removed TODO; segment_identification now works with OCR-derived tokens.

2. **Add OCR dependencies** (`pyproject.toml`)
   - Added `pytesseract>=0.3.10` and `pillow>=10.0.0` to `[project] dependencies`.
   - Tesseract binary + Swedish (`swe`) is required for OCR path; `TesseractOCREngine` verifies and logs clearly if missing.

3. **Wire OCR path in process_invoice** (`src/cli/main.py`)
   - Imports: `render_page_to_image`, `extract_tokens_with_ocr`, `OCRException`.
   - When `extraction_path == "ocr"`: `ocr_render_dir = Path(output_dir) / "ocr_render"`.
   - For each page: `render_page_to_image(page, str(ocr_render_dir))` then `extract_tokens_with_ocr(page)`.
   - On `OCRException` or other failure: log (if verbose) and use `tokens = []` for that page.
   - No pdfplumber usage when OCR path is active.

4. **Wire OCR path in process_virtual_invoice and boundary detection**
   - **process_virtual_invoice:** Added `output_dir: Optional[str] = None`. When `extraction_path == "ocr"` and `output_dir` set, use `ocr_render_dir = Path(output_dir) / "ocr_render"`, then render + OCR per page. Replaced "OCR path not yet implemented" with real OCR branch.
   - **detect_invoice_boundaries:** Added `output_dir: Optional[str] = None`. When `extraction_path == "ocr"`, use `render_page_to_image` + `extract_tokens_with_ocr` per page; if `output_dir` is None, use `tempfile.mkdtemp(prefix="ocr_boundary_")` for render output.
   - **Callers:** `process_pdf` passes `output_dir` to both `detect_invoice_boundaries` and `process_virtual_invoice`.

## Files changed

- `src/pipeline/ocr_abstraction.py` — coordinate scaling
- `pyproject.toml` — pytesseract, pillow
- `src/cli/main.py` — OCR path in process_invoice and process_virtual_invoice; imports; `output_dir` passed to boundaries and process_virtual_invoice
- `src/pipeline/invoice_boundary_detection.py` — OCR path with render + OCR; `output_dir` param

## Acceptance

- OCR tokens use page coordinates (points); segment identification works.
- process_invoice and process_virtual_invoice use OCR when extraction_path is "ocr" (render → OCR → same pipeline).
- Boundary detection uses OCR when extraction_path is "ocr".
- No remaining "OCR path not yet implemented" in these code paths.
- Existing tests (footer, run_summary, segment, row, batch_runner, etc.) pass.
