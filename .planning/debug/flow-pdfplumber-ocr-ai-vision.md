# Debug: Flöde pdfplumber → OCR → AI → vision

**Skapat:** 2026-01-25  
**Syfte:** Kartlägga hur flödet pdfplumber → OCR → AI → vision fungerar och verifiera att det fungerar korrekt.

---

## 1. Önskat flöde (enligt Phase 14 / R4)

Tänkt kedja:

1. **pdfplumber** – textextraktion från PDF (snabb, bra när text är väl renderad).
2. **OCR** – när pdfplumber inte räcker eller textkvaliteten är för låg.
3. **AI (text)** – när konfidens för totalsumma/fakturanummer är under tröskel (~0.95).
4. **AI (vision)** – när textkvaliteten är under tröskel så att text-only AI inte räcker; skicka sidbild till vision-API.

---

## 2. Faktiskt flöde i koden

### 2.1 Token-nivå: pdfplumber vs OCR (compare_extraction)

**Var:** `src/cli/main.py`, `process_pdf()` (ca rad 762–921).

- **compare_extraction=True (default):**
  1. Kör `process_virtual_invoice(..., "pdfplumber")` för sidintervallet.
  2. Beräkna `pdf_text_quality` (text_quality) och `critical_conf` (min(invoice_no_conf, total_conf)).
  3. **Acceptera pdfplumber** om  
     `critical_conf >= 0.95` och `pdf_text_quality >= 0.5`  
     → `extraction_source = "pdfplumber"`, klart för den virtuella fakturan.
  4. Annars kör `process_virtual_invoice(..., "ocr")` för samma intervall.
  5. **Acceptera OCR** om  
     `critical_conf_ocr >= 0.95`, `ocr_median >= 70`, `ocr_text_quality >= 0.5`  
     → `extraction_source = "ocr"`.
  6. Annars **välj bäst** mellan pdf- och OCR-resultat med `_choose_best_extraction_result(r_pdf, r_ocr)` (prioritet: validation_passed, total_confidence, invoice_number_confidence).  
     → `extraction_source = "pdfplumber" | "ocr"`.

- **compare_extraction=False:**  
  En enda körning med `process_virtual_invoice(..., extraction_path)` där `extraction_path = route_extraction_path(doc)` ("pdfplumber" eller "ocr").  
  → `extraction_source = extraction_path`.

**Slutsats:** pdfplumber ↔ OCR är implementerat på **token-nivå** (vilken textextraktion som används). Det är inte en sekventiell “först pdfplumber, sedan OCR i samma körning”, utan “kör båda, välj en”.

### 2.2 Inom en process_virtual_invoice (en extraction_path)

**Var:** `src/cli/main.py`, `process_virtual_invoice()` (ca rad 423–611).

För varje sida i intervallet:

1. **Tokens:** antingen pdfplumber eller OCR (bestämt av `extraction_path`).
2. **Rader/segment:** row_grouping, segment_identification, wrap_detection.
3. **Header:** `extract_header_fields(header_segment, invoice_header)`.
4. **Footer/total:** `extract_total_amount(...)` anropas inifrån `extract_with_retry(extract_total, target_confidence=0.90, max_attempts=5)` (`retry_extraction`).
5. **AI-enrichment (annat än total-fallback):** om `get_ai_enabled()` och `get_ai_endpoint()` finns anropas `AIClient.enrich_invoice()` för att berika header/rader/total. Det är **inte** samma som AI-fallback för totalsumma.
6. **Validering:** `validate_invoice(invoice_header, all_invoice_lines)` → status OK/PARTIAL/REVIEW/FAILED.

AI-fallback för **totalsumma** sker alltså inuti `extract_total_amount`, inte i main.

### 2.3 AI-fallback för totalsumma (text)

**Var:** `src/pipeline/footer_extractor.py`, `extract_total_amount()` (ca rad 249–720) och `_try_ai_fallback()` (ca rad 104–148).

- Efter heuristik, scoring och kalibrering:
  - Om `get_ai_enabled()` och API-nyckel finns:
    - Om det finns kandidater och **bästa heuristik-score >= 0.95** → AI anropas **inte**.
    - Annars (score < 0.95 eller inga kandidater) anropas  
      `_try_ai_fallback(footer_segment, line_items, invoice_header, candidates=..., page_context=page_context_for_ai)`.
- `_try_ai_fallback` bygger `footer_text` och `page_context` och anropar  
  `extract_total_with_ai(footer_text, line_items_sum, candidates=cand, page_context=page_context)`.

**Viktigt:** `_try_ai_fallback` och `extract_total_amount` tar **inte** någon `image_path`.  
→ **AI-text-fallback är kopplad.** Vision anropas aldrig från pipeline.

### 2.4 Vision (AI med bild)

