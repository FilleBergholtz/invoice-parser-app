# Phase 20: Known Limitations

**Phase:** 20 - Tabellsegment & kolumnregler  
**Documented:** 2026-01-26  
**Status:** Implementation complete, limitations documented for future phases

---

## Critical Limitations

### 1. Single VAT Rate Only (25%)

**Limitation:** Systemet stödjer endast en momssats (25%) och kan inte hantera fakturor med flera momssatser.

**Technical Details:**
- Regex pattern: `\b25[.,]00\b` (hardkodat i `invoice_line_parser.py`)
- Påverkar: Nettobeloppsextraktion på rader med 12% eller 6% moms
- Fil: `src/pipeline/invoice_line_parser.py`, rad 34

**Impact:**
- ❌ Fakturor med blandade momssatser (t.ex. livsmedel 12%, böcker 6%, tjänster 25%) parsas felaktigt
- ❌ Rader med 12% eller 6% moms identifieras inte som line items (kräver 25% moms)
- ⚠️ Kan leda till ofullständig radextraktion på fakturor med reducerad moms

**Workaround (Current):**
- Ingen automatisk workaround finns
- Systemet skippar rader utan 25% moms när `require_moms=True`

**Resolution Path:**
1. **Phase 21/22:** Utöka VAT pattern till `\b(25|12|6)[.,]00\b`
2. **Phase 21/22:** Detektera faktisk momssats per rad och validera mot förväntade satser
3. **Phase 21/22:** Lägg till `vat_rate` fält i `InvoiceLine` modell för spårbarhet

**Research Reference:** Se `20-RESEARCH.md`, "Open Questions #3"

---

## Medium Limitations

### 2. Swedish-Only Footer Keywords

**Limitation:** Footer-filtrering använder endast svenska nyckelord.

**Technical Details:**
- Keywords: "Summa att betala", "Nettobelopp exkl. moms", "Totalt", etc.
- Påverkar: Internationella fakturor eller fakturor på engelska
- Fil: `src/pipeline/invoice_line_parser.py`, rad 14-29

**Impact:**
- ⚠️ Engelska fakturor kan extrahera footer-rader som line items
- ⚠️ "Total", "Net Amount", "VAT" kan missas i footer-filtrering

**Workaround (Current):**
- Några engelska keywords finns (`'total'`, `'inkl'`, `'exkl'`)
- Täcker delvis internationella fakturor

**Resolution Path:**
- **Phase 21/22:** Utöka keyword-listor med engelska/norska/danska varianter
- **Future:** Konfigurerbart per leverantörsprofil

---

### 3. Fixed Table End Pattern

**Limitation:** Tabellslut detekteras endast via "Nettobelopp exkl. moms" mönster.

**Technical Details:**
- Pattern: `r"nettobelopp\s+exkl\.?\s*moms"`
- Påverkar: Fakturor med annat slutmönster (t.ex. "Subtotal", "Total excl. VAT")
- Fil: `src/pipeline/invoice_line_parser.py`, rad 33

**Impact:**
- ⚠️ Tabellblock kan sträcka sig för långt (inkludera footer-rader)
- ⚠️ Om mönster saknas returneras alla rader från header till slutet

**Workaround (Current):**
- Footer-filtrering (`_is_footer_row()`) fångar många fall även om tabellblock-avgränsning missar

**Resolution Path:**
- **Phase 21/22:** Lägg till alternativa slutmönster ("Total", "Subtotal")
- **Future:** Konfigurerbart per leverantörsprofil

---

## Minor Limitations

### 4. Header Detection Requires "Nettobelopp" + Column Keyword

**Limitation:** Tabellstart kräver både "nettobelopp" OCH ("artikelnr" ELLER "artikel" ELLER "benämning").

**Technical Details:**
- Function: `_is_table_header_row()`
- Påverkar: Fakturor med annorlunda kolumnrubriker
- Fil: `src/pipeline/invoice_line_parser.py`, rad 37-40

**Impact:**
- ℹ️ Fakturor utan dessa exakta keywords får ingen tabellblock-avgränsning
- ℹ️ Fallback: alla rader behandlas som potentiella line items (filtreras via footer-keywords)

**Workaround (Current):**
- Fungerar bra för svenska fakturor
- Footer-filtrering förhindrar falska positiva även utan block-avgränsning

**Resolution Path:**
- **Phase 21/22:** Utöka header-keywords med varianter ("Description", "Item", "Amount")
- **Future:** Fuzzy matching för header-detektion

---

### 5. No Multi-Page Table Continuation Detection

**Limitation:** Tabellblock detekteras per sida, inte över sidgränser.

**Technical Details:**
- Function: `_get_table_block_rows()` körs per sida
- Påverkar: Fakturor där header endast finns på första sidan
- Scope: Phase 21 scope (multi-line items inkluderar multi-page tables)

**Impact:**
- ℹ️ Sida 2+ kan sakna header → ingen block-avgränsning
- ℹ️ Fungerar för de flesta fakturor som upprepar header per sida

**Workaround (Current):**
- Ingen workaround implementerad
- Många leverantörer upprepar header per sida

**Resolution Path:**
- **Phase 21:** Implementera cross-page table continuation detection
- **Phase 21:** Detekta "continued from previous page" mönster

---

## Summary

| Limitation | Severity | Affected Use Cases | Target Phase |
|------------|----------|-------------------|--------------|
| Single VAT rate (25%) | **CRITICAL** | Fakturor med blandade momssatser | Phase 21/22 |
| Swedish-only keywords | **MEDIUM** | Internationella fakturor | Phase 21/22 |
| Fixed table end pattern | **MEDIUM** | Icke-svenska footer-mönster | Phase 21/22 |
| Strict header detection | **MINOR** | Ovanliga kolumnrubriker | Phase 21/22 |
| No multi-page tables | **MINOR** | Tabeller utan header per sida | Phase 21 |

---

## Validation Notes

**Implementation Quality:** EXCELLENT  
**Research Alignment:** 100% match + improvements (discount handling, credit notes, trailing minus)  
**Anti-Patterns Avoided:** All 5 anti-patterns from research avoided  

**Strengths:**
- ✅ VAT%-anchored net amount extraction (robust against column order variations)
- ✅ Two-tier footer filtering (prevents false positives)
- ✅ Thousand separator handling (Swedish formatting support)
- ✅ Full-text regex parsing (handles multi-token amounts)

**See Also:**
- `20-RESEARCH.md` - Full research documentation
- `20-01-SUMMARY.md` - Implementation summary
- `src/pipeline/invoice_line_parser.py` - Source code

---

*Phase: 20-tabellsegment-kolumnregler*  
*Documented: 2026-01-26*  
*Next Review: Phase 21 planning*
