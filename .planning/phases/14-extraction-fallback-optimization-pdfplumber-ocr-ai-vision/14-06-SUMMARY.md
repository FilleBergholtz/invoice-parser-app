# 14-06: Orchestration + run_summary — Summary

**Done:** 2026-01-25

## Objective

Implement page-level (per virtual invoice) fallback routing and extend run_summary with method_used, vision_reason, text quality and artifact paths. Per 14-RESEARCH R4 and 14-CONTEXT §5, §7: pdfplumber → OCR → AI text → AI vision; only run OCR when pdfplumber does not meet thresholds; record why OCR/AI was used.

## Completed tasks

1. **R4 routing in process_pdf** (`src/cli/main.py`)
   - When `compare_extraction` is True: run pdfplumber first with `return_last_page_tokens=True`.
   - Compute `pdf_text_quality` from last-page tokens via `score_text_quality`, and `critical_conf = min(invoice_number_conf, total_conf)`.
   - If `critical_conf >= 0.95` and `pdf_text_quality >= 0.5` → **accept pdfplumber**, set `extraction_source="pdfplumber"`, `extraction_detail`, skip OCR.
   - Else run OCR with `ocr_render_dir=output_dir/artifacts/pages` (creating `artifacts/pages` when present). Get last-page tokens, `ocr_text_quality = score_ocr_quality(tokens)`, `ocr_metrics = ocr_page_metrics(tokens)`.
   - If `critical_conf_ocr >= 0.95`, `ocr_median >= 70`, `ocr_text_quality >= 0.5` → **accept OCR**, set `extraction_source="ocr"`, `extraction_detail`.
   - Else keep existing _choose_best_extraction_result; set `extraction_source` and `extraction_detail` on the chosen result. Constants: `TEXT_QUALITY_THRESHOLD=0.5`, `CRITICAL_FIELDS_CONF_THRESHOLD=0.95`, `OCR_MEDIAN_CONF_ROUTING_THRESHOLD` from ocr_abstraction.

2. **process_virtual_invoice extensions**
   - Optional `ocr_render_dir` and `return_last_page_tokens`. When `return_last_page_tokens=True`, returns `(VirtualInvoiceResult, {"last_page_tokens": tokens})`; otherwise returns only the result.
   - OCR render uses `ocr_render_dir` when given, else `output_dir/ocr_render`. Inner try/finally so header/footer logic stays in the same try as the token loop.

3. **RunSummary and VirtualInvoiceResult**
   - `RunSummary.extraction_details: Optional[List[Dict[str, Any]]]` — list of per–virtual-invoice extraction metadata.
   - `VirtualInvoiceResult.extraction_detail: Optional[Dict[str, Any]]` — method_used, pdf_text_quality, ocr_text_quality, ocr_median_conf, vision_reason (None for pdfplumber/ocr; for future ai_vision).
   - In process_batch, when a virtual result has `extraction_detail`, append `{**detail, "virtual_invoice_id", "filename"}` to `summary.extraction_details`.

4. **Artifacts**
   - When `compare_extraction` and `output_dir` are set, `output_dir/artifacts/pages` is created and used as OCR render dir so rendered images go under artifacts. run_summary can later reference these paths; full artifact layout (ocr/, ai/) can be extended in a follow-up.

## Files changed

- `src/cli/main.py` — R4 routing in process_pdf; `ocr_render_dir`, `return_last_page_tokens` and inner try/finally in process_virtual_invoice; imports for `score_text_quality`, `score_ocr_quality`, `ocr_page_metrics`, `OCR_MEDIAN_CONF_ROUTING_THRESHOLD`; appending to `summary.extraction_details`.
- `src/run_summary.py` — `extraction_details` on RunSummary.
- `src/models/virtual_invoice_result.py` — `extraction_detail` and extended `extraction_source` doc.

## Verification

- Pipeline prefers pdfplumber when conf ≥ 0.95 and pdf_text_quality ≥ 0.5; otherwise runs OCR and accepts when ocr thresholds pass; otherwise uses _choose_best.
- run_summary.extraction_details is populated with method_used, text quality and ocr_median_conf; vision_reason remains None until ai_vision is wired (14-05 provides the hook).
- Architecture remains file-based; no new services.

## Not in this plan

- DPI retry (300 → 400 when mean_conf < 55) is implemented in pdf_renderer (14-04) but not yet triggered from orchestration; can be added where OCR is run.
- AI vision branch (call extract_total_with_ai(..., image_path=...) when text_quality < 0.5 and set method_used="ai_vision", vision_reason=[...]) is prepared (extraction_detail has vision_reason) but not yet invoked from process_pdf; can be added after choosing best result when conf < 0.95 and best_text_quality < 0.5.
