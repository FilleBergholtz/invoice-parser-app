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

### 2. Invoice Number Shows as "TBD" 

**Problem:** Många fakturor visar "TBD" istället för fakturanummer.

**Root Cause:** Hard gate i `src/pipeline/header_extractor.py` rad 131:
```python
if final_score < 0.95:
    invoice_header.invoice_number = None  # REVIEW
```

När konfidensen är < 0.95, sätts `invoice_number` till `None`, vilket gör att Excel-exporten visar "TBD" (rad 538 i `src/cli/main.py`):
```python
"fakturanummer": invoice_header.invoice_number or "TBD",
```

**Design Intent:** Hard gate är medveten design för att garantera 100% korrekthet - osäkra värden ska inte exporteras som OK. Men användaren vill förmodligen se det extraherade värdet även om det är osäkert (med REVIEW status).

**Options:**
1. **Store extracted value but mark as uncertain** - Spara det extraherade värdet även om konfidensen är < 0.95, men behåll REVIEW status
2. **Keep current design** - Hard gate förblir, men förbättra extraktionslogiken för att öka konfidensen
3. **Show in separate column** - Visa extraherade värde i en separat kolumn med konfidens

**Recommendation:** Option 1 - Spara det extraherade värdet även vid låg konfidens, men behåll REVIEW status. Detta möjliggör manuell granskning utan att förlora information.

**Status:** ⚠️ Needs decision

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

**Status:** ⚠️ Needs implementation

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

**Status:** ⚠️ Needs implementation

---

## Summary

| Issue | Severity | Status | Action Required |
|-------|----------|--------|-----------------|
| Excel column index | Critical | ✅ Fixed | None |
| Invoice number "TBD" | High | ⚠️ Needs decision | Design decision needed |
| Quantity × Price ≠ Summa | High | ⚠️ Needs implementation | Add validation logic |
| Quantity extraction errors | Medium | ⚠️ Needs implementation | Improve heuristics or validation |

---

## Next Steps

1. ✅ **Fixed:** Excel column index
2. **Decision needed:** Invoice number hard gate - ska vi visa extraherade värde även vid låg konfidens?
3. **Implementation needed:** Validera quantity × unit_price mot total_amount
4. **Implementation needed:** Förbättra quantity/price extraction heuristics

---

*Issues documented: 2026-01-17*