**Var:**  
- `src/ai/fallback.py`: `extract_total_with_ai(..., image_path=None)` kan ta `image_path`.  
- `src/ai/providers.py`: `OpenAIProvider.extract_total_amount(..., image_path=...)`; vid `image_path` anropas `_extract_with_vision()`.  
- `src/pipeline/text_quality.py`: kommentaren säger att när `text_quality >= threshold` räcker text-only AI; under det “vision may be used”.

**Brist:** Ingen kod i `footer_extractor` eller `main` skickar någonsin `image_path` till `_try_ai_fallback` eller `extract_total_with_ai`.  
`extract_total_amount()` har ingen parameter för sidsbild; `page_context_for_ai` är bara text.  
→ **Vision är implementerad i AI-lagret men används aldrig i flödet.**

---

## 3. Flödesöversikt (så som det är idag)

```
[process_pdf, compare_extraction=True]
         │
         ├─ process_virtual_invoice(..., "pdfplumber")  →  r_pdf
         │     tokens via pdfplumber
         │     header + extract_total_amount (heuristik + AI text om conf < 0.95)
         │     validation
         │
         ├─ Acceptera pdfplumber?  (conf≥0.95 och pdf_text_quality≥0.5)  →  JA: resultat = r_pdf, klart
         │
         ├─ process_virtual_invoice(..., "ocr")  →  r_ocr
         │     tokens via OCR (render + Tesseract)
         │     header + extract_total_amount (samma logik, inkl. AI text)
         │     validation
         │
         ├─ Acceptera OCR?  (conf≥0.95, ocr_median≥70, ocr_text_quality≥0.5)  →  JA: resultat = r_ocr, klart
         │
         └─ _choose_best(r_pdf, r_ocr)  →  resultat = vald (pdf eller ocr)
         
Ingen vision-användning någonstans i kedjan.
```

---

## 4. Hypotes: var vision borde kopplas in

Enligt `text_quality.py` och R3/R4:

- När **text_quality < tröskel** (t.ex. 0.5) borde “vision may be used”.
- Det skulle innebära att när vi redan använder AI-fallback för total (i `extract_total_amount`) **och** textkvaliteten för den valda token-källan (pdf eller ocr) är låg, så borde vi:
  1. Ha tillgång till en renderad sidbild (t.ex. sista sidan i fakturan).
  2. Skicka denna `image_path` till `_try_ai_fallback` → `extract_total_with_ai(..., image_path=...)`.

Idag finns varken:

- parameter för `image_path` i `extract_total_amount()` / `_try_ai_fallback()`,  
eller  
- logik i main som bygger en `image_path` (t.ex. från `page.rendered_image_path` efter render) och skickar den till footer-extraktion.

---

## 5. Status och nästa steg

| Del av flödet            | Implementerad? | Anteckning |
|--------------------------|----------------|------------|
| pdfplumber vs OCR (token)| Ja             | compare_extraction, _choose_best |
| AI text-fallback (total) | Ja             | i footer_extractor vid conf < 0.95 |
| AI vision (total)        | **Nej**        | providers stödjer image_path, men ingen anropare skickar den |
| text_quality för vision  | Delvis         | Beräknas för routing pdf/ocr; används inte för “nu ska vi använda vision” |

**Rekommenderade åtgärder för att få vision att fungera:**

1. **Granska krav:** Bekräfta i Phase 14 / 15-spec att vision ska användas när text_quality < tröskel vid AI-fallback för total.
2. **Sidbild till footer:** I `process_virtual_invoice`, efter att tokens/segment är klara, om AI är aktiverat och vi planerar att anropa AI för total: rendera sista sidan om den inte redan har `rendered_image_path` (OCR-sökvägen kan återanvändas), annars använd den.
3. **Plumbra image_path till footer:**  
   - Lägg till parameter t.ex. `image_path_for_ai: Optional[str] = None` till `extract_total_amount()` och vidare till `_try_ai_fallback()`.  
   - I main, bygg denna sökväg (för sista sidan) och skicka med i anropet till `extract_total_amount` / retry-wrappern.
4. **När skicka vision:** I footer_extractor (eller i main innan anropet): om `page_context_for_ai` är tillräckligt dålig **eller** text_quality för aktuell token-källa < tröskel, sätt/använd `image_path` i AI-anropet; annars använd bara text (som idag).
5. **Spårbarhet:** Sätt t.ex. `extraction_detail["method_used"] = "ai_vision"` respektive `"ai_text"` när vision användes, så att Excel och loggar visar rätt källa.

---

## 6. Referenser i kod

- Token-nivå pdf/ocr: `src/cli/main.py` rad 802–921.  
- process_virtual_invoice: `src/cli/main.py` rad 423–611.  
- extract_total_amount och _try_ai_fallback: `src/pipeline/footer_extractor.py` rad 104–148, 249–720.  
- extract_total_with_ai och image_path: `src/ai/fallback.py` rad 49–85, 115–132.  
- Vision i provider: `src/ai/providers.py` (OpenAIProvider._extract_with_vision, image_path-hantering).  
- text_quality: `src/pipeline/text_quality.py` rad 1–7 (kommentar om vision).
