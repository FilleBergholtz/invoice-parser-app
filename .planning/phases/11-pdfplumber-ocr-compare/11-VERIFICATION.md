# Phase 11: Pdfplumber och OCR — Verification

Verifiering av dual-run, jämförelse och “use best” enligt 11-CONTEXT.md.

---

## 1. Automatiska kontroller

**Batch, export och detection (relevanta för dual-run-flödet):**

```bash
pytest tests/test_batch_runner.py tests/test_excel_export.py tests/test_pdf_detection.py -v
```

**Senast kört:** 2026-01-25 — **16 passed.**

**Kodkontroll:**

- `compare_extraction` (default True), `--no-compare-extraction` i `src/cli/main.py`.
- `_choose_best_extraction_result`, `extraction_source` på `VirtualInvoiceResult`, `compare_extraction_used` i `RunSummary`.
- Excel-kolumn "Extraktionskälla" i `src/export/excel_export.py` när compare användes.

---

## 2. Manuell verifiering

1. Kör med compare (default):  
   `python run_engine.py --input <pdf> --output <dir> --verbose`  
   (compare är på om du inte sätter `--no-compare-extraction`).
2. I loggen: per virtual invoice ska det stå vilken källa som valdes, t.ex.  
   `[id] using pdfplumber (validation_passed=..., confidence=...)` eller `using ocr`.
3. Exportera till Excel och kontrollera att kolumnen "Extraktionskälla" finns när compare körts, och att exporten motsvarar den valda källan (pdfplumber/ocr).

**Förutsättning för OCR-vägen:** Tesseract installerat med svenska (`swe`). Annars används bara pdfplumber.

---

## 3. Sammanfattning verifiering 2026-01-25

| Kontroll | Resultat |
|----------|----------|
| 11-01 OCR path wiring | ✓ Kod finns (ocr_abstraction, main.py, boundary_detection) |
| 11-02 Dual-run och compare | ✓ `compare_extraction`, `_choose_best_extraction_result`, dual-run i process_pdf |
| 11-03 Use best downstream | ✓ export/review/summary använder valt resultat; extraction_source i Excel |
| Automatiska tester (batch, export, detection) | ✓ 16 passed |
| Manuell körning med compare | Ej kört — använd steg 2 ovan |

---

*Skapad 2026-01-25 — /gsd:verify-work 11*
