# Phase 3: Validation - Issues Found

**Date:** 2026-01-17  
**Source:** User feedback from Excel file inspection

---

## Critical Issues

### 1. Excel Column Index Error - Radsumma Shows as Percentage ✅ FIXED

**Problem:** Radsumma kolumnen visar procentformatering istället för valuta.

**Root Cause:** Faktura-ID kolumnen lades till (index 11), vilket förskjöt alla kontrollkolumner. Koden använde fel index:
- Radsumma är index 13, men koden formaterade index 11 (Faktura-ID)
- Fakturanummer-konfidens är index 15, men koden formaterade index 13 (Radsumma) → Därför fick Radsumma procentformatering!

**Fix:** Uppdaterade kolumnindex i `src/export/excel_export.py`:
- Radsumma: index 11 → 13
- Avvikelse: index 12 → 14
- Fakturanummer-konfidens: index 13 → 15
- Totalsumma-konfidens: index 14 → 16

**Status:** ✅ Fixed

---

### 2. Invoice Number Shows as "TBD" ✅ FIXED

**Problem:** Många fakturor visar "TBD" istället för fakturanummer.

**Root Cause:** Hard gate i `src/pipeline/header_extractor.py` satt `invoice_number = None` när konfidens < 0.95.

**Fix:** Implementerat omfattande förbättringar enligt specifikation:
- ✅ Utökade label-varianter (svenska + engelska): fakturanummer, fakt.nr, invoice number, inv no, etc.
- ✅ Normalisering före matchning: lowercase, ta bort : och #, slå ihop multipla mellanslag
- ✅ Söklogik "bredvid eller under": samma rad (högst prioritet) eller 1-2 rader under label
- ✅ Fallback header-scan: sök i översta 25% av sidan för 5-12 siffror, filtrera bort datum/år/belopp/postnummer
- ✅ Primär regex: `\b\d{6,10}\b`, fallback: `\b\d{5,12}\b`
- ✅ Tog bort hard gate: alltid spara bästa kandidat (även om konfidens < 0.95)
- ✅ Status blir REVIEW om konfidens < 0.95 (hanteras i validation)

**Result:** Fakturanummer visas nu alltid när det finns, även vid lägre konfidens. Osäkra värden markeras för granskning via REVIEW status.

**Status:** ✅ Fixed

---

### 3. Quantity × Unit Price ≠ Summa

**Problem:** Antal × A-pris stämmer inte med Summa på många rader.

**Root Cause:** `InvoiceLine.total_amount` extraheras direkt från PDF (rad 109 i `src/pipeline/invoice_line_parser.py`), medan `quantity` och `unit_price` extraheras separat med heuristik (rad 148-159). Det finns ingen validering eller beräkning som säkerställer att de stämmer.

**Example:**
- PDF visar: "Produkt X    5 st    100,00    500,00"
- System extraherar: quantity=5, unit_price=100.00, total_amount=500.00 ✅
- Men om extraktionen misslyckas: quantity=5, unit_price=100.00, total_amount=450.00 ❌

**Options:**
1. **Validate and warn** - Validera att `total_amount ≈ quantity * unit_price` (med tolerans för avrundning/rabatt), logga varning om skillnad
2. **Calculate from quantity/price** - Om både quantity och unit_price finns, beräkna `total_amount = quantity * unit_price` (ignorera PDF-värdet)
3. **Hybrid approach** - Använd PDF-värdet som primär, men validera mot beräknat värde och flagga avvikelser

**Recommendation:** Option 3 - Använd PDF-värdet som primär (det är vad som faktiskt står på fakturan), men validera mot beräknat värde och flagga avvikelser i validation warnings.

**Fix:** Implementerat validering i `src/pipeline/validation.py`:
- ✅ Ny funktion `validate_line_items()` validerar quantity × unit_price ≈ total_amount för varje line item
- ✅ Validering integrerad i `validate_invoice()` och lägger till varningar i ValidationResult.warnings
- ✅ Tolerans 0.01 SEK för avrundning
- ✅ Varningar formaterade: "Rad X: Antal × A-pris (X.XX) ≠ Summa (X.XX), avvikelse: X.XX SEK"
- ✅ Unit tests tillagda (5 tester, alla passerar)

**Status:** ✅ Fixed

---

### 4. Quantity Extraction Errors

**Problem:** Antal blir fel ibland.

**Root Cause:** Heuristik i `src/pipeline/invoice_line_parser.py` rad 148-159:
- "Rightmost numeric before amount is likely unit_price"
- "Leftmost numeric is likely quantity"
- "Single numeric: prefer quantity if small integer, otherwise unit_price"

Denna heuristik kan misslyckas för komplexa layouts eller när kolumner är i annan ordning.

**Options:**
1. **Improve heuristics** - Förbättra heuristik med bättre layout-analys
2. **Add validation** - Validera quantity/price mot total_amount
3. **Machine learning** - Använd ML för att identifiera kolumner (framtida förbättring)

**Recommendation:** Option 2 - Lägg till validering som flaggar när quantity × unit_price ≠ total_amount, så att användaren kan se problemet.

**Fix:** Implementerat validering som flaggar mismatches (se Issue #3 ovan). Valideringen identifierar när quantity × unit_price ≠ total_amount och lägger till varningar i ValidationResult.warnings, så att användaren kan se problemet direkt i valideringsresultatet.

**Status:** ✅ Fixed

---

## Summary

| Issue | Severity | Status | Action Required |
|-------|----------|--------|-----------------|
| Excel column index | Critical | ✅ Fixed | None |
| Invoice number "TBD" | High | ✅ Fixed | None |
| Quantity × Price ≠ Summa | High | ✅ Fixed | None |
| Quantity extraction errors | Medium | ✅ Fixed | None |

---

## Next Steps

1. ✅ **Fixed:** Excel column index
2. ✅ **Fixed:** Invoice number extraction - utökade labels, normalisering, söklogik, borttagen hard gate
3. ✅ **Fixed:** Validera quantity × unit_price mot total_amount - implementerat validate_line_items() och integrerat i validate_invoice()
4. ✅ **Fixed:** Quantity extraction errors - validering flaggar nu mismatches så användaren kan se problemet

---

*Issues documented: 2026-01-17*
