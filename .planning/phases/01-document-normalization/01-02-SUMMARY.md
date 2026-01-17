---
phase: 01-document-normalization
plan: 02
subsystem: token-extraction
tags: [pdfplumber, pymupdf, pytesseract, ocr]

# Dependency graph
requires:
  - phase: 01-01
    provides: Document and Page models, PDF reader, PDF type detection
provides:
  - Token model (already created in 01-01)
  - Tokenizer for pdfplumber (searchable PDFs)
  - PDF-to-image renderer (300 DPI, pymupdf)
  - OCR abstraction layer (Tesseract implementation)
affects: [01-03 - layout analysis needs tokens]

# Tech tracking
tech-stack:
  added: [pymupdf for PDF rendering, pytesseract for OCR (optional)]
  patterns: [OCR abstraction with ABC interface, TSV parsing for bbox+confidence]

key-files:
  created:
    - src/pipeline/tokenizer.py
    - src/pipeline/pdf_renderer.py
    - src/pipeline/ocr_abstraction.py
    - tests/test_tokenizer.py
    - tests/test_pdf_renderer.py
  modified: []

key-decisions:
  - "Used pymupdf (fitz) for PDF rendering - no system dependencies needed (vs pdf2image requiring Poppler)"
  - "OCR abstraction uses ABC interface - allows future engine switching (PaddleOCR, EasyOCR)"
  - "Tesseract uses TSV output format to get bbox + confidence (not just raw text)"

patterns-established:
  - "OCR pattern: Abstract base class (OCREngine) with concrete implementations"
  - "Coordinate system: Tesseract image coords need scaling to match Page coordinate system"

# Metrics
duration: ~20min
completed: 2026-01-17
---

# Phase 01: Document Normalization - Plan 02 Summary

**Token extraction implemented with pdfplumber path, PDF rendering for OCR, and OCR abstraction layer with Tesseract**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-01-17 13:53
- **Completed:** 2026-01-17 14:13
- **Tasks:** 5 completed
- **Files modified:** 5 created

## Accomplishments

- Tokenizer for searchable PDFs using pdfplumber (extracts tokens with spatial info)
- PDF-to-image renderer using pymupdf (300 DPI, consistent coordinates)
- OCR abstraction layer with Tesseract implementation (TSV output for bbox+confidence)
- Unit tests created for tokenizer and PDF renderer

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Token data model** - Already completed in 01-01
2. **Task 2: Implement tokenizer for searchable PDFs** - `7efada0` (feat)
3. **Task 3: Implement PDF page to image rendering** - `59cec7e` (feat)
4. **Task 4: Implement OCR abstraction layer** - `a7b2e33` (feat)
5. **Task 5: Write unit tests** - Current commit (test)

## Files Created/Modified

- `src/pipeline/tokenizer.py` - Token extraction from pdfplumber (extract_tokens_from_page)
- `src/pipeline/pdf_renderer.py` - PDF page to image conversion (300 DPI, pymupdf)
- `src/pipeline/ocr_abstraction.py` - OCR abstraction layer with OCREngine ABC and TesseractOCREngine
- `tests/test_tokenizer.py` - Unit tests for tokenizer
- `tests/test_pdf_renderer.py` - Unit tests for PDF renderer

## Decisions Made

- **PDF rendering library:** Chose pymupdf (fitz) over pdf2image because it has no system dependencies (pdf2image requires Poppler). This makes installation simpler.

- **OCR abstraction design:** Used ABC (Abstract Base Class) pattern with OCREngine interface. This allows easy switching to other OCR engines (PaddleOCR, EasyOCR) by implementing the same interface.

- **Tesseract output format:** Used TSV output format instead of HOCR or raw text to get both bounding boxes and confidence scores in structured format. This enables proper token creation with spatial information.

- **Coordinate system:** Tesseract returns image pixel coordinates. Conversion to Page coordinate system needs DPI scaling consideration (TODO: proper coordinate transformation).

## Deviations from Plan

None - plan executed exactly as written. All tasks completed as specified.

## Verification Status

- ✅ Token model already created in 01-01
- ✅ Tokenizer extracts tokens with valid bbox from pdfplumber
- ✅ PDF renderer converts pages to 300 DPI images (implementation complete)
- ✅ OCR abstraction layer with Tesseract implementation (TSV output for bbox+confidence)
- ⚠️ Integration tests with actual PDFs pending (requires sample PDF files)

## Next Steps

Plan 01-03 depends on this plan - will use tokens for layout analysis (row grouping).

---

*Plan completed: 2026-01-17*
