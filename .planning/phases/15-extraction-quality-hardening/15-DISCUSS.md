# Phase 15: Extraction quality hardening – Discussion / Spec

**Diskuterad:** 2026-01-25  
**Uppdaterad:** 2026-01-25  
**Källa:** /gsd:discuss-phase 15

---

## OBJECTIVE

Implement the agreed improvements from the latest R1–R4 update and code review to make extraction **strictly better**:

1. **Persist OCR token confidence** and compute OCR quality metrics.
2. **Improve pdfplumber tokenization** metadata and reading order.
3. **Implement text quality scoring** and integrate it into routing (R4).
4. **Harden invoice boundary detection** to reduce false positives.
5. **Improve invoice line parsing** robustness and performance.
6. **Refactor footer extraction** for separation of concerns and deterministic routing decisions.

All changes must **preserve subprocess + file-based architecture** and **improve traceability**.

---

## SCOPE / CONSTRAINTS

- **Desktop app (PySide6) unchanged;** engine remains subprocess and writes artifacts.
- **Keep existing behavior as default/fallback;** changes should be incremental and reversible.
- **Minimal dependencies;** prefer existing stack (pdfplumber, PyMuPDF, Tesseract).
- **Decisions and thresholds MUST use constants from Phase 14 research (R1–R4).**

---

## FILES IN SCOPE (from repo)

| File | Role in phase |
|------|----------------|
| `confidence_scoring.py` | Use actual token confidence (remove placeholder 1.0); align with OCR metrics |
| `confidence_calibration.py` | Keep as-is unless routing/score consistency requires small tweaks |
| `tokenizer.py` | use_text_flow, extra_attrs, reading order (line clustering) |
| `ocr_abstraction.py` | TSV conf → Token.confidence, OCR metrics (median/mean/low_conf_fraction), exclude conf&lt;0 |
| `invoice_boundary_detection.py` | Harden to reduce false positives; require extra signal beyond “faktura” + alphanumeric |
| `invoice_line_parser.py` | Hard/soft footer keywords, remove O(n²) lookups, bbox-based amount detection |
| `header_extractor.py` | Negative labels (orgnr, kundnr, order…), bbox matching for split OCR tokens |
| `footer_extractor.py` | Refactor: candidate gen → scoring → learning → calibration → AI routing; score_raw vs score_calibrated; use R4 thresholds |
| `pdf_renderer.py` | Only if needed for DPI metadata / retry (R1) |

---

## REQUIRED CONSTANTS (from Phase 14 research)

All routing and quality decisions **must** use these; define in one place and import where needed.

| Constant | Value | Use |
|----------|--------|-----|
| `BASELINE_DPI` | 300 | Default page render for OCR |
| `RETRY_DPI` | 400 | Retry render when mean_conf below threshold |
| `OCR_MEAN_CONF_RETRY_THRESHOLD` | 55 | Trigger DPI retry (R1) |
| `OCR_MEDIAN_CONF_ROUTING_THRESHOLD` | 70 | Route to AI when below (R2) |
| `OCR_LOW_CONF_FRACTION_THRESHOLD` | 0.25 | Support signal for vision (R2) |
| `TEXT_QUALITY_THRESHOLD` | 0.5 | Above → AI text-only ok; below → vision eligible (R4) |
| `CRITICAL_FIELDS_CONF_THRESHOLD` | 0.95 | Gate for OK status |
| `AI_JSON_RETRY_COUNT` | 1 | Max retries on invalid JSON |
| `VISION_MAX_PIXELS_LONGEST_SIDE` | 4096 | Vision image limit (R3) |
| `VISION_MAX_FILE_BYTES` | 20·1024·1024 (20 MB) | Vision file size limit (R3) |

---

## DELIVERABLES

### D1) Token confidence plumbing (OCR)

- **Token model:** `confidence: Optional[float]`
- **ocr_abstraction.py:**
  - Store TSV word-level confidence into `Token.confidence` for word tokens.
  - Exclude `conf < 0` (or include only `level==5`) from any aggregation.
- **OCR metrics helpers:** `ocr_median_conf`, `ocr_mean_conf`, `ocr_low_conf_fraction` (or single function / dataclass returning all).
- **confidence_scoring.py:** Use actual token confidence; **remove placeholder 1.0** behavior where OCR tokens are involved.

### D2) pdfplumber tokenizer improvements

- **tokenizer.py:**
  - Remove unused chars extraction if not needed.
  - Use `extract_words(use_text_flow=True)`.
  - Enable `extra_attrs=["fontname","size"]` with **safe fallback** (try/except or feature flag) so font metadata is available for scoring.
  - Improve reading order by **clustering tokens into lines** (avoid simple (y,x) mixing).

### D3) Text quality scoring module + integration

- **New module:** `text_quality.py`
  - `score_text_quality(text, tokens) -> float` in [0..1]
  - `score_ocr_quality(tokens) -> float` in [0..1] using OCR metrics
