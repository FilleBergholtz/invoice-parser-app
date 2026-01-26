# Phase 16 — Text-layer routing (OCR-skip)

## Målbild (OCR-01..OCR-04)
Per sida: använd text-layer (pdfplumber) när texten är “tillräcklig”; annars OCR. Beslutet ska vara konfigurerbart via `min_text_chars` + ankare. OCR/pdfplumber‑jämförelse får inte krascha (KeyError: 4).

## Föreslagna heuristiker för “tillräcklig text”
Basera på pdfplumber‑text per sida (inte dokumentnivå). Behåll kraven från OCR‑02 och komplettera med robusta stödsignaler:

1. **Basvillkor (OCR‑02)**  
   - `min_text_chars`: minst N tecken i `page.extract_text()` (trim)  
   - **ankare 1**: matcha “Faktura” (case‑insensitive, tillåt whitespace/tabb/kolon)  
   - **ankare 2**: matcha minst ett extra ankare, t.ex. “Sida 1/2” eller “Ramirent”

2. **Stödsignaler (för robusthet, men ej krav)**  
   - `min_word_tokens` (från `extract_words`): t.ex. >= 60  
   - `text_quality` (befintlig `score_text_quality`): t.ex. >= 0.5  
   - `alpha_num_ratio`: andel alfanumeriskt i text (faller ut i `score_text_quality`)

3. **Per‑sida logik (föreslagen)**
   - Om basvillkor uppfylls → **skip OCR** för sidan  
   - Om basvillkor ej uppfylls, men `text_quality` och `min_word_tokens` är höga → **tillåt text‑layer** (redundant säkerhet)  
   - Annars → **OCR fallback** för sidan

Kommentar: På sidor utan rubrik/huvud (“items‑pages”) kan ankare missas. Därför bör stödsignaler få “rädda” text‑layer för sidor med bra tabelltext. Kravet OCR‑02 uppfylls ändå genom att basvillkor styr default‑beslutet.

## Konfigurerbara nycklar och default
Förslag på nya config‑nycklar (i profil, t.ex. `configs/profiles/default.yaml`):

```yaml
ocr_routing:
  min_text_chars: 500
  required_anchors:
    - "Faktura"
  extra_anchors:
    - "Sida\\s+\\d+/\\d+"
    - "Ramirent"
  min_word_tokens: 60
  min_text_quality: 0.50
  allow_quality_override: true
  cache_pdfplumber_text: true
```

Relaterad nyckel (från v2.1 requirements):

```yaml
table_parser_mode: "auto"  # auto|text|pos
```

Motivering:
- `min_text_chars=500` och ankare uppfyller OCR‑02 rakt av.
- `min_word_tokens` och `min_text_quality` minskar risken för falskt OCR på text‑tunga sidor utan ankare.
- `allow_quality_override` gör att man kan slå av stödlogiken om man vill vara strikt.
- `cache_pdfplumber_text` undviker dubbel‑extraktion per sida.

## Var i pipeline checken ska ligga
Föreslagen placering (per sida, tidigt i extraktion):

1. **I `process_virtual_invoice` (primär plats)**  
   - Vid token‑extraktion: först pdfplumber‑text + tokens  
   - Kör “tillräcklig text”‑check per sida  
   - Om **true**: behåll pdfplumber‑tokens och skip OCR för sidan  
   - Om **false**: render + OCR för den sidan

2. **I `detect_invoice_boundaries` (sekundär plats)**  
   - När boundaries behöver tokens per sida: gör samma per‑sida routing  
   - Viktigt för mixed‑PDF där vissa sidor saknar text‑layer

3. **I `process_pdf` compare‑path**  
   - Nu körs pdfplumber och OCR separat och väljer bästa.  
   - När per‑sida routing finns kan compare‑path förenklas:  
     - Kör pdfplumber överallt → OCR endast där text‑layer ej räcker.  
     - Minska körtid och undvik OCR‑fel på bra text.

## Trolig orsak till `KeyError: 4` och fix‑strategier
Trolig källa: `pytesseract.image_to_data(..., output_type=4)` i `ocr_abstraction.py`.

Möjlig förklaring:
- I vissa pytesseract‑versioner är `Output` en enum/dict som inte innehåller nyckeln `4`.  
  Då uppstår `KeyError: 4` i `pytesseract.pytesseract`.

Fix‑strategier:
1. **Byt till stabil output_type**  
   - Använd `pytesseract.Output.STRING` (TSV‑string) och parsa TSV själv (som nu),  
     eller `pytesseract.Output.DICT` och slippa TSV‑parsing.
2. **Defensiv fallback**  
   - Om `Output.TSV` saknas → fallback till `Output.STRING` i stället för `4`.  
3. **Validera output i compare‑path**  
   - Om OCR faller, fortsätt med pdfplumber‑resultat i compare‑path (utan crash).

## Risker
- **Ankare saknas på items‑sidor** → risk för onödig OCR om bara “Faktura” + extra ankare krävs.
- **Text‑layer med brus** (t.ex. vattensstämpel) → risk för falsk “tillräcklig text”.
- **OCR‑skip i mixed‑PDF** → per‑sida routing måste stödja både text och OCR i samma faktura.
- **Prestanda**: dubbel extraktion (text + OCR) om caching saknas.

## Testidéer
- **Enhets‑/routing‑tester**  
  - sida med text >= 500 + “Faktura” + “Sida 1/2” → OCR skip  
  - sida med text < 500 → OCR används  
  - sida utan ankare men hög `text_quality` + många tokens → OCR skip om override är på  
  - sida med låg `text_quality` trots många tecken → OCR används

- **Integrationstester (compare‑path)**  
  - Mixed‑PDF: sida 1 text‑layer, sida 2 bild → OCR bara på sida 2  
  - OCR‑fall som tidigare gav `KeyError: 4` → fallback till pdfplumber utan crash  
  - Verifiera att `extraction_detail` innehåller per‑sida routingbeslut

- **Regression**  
  - Kör befintliga `tests/test_pdf_detection.py` och `tests/test_tokenizer.py`  
  - Kontrollera att `process_pdf(compare_extraction=True)` inte kräver OCR för text‑tunga sidor
