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

### 5. Tusendelsavgränsning i belopp hanteras inte korrekt

**Problem:** Belopp med tusendelsavgränsare (mellanslag) hanteras inte korrekt när beloppet är uppdelat mellan flera tokens.

**Root Cause:** I `src/pipeline/invoice_line_parser.py` rad 88-106 extraheras belopp token-för-token. Kod använder `.replace(' ', '')` för att ta bort mellanslag, vilket fungerar om "1 234,56" är i ett token, men misslyckas om det är uppdelat mellan tokens (t.ex. "1", "234,56" eller "1 234", ",56").

**Exempel från fakturor:**
- "1 072,60" - fungerar om i ett token
- "1 640,00" - kan misslyckas om uppdelat
- "7 517,00" - kan misslyckas om uppdelat
- "167 715,20" - kan misslyckas om uppdelat

**Problem:** Regex `r'[\d\s]+[.,]\d{2}'` matchar belopp per token, men när tusendelsavgränsare är mellan tokens extraheras endast delar av beloppet.

**Options:**
1. **Merge adjacent numeric tokens** - Kombinera intilliggande numeriska tokens när de matchar beloppsmönster
2. **Extract from full row text** - Extrahera belopp från `row.text` istället för token-för-token
3. **Improve regex to handle multi-token** - Använda mer sofistikerad parsing som hanterar flera tokens

**Recommendation:** Option 2 - Extrahera belopp från `row.text` för bättre stöd av tusendelsavgränsare, sedan matcha tillbaka till tokens för position.

**Fix:** Implementerat i `src/pipeline/invoice_line_parser.py`:
- ✅ Ny funktion `_extract_amount_from_row_text()` extraherar belopp från `row.text` istället för token-för-token
- ✅ Förbättrad regex: `r'\d{1,3}(?:\s+\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2})'` matchar både med och utan tusendelsavgränsare
- ✅ Mappning av beloppsposition i `row.text` tillbaka till token-index för att hitta `amount_token_idx`
- ✅ Stöd för belopp som "123,45", "1234,56", "1 234,56", "167 715,20", "1 072,60"

**Status:** ✅ Fixed

---

### 6. Rabatter extraheras inte

**Problem:** Negativa belopp (rabatter) extraheras inte från fakturor. Rabatter finns i beskrivning eller som negativa belopp.

**Root Cause:** I `src/pipeline/invoice_line_parser.py` rad 116 finns kontroll `if total_amount is None or total_amount <= 0: return None`, vilket ignorerar alla negativa belopp (rabatter). Dessutom finns ingen logik för att identifiera rabatter i beskrivningen eller extrahera negativa belopp.

**Exempel från fakturor:**
- "-88,00" - negativt belopp som troligen är rabatt
- "-603,61" - negativt belopp
- "-2 007,28" - negativt belopp med tusendelsavgränsare
- "M9 Toabal-standard 4 EA 440,00 -88,00 1 672,00" - rabatt i egen kolumn

**Options:**
1. **Allow negative amounts** - Tillåt negativa belopp som separata rabattrader eller som rabatt-kolumn
2. **Extract discount from description** - Sök efter rabatt i beskrivning ("-10%", "rabatt", etc.)
3. **Detect negative column** - Identifiera negativt belopp som rabatt-kolumn innan total_amount

**Recommendation:** Option 3 - Identifiera negativa belopp som rabatt-kolumn innan total_amount. Om negativt belopp finns innan total_amount, behandla det som rabatt, inte som total_amount.

**Fix:** Implementerat i `src/pipeline/invoice_line_parser.py`:
- ✅ Uppdaterad `_extract_amount_from_row_text()` för att hitta både positiva och negativa belopp
- ✅ Regex uppdaterad: `r'-?\d{1,3}(?:\s+\d{3})*(?:[.,]\d{2})|-?\d+(?:[.,]\d{2})'` matchar negativa belopp med minus-tecken
- ✅ Logik: Högra positiva beloppet = total_amount, negativa belopp innan total_amount = discount
- ✅ Discount extraheras som positivt värde (absolutvärde av negativt belopp)
- ✅ Stöd för rader som "440,00 -88,00 1 672,00" → total_amount=1672.00, discount=88.00

**Status:** ✅ Fixed

---

### 7. Artikelnummer och radnummer i beskrivning

**Problem:** Beskrivningen innehåller ofta artikelnummer och radnummer i början, men dessa extraheras inte separat.

**Root Cause:** I `src/pipeline/invoice_line_parser.py` rad 120-121 extraheras beskrivning som allt text före amount-kolumnen, utan att separera artikelnummer/radnummer.

**Exempel från fakturor:**
- "26 011407 EntrebodTB3entre" - artikelnummer "26 011407"
- "39 93178 KonferensbodK11kököppenlångsida" - artikelnummer "39 93178"
- "15365 Konferensbod K11 öppen långsida" - artikelnummer "15365"
- "11 M9 Toabal-standard" - radnummer "11"

**Options:**
1. **Extract article number from description start** - Identifiera artikelnummer i början av beskrivning (6-8 siffror, eventuellt med mellanslag)
2. **Extract line number from description start** - Identifiera radnummer i början (2-3 siffror)
3. **Add article_number and invoice_line_number fields** - Lägg till separata fält i InvoiceLine modellen

**Recommendation:** Option 1 - Identifiera artikelnummer i början av beskrivning och extrahera som separat fält. Radnummer hanteras redan via `line_number` i InvoiceLine.

**Status:** ⚠️ Needs investigation - Lägg till artikelnummer-fält om det behövs, annars behåll i beskrivning.

---

## Summary

| Issue | Severity | Status | Action Required |
|-------|----------|--------|-----------------|
| Excel column index | Critical | ✅ Fixed | None |
| Invoice number "TBD" | High | ✅ Fixed | None |
| Quantity × Price ≠ Summa | High | ✅ Fixed | None |
| Quantity extraction errors | Medium | ✅ Fixed | None |
| Tusendelsavgränsning | High | ✅ Fixed | None |
| Rabatter extraheras inte | Medium | ✅ Fixed | None |
| Artikelnummer i beskrivning | Low | ⚠️ Needs investigation | Extract article number if needed |

---

## Next Steps

1. ✅ **Fixed:** Excel column index
2. ✅ **Fixed:** Invoice number extraction - utökade labels, normalisering, söklogik, borttagen hard gate
3. ✅ **Fixed:** Validera quantity × unit_price mot total_amount - implementerat validate_line_items() och integrerat i validate_invoice()
4. ✅ **Fixed:** Quantity extraction errors - validering flaggar nu mismatches så användaren kan se problemet
5. ✅ **Fixed:** Tusendelsavgränsning - implementerat `_extract_amount_from_row_text()` som extraherar belopp från row.text med stöd för tusendelsavgränsare
6. ✅ **Fixed:** Rabatter - implementerat identifiering av negativa belopp som rabatt-kolumn innan total_amount i `_extract_amount_from_row_text()`
7. **Investigation needed:** Artikelnummer - avgöra om separata fält behövs eller om beskrivning räcker

---

*Issues documented: 2026-01-17*  
*Updated: 2026-01-17 - Added issues #5, #6, #7*