- **Integration in routing (per page), R4:**
  - If `best_available_text_quality >= TEXT_QUALITY_THRESHOLD` → AI text-only allowed.
  - If both `pdf_text_quality` and `ocr_text_quality` < threshold → AI vision (if allowed).

### D4) OCR DPI retry implementation (R1)

- After OCR at `BASELINE_DPI`:
  - If `ocr_mean_conf < OCR_MEAN_CONF_RETRY_THRESHOLD` → re-render that page at `RETRY_DPI` and re-run OCR **once**.
- Max **one retry per page**.
- Artifacts must reflect which DPI was used per page.

### D5) Invoice boundary detection hardening

- **invoice_boundary_detection.py:**
  - Reduce false positives: do **not** treat “faktura” + random alphanumeric as sufficient alone.
  - Require **additional signal** (label match, strong candidate score, or combination with date/amount signals).
  - Reuse existing scoring where possible; avoid weak regex-only checks.

### D6) Invoice line parser robustness + performance

- **invoice_line_parser.py:**
  - Split footer keyword logic into **HARD** vs **SOFT** keywords.
  - For **SOFT** keywords require additional signal (footer zone, amount patterns, etc.) before classifying as footer.
  - **Remove O(n²) token index lookups** (e.g. `row.tokens.index(token)` in loops).
  - Prefer **bbox/X-position based** amount detection; avoid brittle char-offset mapping where possible.

### D7) Header/Footer extractor maintainability + routing consistency

- **header_extractor.py:**
  - Improve candidate filtering with **negative labels** (orgnr, kundnr, order, etc.) to reduce invoice-number false positives.
  - Improve **bbox matching** for split OCR tokens (normalize and fallback to digit-token union bbox).
- **footer_extractor.py:**
  - Refactor to **separate:** candidate generation → scoring → learning boost → calibration → AI fallback / routing.
  - Consistent data model: `score_raw` vs `score_calibrated`.
  - **Routing decisions** to AI/vision must use **Phase 14 thresholds** (quality + confidence), not only top-score.

### D8) Traceability and artifacts

- **run_summary.json** per-page must include:
  - `method_used`: `pdfplumber` | `ocr` | `ai_text` | `ai_vision`
  - `metrics`: `pdf_text_quality`, `ocr_text_quality`, `ocr_median_conf`, `ocr_mean_conf`, `low_conf_fraction`
  - **reason flags:** e.g. `["ocr_median_conf<70", "text_quality<0.5"]`
  - **artifact paths:** rendered image, OCR TSV, AI request/response (where applicable)
- When `method_used === "ai_vision"`, add **`vision_reason`** list (conditions that led to vision).

---

## NON-GOALS

- No change to GUI/desktop architecture.
- No new web services.
- No broad refactor of pipeline beyond touched modules.
- No model training; only deterministic scoring + calibrated confidence already in repo.

---

## TESTING / VERIFICATION

- **Unit or lightweight regression tests** for:
  - OCR TSV parsing: conf -1 excluded, word conf stored.
  - OCR metrics aggregation (median / mean / low fraction).
  - Tokenizer `extra_attrs` fallback and reading order.
  - Boundary detection: reduced false positives on sample inputs.
  - Line parser: classification improvements (hard/soft keywords).
- **Small benchmark script** over a set of PDFs to compare:
  - Number of AI calls (should go down or become more targeted).
  - Fraction of pages routed to vision (should be rare).
  - Extraction success rate of critical fields.

---

## ACCEPTANCE CRITERIA

- OCR token confidence is **persisted and used** (no placeholder 1.0).
- Page-level routing **follows Phase 14 rules** and is **explainable** in run_summary.json.
- **False invoice boundary detections decrease** without breaking multi-invoice PDFs.
- **Line-item parsing** drops fewer true items and **improves performance** (no O(n²) in hot path).
- **Footer/Header extraction** remains correct and is **easier to maintain** (clear separation, score_raw/score_calibrated, R4 thresholds for AI/vision).
- **Overall:** fewer unnecessary AI/vision calls while **maintaining or improving** critical field accuracy.

---

## PLAN MAPPING

| Deliverable | Plan | Notes |
|-------------|------|--------|
| D1 Token confidence | 15-01 | Token + ocr_abstraction + confidence_scoring; wave 1 |
| D2 pdfplumber tokenizer | 15-02 | tokenizer.py; wave 1 |
| D3 Text quality + routing | 15-03 | text_quality.py + routing; wave 2, depends 15-01, 15-02 |
| D4 DPI retry | 15-04 | pdf_renderer + orchestration R1; wave 2, depends 15-01 |
| D5 Boundary hardening | 15-05 | invoice_boundary_detection.py; wave 1 |
| D6 Line parser | 15-06 | invoice_line_parser.py; wave 1 |
| D7 Header/Footer | 15-07 | header_extractor + footer_extractor; wave 2 |
| D8 Traceability | 15-08 | run_summary method_used, metrics, reason flags, vision_reason; wave 3, depends 15-03 |

---

*Phase: 15-extraction-quality-hardening*  
*Discussion gathered: 2026-01-25 | Updated: 2026-01-25*
