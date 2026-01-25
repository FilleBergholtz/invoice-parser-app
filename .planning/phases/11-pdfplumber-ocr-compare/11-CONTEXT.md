# Phase 11: Pdfplumber och OCR – Context

**Gathered:** 2026-01-25  
**Status:** Ready for execution

## Phase Boundary

Implement both pdfplumber and OCR extraction, run both per invoice/PDF, compare results (e.g. validation_passed, confidence), and use the best source going forward in the pipeline.

**Core Problem:** Pdfplumber uses embedded PDF text; it can include garbled layers (watermarks, reversed text). OCR on rendered pages often yields cleaner text for AI and extraction. We don't know which is better per document—so we run both and pick the best.

**Goal:** System runs both pdfplumber and OCR extraction when configured, compares outcomes, and uses the best result (validation + confidence) for export, review, and AI.

## Existing Pieces

- **`ocr_abstraction`:** `TesseractOCREngine`, `extract_tokens_with_ocr(page)`. Expects `page.rendered_image_path`. Returns `List[Token]`; coordinates are in **image pixels** (TODO: scale to page points).
- **`pdf_renderer`:** `render_page_to_image(page, output_dir)` → PNG at 300 DPI, sets `page.rendered_image_path`. Uses pymupdf (fitz).
- **`tokenizer`:** `extract_tokens_from_page(page, pdfplumber_page)` → tokens from pdfplumber (points).
- **`pdf_detection`:** `route_extraction_path(doc)` → `"pdfplumber"` or `"ocr"`. OCR path exists but is not implemented in `process_invoice` / `process_virtual_invoice` (only logs a warning).
- **Pipeline:** tokens → `group_tokens_to_rows` → `identify_segments` (header/items/footer by Y thresholds in **page coordinates**). Same pipeline for both sources once we have tokens in page space.

## Implementation Decisions

### 1. OCR coordinate scaling

- Render at 300 DPI ⇒ image size (px) = page size (pt) × 300/72. Scale factor **72/300** converts OCR pixel coordinates to page points.
- Apply scaling in `ocr_abstraction` (or a thin wrapper) before creating `Token`s so segment identification works.

### 2. OCR path wiring

- When `extraction_path == "ocr"`: for each page, `render_page_to_image(page, output_dir)` then `extract_tokens_with_ocr(page)`. Use e.g. `output_dir / "ocr_render"` for images.
- Reuse same pipeline: `group_tokens_to_rows` → `identify_segments` → line items, footer, etc.

### 3. Dual-run and compare (nu standard)

- **Compare är standard:** Motorn kör både pdfplumber och OCR per faktura, jämför och använder bästa resultatet. CLI-flagga `--no-compare-extraction` stänger av OCR-jämförelsen (endast pdfplumber).
- När compare är på (default):
  - Run full pipeline with **pdfplumber** → result A (per virtual invoice or per PDF).
  - Run full pipeline with **OCR** → result B.
  - Compare A vs B (e.g. `validation_passed`, `total_confidence`, optionally `invoice_number_confidence`).
  - Select **best** and use that result for the rest of the run.
- Vid konfidens &lt; 95 % används AI-fallback (om aktiverad) oavsett compare.

### 4. “Best” definition

- Prefer result with `validation_passed` (total ≈ line_items_sum) if only one has it.
- Else prefer higher `total_confidence` (and optionally `invoice_number_confidence`).
- If both fail (e.g. no candidates), keep pdfplumber as default.

### 5. Dependencies

- `pytesseract`, `pillow` for OCR. Tesseract binary + Swedish (`swe`) data on system.

## Plans (Overview)

1. **11-01:** OCR path wiring — coordinate scaling, render→OCR in pipeline, dependencies.
2. **11-02:** Dual-run and comparison — `--compare-extraction`, run both, compare, pick best.
3. **11-03:** Use best result downstream — ensure export/review/AI use chosen source; optional logging of which source was used.
