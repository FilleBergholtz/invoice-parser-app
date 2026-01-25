# Phase 15: Extraction quality hardening — Verification

**Skapad:** 2026-01-25  
**Spec:** 15-DISCUSS.md

Verifiering av D1–D8 och acceptanskriterier enligt 15-DISCUSS.md. Uppdateras när planer (15-01 …) är definierade.

---

## 1. Per-plan checks (from SUMMARY)

| Plan | Deliverable | Check | Resultat |
|------|-------------|--------|----------|
| 15-01 | D1 | Token.confidence, ocr metrics, confidence_scoring no placeholder 1.0 | |
| 15-02 | D2 | use_text_flow, extra_attrs fallback, line clustering | |
| 15-03 | D3 | score_text_quality/score_ocr_quality, R4 routing | |
| 15-04 | D4 | DPI retry when mean_conf&lt;55, max 1, artifacts show DPI | |
| 15-05 | D5 | Boundary: extra signal beyond faktura+alphanum | |
| 15-06 | D6 | HARD/SOFT keywords, no O(n²), bbox amount | |
| 15-07 | D7 | Header neg labels/bbox; Footer separation + R4 | |
| 15-08 | D8 | method_used, metrics, reason flags, vision_reason | |

*Uppdatera resultat efter varje plan-SUMMARY.*

---

## 2. Deliverable-level checks (15-DISCUSS)

| ID | Deliverable | Verifiering |
|----|-------------|-------------|
| D1 | Token confidence plumbing | Token.confidence satt från OCR; conf&lt;0 exkluderad; ocr_median/mean/low_conf_fraction; confidence_scoring använder verklig confidence |
| D2 | pdfplumber tokenizer | use_text_flow=True; extra_attrs med safe fallback; läsordning via line clustering |
| D3 | Text quality + routing | text_quality.py: score_text_quality, score_ocr_quality [0..1]; R4-routing använder TEXT_QUALITY_THRESHOLD |
| D4 | DPI retry (R1) | Retry vid mean_conf&lt;55, max 1 per sida; artifacts visar använd DPI |
| D5 | Boundary hardening | Färre falska positiva; kräv extra signal utöver “faktura”+alfanum |
| D6 | Line parser | HARD/SOFT keywords; inga O(n²) index-lookups; bbox-baserad amount-detektion |
| D7 | Header/Footer | Header: negativa labels, bbox för split-tokens. Footer: separation candidate→scoring→learning→calibration→routing; R4-trösklar |
| D8 | Traceability | run_summary: method_used, metrics, reason flags, artifact paths, vision_reason vid ai_vision |

---

## 3. Unit / regression tests (15-DISCUSS)

- OCR TSV: conf -1 exkluderad, word conf sparad.
- OCR metrics: median / mean / low fraction.
- Tokenizer: extra_attrs fallback och läsordning.
- Boundary detection: färre falska positiva på sample-inputs.
- Line parser: hard/soft-klassificering.

---

## 4. Benchmark (15-DISCUSS)

Kör benchmark över ett set PDF:er och jämför:

- Antal AI-anrop (ska minska eller bli mer riktade).
- Andel sidor till vision (ska vara sällsynt).
- Extraktionsframgång för kritiska fält (behåll eller förbättra).

---

## 5. Acceptance criteria (15-DISCUSS)

1. OCR token confidence persisterad och använd (ingen placeholder 1.0).
2. Per-sida routing följer Phase 14-regler och är förklarbar i run_summary.json.
3. Färre falska gränsdetektioner utan att multi-invoice-PDF:er går sönder.
4. Radparsning tappar färre giltiga rader och prestanda förbättrad.
5. Footer/Header korrekt och mer underhållbart; AI/vision-routing använder R4-trösklar.
6. Färre onödiga AI/vision-anrop; kritisk fältnoggrannhet bibehållen eller förbättrad.

---

*Skapad 2026-01-25 — Phase 15 extraction quality hardening — Spec: 15-DISCUSS.md*
