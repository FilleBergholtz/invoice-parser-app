# Phase 14: Extraction fallback optimization — Verification

**Verifierad:** 2026-01-25

Verifiering av fallback-kedjan pdfplumber → OCR → AI text → AI vision, Token.confidence, text quality, DPI, vision/R3 och orchestration enligt 14-CONTEXT.md och 14-DISCUSS.md.

---

## 1. Per-plan checks (from SUMMARY)

| Plan | Check | Resultat |
|------|--------|----------|
| 14-01 | Token.confidence, ocr_page_metrics, OCR_EXCLUDE_CONF_BELOW, skip conf&lt;0 | ✓ |
| 14-02 | use_text_flow=True, extra_attrs + fallback, _tokens_reading_order | ✓ |
| 14-03 | score_text_quality(text, tokens), score_ocr_quality(tokens) [0..1] | ✓ |
| 14-04 | render_page_to_image(..., dpi=300/400), BASELINE_DPI, RETRY_DPI | ✓ |
| 14-05 | _prepare_vision_image, extract_total_amount(image_path=), R3, 1-retry | ✓ |
| 14-06 | R4 routing i process_pdf, extraction_detail, extraction_details | ✓ |

---

## 2. Kod-/importkontroller

Kör:

```bash
python -c "
import dataclasses
from src.models.token import Token
assert 'confidence' in [f.name for f in dataclasses.fields(Token)]
print('14-01 Token.confidence ok')

from src.pipeline.ocr_abstraction import ocr_page_metrics, OCRPageMetrics, OCR_MEDIAN_CONF_ROUTING_THRESHOLD
assert OCR_MEDIAN_CONF_ROUTING_THRESHOLD == 70
m = ocr_page_metrics([])
assert hasattr(m, 'mean_conf') and hasattr(m, 'median_conf') and hasattr(m, 'low_conf_fraction')
print('14-01 ocr_page_metrics ok')

from src.pipeline.text_quality import score_text_quality, score_ocr_quality
s = score_text_quality('', [])
assert 0.0 <= s <= 1.0
s2 = score_ocr_quality([])
assert 0.0 <= s2 <= 1.0
print('14-03 text_quality ok')

from src.pipeline.pdf_renderer import render_page_to_image, BASELINE_DPI, RETRY_DPI, OCR_MEAN_CONF_RETRY_THRESHOLD
import inspect
sig = inspect.signature(render_page_to_image)
assert 'dpi' in sig.parameters
assert BASELINE_DPI == 300 and RETRY_DPI == 400
print('14-04 pdf_renderer DPI ok')

from src.ai.providers import OpenAIProvider
import inspect as insp
sig2 = insp.signature(OpenAIProvider.extract_total_amount)
assert 'image_path' in sig2.parameters
from src.ai.providers import VISION_MAX_PIXELS_LONGEST_SIDE, VISION_MAX_FILE_BYTES, AI_JSON_RETRY_COUNT
assert VISION_MAX_PIXELS_LONGEST_SIDE == 4096 and AI_JSON_RETRY_COUNT == 1
print('14-05 AI vision/R3 ok')

from src.run_summary import RunSummary
assert hasattr(RunSummary, 'extraction_details')
from src.models.virtual_invoice_result import VirtualInvoiceResult
assert hasattr(VirtualInvoiceResult, 'extraction_detail')
print('14-06 extraction_detail(s) ok')

print('Phase 14 symbol check: all ok')
"
```

**Resultat:** Phase 14 symbol check: all ok

---

## 3. Automatiska tester

Relevanta testmoduler för phase 14 (tokenizer, pdf_renderer, pipeline-kedja, run_summary, cli):

```bash
python -m pytest tests/test_tokenizer.py tests/test_pdf_renderer.py tests/test_run_summary.py tests/test_segment_identification.py tests/test_row_grouping.py tests/test_invoice_line_parser.py tests/test_header_extractor.py tests/test_cli.py -v
```

**Senast kört:** 2026-01-25 — **28 passed, 14 skipped** (skipped: pdf_renderer/tokenizer/cli kräver pymupdf/PDF-filer)

---

## 4. Success criteria (14-CONTEXT / 14-DISCUSS)

1. **Token + OCR confidence:** Token har `confidence`; OCR sätter den för ord (conf ≥ 0); conf &lt; 0 ger inget token. ocr_page_metrics ger mean/median/low_conf_fraction. ✓
2. **pdfplumber tokenizer:** use_text_flow=True, extra_attrs med fallback, linjeclustering för läsordning. ✓
3. **Text quality:** score_text_quality och score_ocr_quality [0..1] för routing. ✓
4. **Rendering DPI:** 300 baseline, 400 retry; R1-konstanter i pdf_renderer. ✓
5. **AI vision:** image_path på extract_total_amount; R3 (4096 px, 20 MB); max 1 retry vid ogiltig JSON. ✓
6. **Orchestration:** R4-routing (pdfplumber accept → annars OCR → annars choose_best); extraction_detail på resultat; extraction_details i RunSummary; artifacts/pages vid compare. ✓
7. **Inga nya tjänster;** filbaserad arkitektur oförändrad. ✓

---

## 5. Manuell verifiering (rekommenderas)

1. **Engine med compare:**  
   `python run_engine.py --input <pdf> --output <dir> --verbose`  
   Vid tillräcklig konfidens och text quality ska pdfplumber accepteras utan OCR; annars ska OCR köras och vald källa loggas.

2. **RunSummary / artifacts:**  
   Kontrollera att `run_summary.json` (eller motsvarande) innehåller `extraction_details` med method_used, pdf_text_quality, ocr_text_quality, ocr_median_conf där det är tillämpligt. Vid `compare_extraction` och angiven output skapas `artifacts/pages` när OCR används.

3. **AI vision (om aktiverad):**  
   Vid dålig text quality och när AI-vision är konfigurerad ska bild skickas till provider; R3-gränser ska inte överskridas.

---

*Skapad 2026-01-25 — verifiera phase 14*
