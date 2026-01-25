# Phase 14: Extraction fallback optimization (pdfplumber → OCR → AI → vision) – Context

**Gathered:** 2026-01-25  
**Updated:** 2026-01-25  
**Status:** Ready for planning  
**Full spec:** see `14-DISCUSS.md`

---

## Phase Boundary

Optimize the extraction pipeline to be **robust, accurate, and cost-efficient** with a clear fallback chain: **pdfplumber → OCR → AI text → AI vision**. Per-page routing is driven by extraction confidence and text quality; only pages that need fallback are rendered/OCR’ed/AI’ed. No new architecture (subprocess + file-based artifacts only).

**Out of scope:** Client-server, HTTP services, new dependencies unless justified by research outcomes. GUI changes are optional (surface state/artifacts only).

---

## Current State (Summary)

- Page rendering to PNG at ~300 DPI exists; suitable for OCR and AI vision.
- OCR abstraction parses Tesseract TSV; token-level confidence not yet persisted.
- Confidence scoring and calibration exist but lack OCR token confidence input.
- PDF detection is document-level; routing must become **page-level and confidence-driven**.

---

## Research Tasks (R1–R4) and Constraints

Research in this phase is **limited and goal-oriented**: only decisions that are hard to reverse or significantly affect accuracy, cost, or performance. Outputs must be **concrete constants or rules in code**. Research must be **time-boxed**; **no research task may block unrelated implementation work.**

### R1 — OCR Rendering Parameters

- **Goal:** Optimal rendering for OCR and AI vision.
- **Deliverable:** Baseline DPI (e.g. 300); optional retry DPI rule (e.g. retry at 400 only if OCR mean_conf < X).

### R2 — OCR Confidence Aggregation

- **Goal:** How to summarize OCR confidence for routing.
- **Deliverable:** Chosen metric(s) (mean/median/trimmed); confirm conf == -1 excluded; threshold values (e.g. median_conf < 70 → AI).

### R3 — AI Vision Capabilities and Limits

- **Goal:** Vision used only when necessary, within technical limits.
- **Deliverable:** Confirmed input format (PNG/JPEG, max resolution/size); which provider/model; rule for when vision is allowed vs forbidden; cost vs text-only.

### R4 — AI Routing Rules (Text-only vs Vision)

- **Goal:** Deterministic, explainable triggers for AI.
- **Deliverable:** Final routing table (pdfplumber → OCR → AI text → AI vision); retry rules (max 1 retry, strict schema); when text-only suffices vs when vision is required.

---

## Implementation Decisions (Post-Research)

### 1. Fallback chain and routing

- **Step 1:** pdfplumber → field confidence + text quality. Accept if above thresholds.
- **Step 2:** OCR for **only needed pages** → field confidence + OCR quality. Accept if above thresholds.
- **Step 3:** AI **text-only** when text/OCR quality is acceptable.
- **Step 4:** AI **vision** when both pdfplumber and OCR text are poor.

Two signals: **(1) extraction confidence** (existing), **(2) text quality score** (new, per page). Exact thresholds come from R1–R4.

### 2. Token model and OCR quality

- Add `Optional[float] confidence` to Token; persist OCR confidence from TSV.
- Exclude `conf == -1` rows from word tokens. OCR aggregation choice per R2.

### 3. pdfplumber tokenizer

- `use_text_flow=True`; `extra_attrs=["fontname","size"]` with safe fallback; improve reading order via line clustering.

### 4. Text quality scoring

- Deterministic score [0..1] per page; separate `pdf_text_quality` and `ocr_text_quality`.

### 5. Page-level orchestration

- Page-level routing implementing the four-step chain; only necessary pages rendered/OCR’ed.

### 6. AI interfaces

- Text-only and vision-based extraction; strict JSON schema; retry once on invalid output. Vision format and limits per R3; routing rules per R4.

### 7. Artifacts and run_summary

- **run_summary.json** per-page: `method_used`, confidence values, text quality scores, artifact paths. Must **fully explain *why* OCR or AI was used.**

### Claude's discretion

- Exact text quality formula (weights, factors) within the agreed factors.
- Internal structure of text_quality module and pipeline wiring.
- Calibration use (existing isotonic) before 0.95 gating — optional but recommended.

---

## Implementation Task List (from 14-DISCUSS)

1. Token model update — Optional[float] confidence, persist OCR into Token.confidence.
2. pdfplumber tokenizer — use_text_flow=True, extra_attrs with safe fallback, line clustering.
3. Text quality scoring — deterministic [0..1] per page, separate pdf vs OCR.
4. Page-level orchestration — pdfplumber → OCR → AI text → AI vision; only necessary pages.
5. AI interfaces — text-only + vision; strict JSON; retry once.
6. Artifacts and traceability — run_summary.json with method_used, confidences, text quality, artifact paths; explain *why*.

---

## Acceptance Criteria

- Pipeline **deterministically** selects **minimal necessary method per page**.
- **AI vision only when text-based methods are demonstrably insufficient.**
- Critical fields **calibrated confidence ≥ 0.95** or explicitly flagged.
- **run_summary.json fully explains *why* OCR or AI was used.**
- Architecture remains **subprocess + file-based**, no new services.

---

## Specific Ideas

- “Minimal necessary method per page” — avoid OCR/AI when pdfplumber is sufficient.
- run_summary must make routing **explainable** (why OCR or AI was used).
- File-based artifacts only; no client-server.

---

## Deferred Ideas

- OCR preprocessing (deskew, contrast): only if research strongly justifies.
- Alternative OCR engines: baseline Tesseract TSV; others out of scope unless justified.

---

## Existing Codebase Anchors

- `pdf_renderer.py` — PNG at ~300 DPI; align with research (R1).
- `ocr_abstraction.py` — TSV parsing; add Token.confidence and aggregation (R2).
- `pdf_detection.py` — document-level today; add page-level routing.
- `confidence_scoring.py` — field confidence exists; add OCR token input and text quality.

---

*Phase: 14-extraction-fallback-optimization-pdfplumber-ocr-ai-vision*  
*Context gathered: 2026-01-25 | Updated: 2026-01-25*
