# Spec-fil Analys: Avvikelser mellan spec och implementation

**Datum:** 2026-01-24  
**Spec-fil:** `specs/invoice_pipeline_v1.md`  
**Implementation:** `src/cli/main.py` + pipeline-moduler

---

## Sammanfattning

Spec-filen beskriver en **teoretisk pipeline** med 12 steg, men den faktiska implementationen är **optimerad och förenklad** med vissa steg integrerade eller hoppade över.

---

## Identifierade Avvikelser

### 1. ❌ Steg 6: Segments → Zoner

**Spec:** Explicitt steg där Segments transformeras till Zone-objekt.

**Implementation:** Zones används bara **konceptuellt** i confidence scoring (t.ex. "header zone", "footer zone") men det finns inga separata Zone-objekt eller Zone-klasser. Header och footer extraheras direkt från Segment-objekt.

**Rekommendation:** Spec bör uppdateras för att reflektera att zones är konceptuella områden, inte separata datatyper.

---

### 2. ❌ Steg 7: Zoner → Header

**Spec:** Header extraheras från Zone-objekt.

**Implementation:** Header extraheras **direkt från header_segment** (Segment-objekt) via `extract_header_fields()`. Ingen Zone-mellansteg.

**Rekommendation:** Spec bör ändras till "Segments → Header" (hoppa över Zone-steg).

---

### 3. ❌ Steg 8: Header → Specifikation

**Spec:** InvoiceHeader transformeras till InvoiceSpecification-objekt.

**Implementation:** **InvoiceSpecification finns inte längre**. Alla fält finns direkt i InvoiceHeader-klassen. Ingen transformation görs.

**Rekommendation:** Spec bör uppdateras för att reflektera att InvoiceHeader är slutresultatet, inte InvoiceSpecification.

---

### 4. ⚠️ Steg 9: Segments → InvoiceLine

**Spec:** InvoiceLines extraheras från items-segment.

**Implementation:** ✅ **Korrekt** - `extract_invoice_lines(items_segment)` gör exakt detta.

**Status:** Spec stämmer med implementation.

---

### 5. ❌ Steg 10: InvoiceLine → Reconciliation

**Spec:** Separata Reconciliation-objekt skapas med beräknade summor.

**Implementation:** **Ingen separat Reconciliation-klass**. Reconciliation-logiken (beräkning av `lines_sum`, `diff`) görs direkt i `validate_invoice()` funktionen. Resultatet lagras i `ValidationResult` (som har `lines_sum`, `diff`, etc.).

**Rekommendation:** Spec bör uppdateras för att reflektera att reconciliation är integrerad i validation-steget.

---

### 6. ⚠️ Steg 11: Reconciliation → Validation

**Spec:** Validation-objekt skapas från Reconciliation.

**Implementation:** ✅ **Delvis korrekt** - `validate_invoice()` skapar `ValidationResult`, men reconciliation görs **inom** validation-steget, inte som separat steg.

**Rekommendation:** Spec bör uppdateras för att visa att reconciliation och validation är samma steg.

---

### 7. ✅ Steg 12: Validation → Export

**Spec:** Export genereras från Validation-objekt.

**Implementation:** ✅ **Korrekt** - Excel-export använder `ValidationResult` och `InvoiceHeader` + `InvoiceLine`-listor.

**Status:** Spec stämmer med implementation.

---

### 8. ⚠️ Saknat steg: Footer-extraktion

**Spec:** Nämner inte explicit footer-extraktion som separat steg.

**Implementation:** Footer extraheras separat via `extract_total_amount(footer_segment, ...)` som ett eget steg efter header-extraktion.

**Rekommendation:** Spec bör lägga till "Segments → Footer" eller "Footer → Total Amount" som explicit steg.

---

## Faktisk Pipeline-ordning (Implementation)

1. ✅ PDF → Document (`read_pdf()`)
2. ✅ Document → Page (`doc.pages`)
3. ✅ Page → Tokens (`extract_tokens_from_page()`)
4. ✅ Tokens → Rows (`group_tokens_to_rows()`)
5. ✅ Rows → Segments (`identify_segments()`)
6. ✅ Segments → InvoiceLine (`extract_invoice_lines()`)
7. ✅ Segments → Header (`extract_header_fields()` på header_segment)
8. ✅ Segments → Footer (`extract_total_amount()` på footer_segment)
9. ✅ InvoiceHeader + InvoiceLines → Validation (`validate_invoice()` - inkluderar reconciliation)
10. ✅ Validation → Export (`export_to_excel()`)

**Totalt: 10 steg** (inte 12 som i spec)

---

## Rekommenderade Uppdateringar till Spec

### Alternativ 1: Uppdatera spec för att matcha implementation

1. Ta bort steg 6 (Segments → Zoner) - zones är konceptuella, inte datatyper
2. Ändra steg 7 till "Segments → Header" (direkt från segment)
3. Ta bort steg 8 (Header → Specifikation) - InvoiceSpecification finns inte
4. Lägg till "Segments → Footer" som nytt steg (för total amount extraction)
5. Kombinera steg 10-11 till "InvoiceLines + Header → Validation" (inkluderar reconciliation)

### Alternativ 2: Behåll spec som teoretisk referens

Lägg till notis i början av spec-filen:
> **Notera:** Denna spec beskriver en teoretisk pipeline-struktur. Den faktiska implementationen är optimerad och vissa steg är integrerade eller hoppade över. Se `SPEC_ANALYSIS.md` för detaljerad jämförelse.

---

## PyInstaller Spec-filer

### EPG_PDF_Extraherare.spec (GUI)
- ✅ Korrekt entry point: `run_gui.py`
- ✅ Korrekt excludes: streamlit, fastapi (inte behövs för GUI)
- ✅ Korrekt console=False för GUI-app

### EPG_PDF_Extraherare_CLI.spec
- ✅ Korrekt entry point: `src/cli/main.py`
- ✅ Korrekt excludes: streamlit, PySide6 (inte behövs för CLI)
- ✅ Korrekt console=True för CLI-app
- ⚠️ Kommentarer nämner "CLI behöver inte Streamlit/FastAPI" - korrekt, men dessa är redan borttagna från projektet

**Status:** PyInstaller spec-filer är korrekta och uppdaterade.

---

## Slutsats

**Pipeline-specifikationen (`invoice_pipeline_v1.md`) är inte helt korrekt** längre eftersom:
- Vissa steg (Zones, InvoiceSpecification, Reconciliation) finns inte som separata datatyper
- Steg-ordningen skiljer sig från implementationen
- Footer-extraktion saknas som explicit steg

**Rekommendation:** Uppdatera spec-filen för att matcha den faktiska implementationen, eller lägg till en tydlig notis om att det är en teoretisk referens.
