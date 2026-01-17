# Stack Research

**Domain:** Invoice parsing system (OCR + layout analysis + data extraction)
**Researched:** 2025-01-27
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Runtime environment | Industry standard for OCR/data processing pipelines, excellent library ecosystem |
| pdfplumber | >=0.10.0 | PDF text extraction & layout analysis | Excellent for searchable PDFs, preserves layout, built-in table detection, spatial information (x,y,width,height) |
| pandas | >=2.0.0 | Data processing & Excel export | Industry standard for structured data manipulation, excellent Excel export capabilities |
| pytest | >=7.4.0 | Testing framework | Standard Python testing tool, integrates well with data pipelines |
| pytesseract | Latest | OCR for scanned PDFs | Free, open-source OCR engine with good Swedish language support, fallback when PDF has no text layer. **Requirement:** Tesseract OCR must be installed system-wide with Swedish language data (swe). OCR abstraction layer allows switching to PaddleOCR/EasyOCR later without pipeline changes |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pdf2image | Latest | PDF to image conversion | When OCR is needed for scanned/inaccessible PDFs. **Requirement:** Requires Poppler system dependency. Alternative: pymupdf (fitz) |
| pymupdf (fitz) | Latest | PDF rendering to images | Alternative to pdf2image. **Requirement:** Standardized DPI (e.g. 300) and consistent coordinate system across all rendering |
| opencv-python | Latest | Image preprocessing | Deskewing, noise reduction, contrast enhancement before OCR |
| Pillow (PIL) | Latest | Image manipulation | Image preprocessing and conversion utilities |
| openpyxl | Latest | Excel file generation | Enhanced Excel export with formatting, multiple sheets |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| black | >=23.0.0 | Code formatting | PEP 8 compliance, consistent style |
| mypy | >=1.5.0 | Type checking | Type hints validation for Python 3.11+ |
| ruff | >=0.0.280 | Linting | Fast Python linter, replaces flake8 |

## Installation

```bash
# Core dependencies (already in pyproject.toml)
pip install pdfplumber>=0.10.0 pandas>=2.0.0 pytest>=7.4.0 pytest-cov>=4.1.0

# PDF rendering (choose one)
pip install pdf2image  # Requires Poppler system dependency
# OR
pip install pymupdf  # Alternative: fitz library

# OCR support (requires system Tesseract with Swedish)
pip install pytesseract opencv-python Pillow

# Excel export enhancement
pip install openpyxl

# Dev dependencies (already in pyproject.toml)
pip install black>=23.0.0 mypy>=1.5.0 ruff>=0.0.280
```

### System Dependencies

**Tesseract OCR (REQUIRED for OCR functionality):**
- Install Tesseract OCR with Swedish language data (swe)
- macOS: `brew install tesseract tesseract-lang`
- Linux: `apt-get install tesseract-ocr tesseract-ocr-swe` (or equivalent)
- Windows: Download installer from GitHub releases

**Poppler (if using pdf2image):**
- Required for PDF to image conversion
- macOS: `brew install poppler`
- Linux: `apt-get install poppler-utils`

**OCR Abstraction Requirement:**
- OCR interface must return: tokens + bbox + confidence (not just raw text)
- Tesseract can provide this via TSV or HOCR output format
- Design allows switching to PaddleOCR/EasyOCR later without changing pipeline

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| pdfplumber | PyPDF2, pdfminer.six | PyPDF2 is simpler but lacks layout analysis. pdfminer.six is lower-level, pdfplumber provides better abstraction. |
| pdfplumber | pdfminer directly | pdfplumber is built on pdfminer but provides higher-level API with better table detection. |
| pytesseract | AWS Textract, Google Document AI | Cloud services offer higher accuracy but have cost, vendor lock-in, and latency. Use for production at scale with budget. |
| pytesseract | PaddleOCR, EasyOCR | More advanced OCR engines with better accuracy. **Design requirement:** OCR abstraction layer allows switching engines without pipeline changes. Tesseract via pytesseract with TSV/HOCR output provides tokens+bbox+confidence. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Pure regex-based extraction | Brittle, breaks with layout changes, no spatial understanding | pdfplumber for layout-aware extraction + rules for field identification |
| Template-based parsing only | Requires maintenance for each vendor, breaks with format changes | Layout analysis + AI/rule hybrid approach |
| Generic OCR without preprocessing | Poor accuracy on low-quality scans | Preprocessing (deskew, denoise) + OCR |
| Unstructured text extraction | Loses spatial information critical for field identification | Spatial-aware extraction (pdfplumber or OCR with bbox). **Requirement:** OCR must return tokens+bbox+confidence, not just raw text |
| Table extractor as single point of failure | pdfplumber table detection can fail on complex layouts | Layout-driven approach: tokens→rows→segments. Table extractors are helpers, not core dependency |

## Stack Patterns by Variant

**If primarily digital/searchable PDFs:**
- Use pdfplumber as primary extractor (fast, accurate)
- Minimal OCR dependency (fallback only)
- Focus on layout analysis and spatial heuristics

**If primarily scanned PDFs:**
- Use pdf2image (or pymupdf) + pytesseract for OCR
- **Requirement:** Standardized DPI (300) and consistent coordinate system
- OCR via TSV/HOCR to get tokens+bbox+confidence (not just raw text)
- Add preprocessing (opencv-python) for image quality
- Combine OCR output with pdfplumber-style spatial analysis

**If mixed sources (production):**
- Detect PDF type first (text layer check)
- Route to pdfplumber (searchable) or OCR pipeline (scanned)
- Unified extraction interface regardless of source

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| pdfplumber>=0.10.0 | Python 3.11+ | Requires pdfminer.six internally |
| pandas>=2.0.0 | Python 3.11+ | Better type hints, performance improvements |
| pytesseract | Tesseract OCR engine (system install) | Requires separate Tesseract installation with Swedish language data (swe), not a Python package dependency |
| pdf2image | Poppler (system install) | Requires Poppler system dependency for PDF rendering |
| pymupdf | Self-contained | No system dependencies, alternative to pdf2image |

## Sources

- WebSearch 2025 — "invoice parsing PDF OCR Python 2025 best libraries pdfplumber pytesseract"
- WebSearch 2025 — Industry benchmarks and library comparisons
- Official docs: pdfplumber.com, pandas.pydata.org
- Project requirement: Already specified in pyproject.toml

---
*Stack research for: Invoice Parser App (Swedish invoices, 100% accuracy on invoice number/total)*
*Researched: 2025-01-27*
