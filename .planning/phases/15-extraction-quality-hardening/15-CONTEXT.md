# Phase 15: Extraction quality hardening (OCR confidence + routing + parser robustness) – Context

**Gathered:** 2026-01-25  
**Updated:** 2026-01-25  
**Status:** Ready for planning  
**Depends on:** Phase 14 (Extraction fallback optimization)

---

## Phase Boundary

Hårdna extraktionskvaliteten genom **OCR confidence-tillämpning**, **routing-stabilitet** och **parser-robusthet**. Bygg vidare på Phase 14:s fallback-kedja och text quality; ingen ny arkitektur. Fokus: färre fel vid kantfall, tydligare beslut om när OCR/AI används, och parsers som inte kraschar eller ger felaktiga fält vid dålig text.

**In scope:**
- **OCR confidence:** Tröskeljustering, användning i UI/logg (t.ex. visa median_conf eller low_conf_fraction där det hjälper), eventuell DPI-retry-finkalibrering.
- **Routing:** Stabilisera och dokumentera routing-beslut; undvik flippande mellan metoder vid marginalfall; tydlig “vision_reason” och gränsfall-hantering.
- **Parser robustness:** Tålighet mot tom text, konstiga tecken, för korta/långa rader; defensiv parsing i header/total/line-item-stegen så att enstaka fel inte förstör hela dokumentet.

**Out of scope:** Nya extraction-metoder, nya AI-modeller, client-server, stor refaktor av pipeline-arkitekturen.

---

## Current State (Summary)

- Phase 14 levererar: Token.confidence, ocr_page_metrics (mean/median/low_conf_fraction), text_quality (pdf/ocr), per-page routing (pdfplumber → OCR → AI text → AI vision), run_summary med method_used och vision_reason.
- Trösklar (t.ex. median_conf 70, text_quality 0.5) är definierade men kan behöva justering utifrån riktiga fakturor.
- Parsers (header, total, line items) antas ofta “snäll” input; kantfall (tomma sidor, mycket brus, konstiga tecken) kan ge oväntade resultat.

---

## Goals

1. **OCR confidence:** Säkerställ att confidence-mått används konsekvent (routing, DPI-retry, run_summary) och att trösklar eller deras användning kan finjusteras/observeras (logg, UI, eller konfig).
2. **Routing:** Gör routing-beslut stabila och förutsägbara vid marginalfall; tydlig dokumentation och eventuella “tie-break”-regler eller buffer (hysteresis) så att små fluktuationer inte byter metod.
3. **Parser robustness:** Förbättra header-, total- och line-item-parsning mot tomma/brusiga/konstiga inputs så att systemet sätter REVIEW eller tomma fält i stället för krasch eller felaktiga värden.

---

## Implementation Directions (to be refined in plans)

- **OCR confidence:** Granska var median_conf, low_conf_fraction och mean_conf används; lägg till loggning eller UI-visning där det underlättar felsökning; överväg konfigurerbara trösklar eller dokumentation av “rekommenderade” värden.
- **Routing:** Definiera explicita regler för lika confidence/text_quality (t.ex. preferera pdfplumber över OCR över AI); eventuell liten buffer (hysteresis) kring trösklar för att undvika flipp; se till att vision_reason alltid reflekterar verkliga villkor.
- **Parser robustness:** Null/empty-checks, safe parsing av tal och datum, max-längd eller truncation där det är meningsfullt; returnera “empty/safe” default istället för exception där det passar; behåll eller förstärk REVIEW-path när data är osäker.

---

## Acceptance Criteria (draft)

- OCR confidence-mått används konsekvent i routing och run_summary; trösklar är dokumenterade eller konfigurerbara.
- Routing visar inget onödigt “flipp” mellan metoder vid marginella inputs; vision_reason och method_used är konsekventa.
- Parsers (header, total, line items) hanterar tom/brusig/konstig text utan krasch och med tydlig REVIEW eller tomt fält där lämpligt.
- Befintliga tester och Phase 14-verifiering förblir passerande.

---

## Existing Codebase Anchors

- `src/pipeline/ocr_abstraction.py` — ocr_page_metrics, OCR_MEDIAN_CONF_ROUTING_THRESHOLD, DPI-retry (mean_conf).
- `src/pipeline/text_quality.py` — score_text_quality, score_ocr_quality.
- `src/run_summary.py` — extraction_details, method_used, vision_reason.
- Pipeline/orchestration (R4-routing) — process_pdf, extraction_detail.
- Header/total/line parsing — header_extractor, total extraction, invoice_line_parser etc.

---

*Phase: 15-extraction-quality-hardening*  
*Context gathered: 2026-01-25 | Updated: 2026-01-25*
