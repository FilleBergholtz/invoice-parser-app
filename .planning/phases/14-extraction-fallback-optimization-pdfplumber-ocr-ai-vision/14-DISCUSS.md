# Phase 14: Extraction fallback optimization (pdfplumber → OCR → AI → vision) – Discussion / Spec

**Diskuterad:** 2026-01-25  
**Uppdaterad:** 2026-01-25  
**Källa:** /gsd:discuss-phase 14

---

## OBJECTIVE

Optimize the extraction pipeline to be **robust, accurate, and cost-efficient**:

1. **Try pdfplumber first** (searchable PDFs).
2. If extraction confidence < 0.95 **OR** extracted text quality is poor → **run OCR** for the relevant pages.
3. If OCR still yields < 0.95 **OR** OCR text quality is poor → **use AI (text-only)**.
4. If both pdfplumber text and OCR text are poor (AI likely to misunderstand) → send the **PDF page as an image** to multimodal AI (“vision”).

---

## SCOPE / CONSTRAINTS

- **Desktop app (PySide6)**, engine runs as subprocess.
- **File-based artifacts only** (run_summary.json, Excel, images, OCR output).
- **No client-server architecture, no HTTP services.**
- **Avoid new dependencies** unless justified by research outcomes.

---

## CURRENT STATE (SUMMARY)

- **Page rendering** to PNG at ~300 DPI already exists and is suitable for OCR and AI vision.
- **OCR abstraction** parses Tesseract TSV but token-level confidence is not yet persisted.
- **Confidence scoring and calibration** already exist but lack OCR token confidence input.
- **PDF detection** is document-level; routing must become **page-level and confidence-driven**.

---

## RESEARCH TASKS (LIMITED, GOAL-ORIENTED)

This phase includes **targeted research tasks** strictly limited to decisions that are hard to reverse or significantly affect accuracy, cost, or performance.

**Purpose:** Finalize thresholds and technical parameters before full implementation. **No open-ended exploration.**

### R1 — OCR Rendering Parameters

**Goal:** Determine optimal rendering strategy for OCR and AI vision.

**Questions to answer:**

- Is 300 DPI sufficient for the majority of invoices, or is a retry at 400 DPI needed?
- Does rerendering only failed pages materially improve OCR confidence?
- Are there clear cases where higher DPI degrades performance without accuracy gains?

**Deliverable:**

- Final baseline DPI (e.g. 300)
- Optional retry DPI rule (e.g. retry at 400 only if OCR mean_conf < X)

---

### R2 — OCR Confidence Aggregation

**Goal:** Define how OCR confidence should be summarized and used for routing decisions.

**Questions to answer:**

- Should routing use mean, median, or trimmed mean OCR confidence?
- What fraction of low-confidence tokens (e.g. conf < 50) correlates with parsing failure?
- Confirm that TSV rows with conf == -1 are excluded from word confidence.

**Deliverable:**

- Chosen OCR confidence metric(s)
- Threshold values used in routing (e.g. median_conf < 70 → AI)

---

### R3 — AI Vision Capabilities and Limits

**Goal:** Ensure AI vision is used only when necessary and within technical limits.

**Questions to answer:**

- Which AI provider/model is used for vision?
- Supported inputs: PNG/JPEG? Max resolution or file size? Multiple images per request?
- Cost implications compared to text-only AI.

**Deliverable:**

- Confirmed AI vision input format
- Max image resolution to send
- Explicit rule for when vision is allowed vs forbidden

---

### R4 — AI Routing Rules (Text-only vs Vision)

**Goal:** Define deterministic, explainable triggers for AI usage.

**Questions to answer:**

- When is text-only AI sufficient despite low parser confidence?
- When must vision be used because text quality is too poor?
- Should AI be retried in vision mode if text-only AI fails schema validation?

**Deliverable:**

- Final routing decision table: pdfplumber → OCR → AI text → AI vision
- Retry rules (max 1 retry, strict schema)

---

## RESEARCH CONSTRAINTS

- Research must be **time-boxed**.
- Research outputs must result in **concrete constants or rules in code**.
- **No research task may block unrelated implementation work.**

---

## IMPLEMENTATION TASKS (POST-RESEARCH)

1. **Token model update**
   - Add Optional[float] confidence to Token.
   - Persist OCR confidence into Token.confidence.

2. **pdfplumber tokenizer improvements**
   - Ensure use_text_flow=True.
   - Support extra_attrs=["fontname","size"] with safe fallback.
   - Improve reading order via line clustering.

3. **Text quality scoring**
   - Implement deterministic text quality score [0..1] per page.
   - Separate pdfplumber text quality and OCR text quality.

4. **Page-level orchestration**
   - Implement page-level routing: pdfplumber → OCR → AI text → AI vision.
   - Ensure only necessary pages are rendered/OCR’ed.

5. **AI interfaces**
   - Support both text-only and vision-based extraction.
   - Enforce strict JSON schema and retry once on invalid output.

6. **Artifacts and traceability**
   - Write per-page decision metadata to run_summary.json:
     - method_used
     - confidence values
     - text quality scores
     - artifact paths (images, OCR TSV, AI responses)
   - **Rekommendation A:** När `method_used` är `ai_vision`, inkludera även **vision_reason**: en array med de tröskelvillkor som ledde till vision, t.ex. `["pdf_text_quality < 0.5", "ocr_median_conf < 70"]`. Underlättar debugging, användarstöd och framtida threshold-justering.

---

## ACCEPTANCE CRITERIA

- Pipeline **deterministically selects the minimal necessary extraction method per page**.
- **AI vision is used only when text-based methods are demonstrably insufficient.**
- Critical fields reach **calibrated confidence ≥ 0.95** or are explicitly flagged.
- **run_summary.json fully explains *why* OCR or AI was used.**
- Architecture remains **subprocess + file-based** with no new services.

---

*Phase: 14-extraction-fallback-optimization-pdfplumber-ocr-ai-vision*  
*Discussion gathered: 2026-01-25 | Updated: 2026-01-25*
