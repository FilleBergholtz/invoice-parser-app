# Phase 15: Extraction quality hardening (OCR confidence + routing + parser robustness) – Context

**Gathered:** 2026-01-25  
**Updated:** 2026-01-25  
**Status:** Ready for planning  
**Full spec:** see **15-DISCUSS.md**  
**Depends on:** Phase 14 (Extraction fallback optimization)

---

## Phase Boundary

Implement the agreed improvements from R1–R4 and code review so extraction is **strictly better**: persist OCR token confidence and metrics, improve pdfplumber tokenization and text quality scoring, harden invoice boundary detection, improve line parsing robustness/performance, and refactor footer (and header) extraction for clear separation and deterministic routing. All changes preserve **subprocess + file-based** architecture and improve **traceability**.

**Out of scope:** GUI changes, new web services, broad pipeline refactor, model training.

---

## Current State (Summary)

- Phase 14 delivers: Token.confidence, ocr_page_metrics, text_quality, per-page routing, run_summary with method_used and vision_reason.
- Some behavior may still use placeholders (e.g. confidence 1.0) or lack full use of R1–R4 constants.
- Boundary detection, line parser, and footer/header logic need hardening and maintainability improvements as spelled out in 15-DISCUSS.

---

## Deliverables (from 15-DISCUSS)

| ID | Summary |
|----|--------|
| **D1** | Token confidence plumbing (OCR): persist TSV conf in Token, exclude conf&lt;0, OCR metrics helpers, confidence_scoring uses real confidence |
| **D2** | pdfplumber tokenizer: use_text_flow, extra_attrs with fallback, line-clustering reading order |
| **D3** | text_quality.py + R4 routing integration (TEXT_QUALITY_THRESHOLD, ai_text vs ai_vision) |
| **D4** | OCR DPI retry (R1): BASELINE_DPI → if mean_conf&lt;55 retry at RETRY_DPI once per page; artifacts show DPI |
| **D5** | Invoice boundary hardening: reduce false positives; require extra signal beyond “faktura”+alphanumeric |
| **D6** | Line parser: HARD vs SOFT footer keywords, remove O(n²) lookups, bbox-based amount detection |
| **D7** | Header: negative labels, bbox matching for split tokens. Footer: refactor to candidate→scoring→learning→calibration→routing; R4 thresholds |
| **D8** | Traceability: run_summary per-page method_used, metrics, reason flags, artifact paths, vision_reason when ai_vision |

---

## Required Constants (Phase 14 R1–R4)

All thresholds must come from Phase 14 research: `BASELINE_DPI=300`, `RETRY_DPI=400`, `OCR_MEAN_CONF_RETRY_THRESHOLD=55`, `OCR_MEDIAN_CONF_ROUTING_THRESHOLD=70`, `OCR_LOW_CONF_FRACTION_THRESHOLD=0.25`, `TEXT_QUALITY_THRESHOLD=0.5`, `CRITICAL_FIELDS_CONF_THRESHOLD=0.95`, `AI_JSON_RETRY_COUNT=1`, `VISION_MAX_PIXELS_LONGEST_SIDE=4096`, `VISION_MAX_FILE_BYTES=20MB`. See 15-DISCUSS for full table.

---

## Files in Scope

`confidence_scoring.py`, `confidence_calibration.py`, `tokenizer.py`, `ocr_abstraction.py`, `invoice_boundary_detection.py`, `invoice_line_parser.py`, `header_extractor.py`, `footer_extractor.py`, `pdf_renderer.py` (only if needed for DPI/retry). New: `text_quality.py` (if not already present from Phase 14).

---

## Acceptance Criteria (15-DISCUSS)

- OCR token confidence persisted and used (no placeholder 1.0).
- Page-level routing follows Phase 14 rules and is explainable in run_summary.json.
- False invoice boundary detections decrease without breaking multi-invoice PDFs.
- Line-item parsing drops fewer true items and improves performance.
- Footer/Header extraction correct and easier to maintain; AI/vision routing uses R4 thresholds.
- Fewer unnecessary AI/vision calls; critical field accuracy maintained or improved.

---

## Existing Codebase Anchors

- `src/pipeline/ocr_abstraction.py` — TSV parsing, Token confidence, ocr_page_metrics.
- `src/pipeline/text_quality.py` — score_text_quality, score_ocr_quality (if exists).
- `src/run_summary.py` — extraction_details, method_used, vision_reason.
- Pipeline/orchestration — R4 routing, process_pdf, extraction_detail.
- `header_extractor.py`, `footer_extractor.py`, `invoice_line_parser.py`, `invoice_boundary_detection.py`, `tokenizer.py`, `confidence_scoring.py`.

---

*Phase: 15-extraction-quality-hardening*  
*Context gathered: 2026-01-25 | Updated: 2026-01-25 | Spec: 15-DISCUSS.md*
