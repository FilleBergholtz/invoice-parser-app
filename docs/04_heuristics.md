# Heuristiker och Regler

## Översikt

Detta dokument definierar heuristiker och regler för parsing-logik i invoice-parser pipeline. Heuristikerna används för att identifiera och extrahera data när exakta mönster inte finns.

## Viktiga regler

### Regel 1: Rad med belopp = produktrad

**Beskrivning**: En rad som innehåller ett numeriskt belopp tolkas som en produktrad (InvoiceLine).

**Implementation**:
- Identifiera numeriska värden i raden (regex: `\d+[,.]?\d*`)
- Om rad innehåller belopp i höger kolumn = produktrad
- Belopp kan vara formaterat med komma eller punkt som decimalseparator

**Exempel**:
```
Produkt A    2 st    100.00    200.00
```
Denna rad identifieras som produktrad eftersom den innehåller belopp (200.00).

---

## Token-gruppering till rader

### Heuristik 1: Y-position tolerans

**Beskrivning**: Tokens på samma Y-position grupperas i samma rad.

**Regel**:
- Tolerans för Y-position: ±2 pixlar eller 0.01 av sidhöjd
- Median Y-position används för raden
- Tokens sorteras efter X-position inom raden (vänster till höger)

**Implementation**:
```python
def group_tokens_to_rows(tokens: List[Token], y_tolerance: float = 2.0) -> List[Row]:
    # Gruppera tokens baserat på Y-position med tolerans
    # Returnera sorterade rader (top-to-bottom)
```

---

## Segment-identifiering

### Heuristik 2: Position-baserad segmentering

**Beskrivning**: Segments identifieras baserat på Y-position på sidan.

**Regler**:
- **Header**: Övre 20-30% av sidan (y < 0.3 * page_height)
- **Items**: Mittdel (0.3 * page_height < y < 0.8 * page_height)
- **Footer**: Nedre del (y > 0.8 * page_height)

**Undantag**:
- Om header innehåller tabellhuvud → items kan börja tidigare
- Om footer innehåller endast "Sida X av Y" → inte footer-segment

### Heuristik 3: Innehållsbaserad segmentering

**Beskrivning**: Använd nyckelord för att identifiera segments.

**Regler för Header**:
- Nyckelord: "Faktura", "Invoice", "Leverantör", "Supplier", "Fakturanummer", "Invoice Number"
- Om rad innehåller dessa nyckelord → header-segment

**Regler för Footer**:
- Nyckelord: "Totalt", "Total", "Summa", "Subtotal", "Moms", "VAT"
- Numeriska summor i slutet av dokumentet → footer-segment

---

## Header-identifiering

### Heuristik 4: Header-scoring

**Beskrivning**: Score-header baserat på position, formatering och nyckelord.

**Scoring-komponenter**:
- **Position**: Övre del (y < 0.3 * page_height) = +3 poäng
- **Nyckelord**: Varje nyckelord matchad = +2 poäng
- **Formatering**: Större typsnitt = +1 poäng
- **Konfidenspoäng**: (total_score / max_possible_score)

**Nyckelord för header**:
- Svenska: "Faktura", "Fakturanummer", "Fakturadatum", "Leverantör", "Kund"
- Engelska: "Invoice", "Invoice Number", "Invoice Date", "Supplier", "Customer"

**Implementation**:
```python
def calculate_header_score(segment: Segment, page: Page) -> float:
    score = 0.0
    # Position scoring
    # Keyword matching
    # Font size scoring
    return score / max_score  # Normalized to 0.0-1.0
```

### Heuristik 5: Fakturanummer-extraktion

**Beskrivning**: Identifiera fakturanummer via nyckelord + värde.

**Regler**:
- Sök efter nyckelord: "fakturanummer", "invoice number", "no.", "nr", "number"
- Efter nyckelord: följande text/värde = fakturanummer
- Fakturanummer kan vara: alfanumerisk (ex: "INV-2024-001") eller numerisk (ex: "12345")

**Regex-mönster**:
- `(?:fakturanummer|invoice\s*number|no\.|nr|number)[\s:]*([A-Z0-9\-]+)`

### Heuristik 6: Datum-extraktion

**Beskrivning**: Identifiera datum i olika format.

**Datumformat som stöds**:
- `YYYY-MM-DD` (ex: "2024-01-15")
- `DD/MM/YYYY` (ex: "15/01/2024")
- `DD.MM.YYYY` (ex: "15.01.2024")
- `DD-MM-YYYY` (ex: "15-01-2024")
- `YYYY-MM-DD` (ex: "2024-01-15")
- Svenska format: "15 januari 2024", "15 jan 2024"

**Regler**:
- Sök efter nyckelord: "datum", "date", "fakturadatum", "invoice date"
- Efter nyckelord: första matchande datum-format = datum

**Regex-mönster**:
- `(\d{4}-\d{2}-\d{2})` (ISO-format)
- `(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4})` (DD/MM/YYYY varianter)

---

## Produktrad-identifiering

### Heuristik 7: Kolumn-baserad parsing

**Beskrivning**: Identifiera kolumner baserat på X-position.

**Regler**:
- Analysera X-positioner för alla tokens i items-segment
- Identifiera kolumner baserat på X-position-kluster
- Vanliga kolumner (vänster till höger):
  1. Beskrivning (stor bredd)
  2. Kvantitet (smal)
  3. Enhetspris (smal, högerjusterad)
  4. Totalt belopp (smal, högerjusterad)

**Implementation**:
```python
def identify_columns(rows: List[Row]) -> List[float]:
    # Analysera X-positioner
    # Identifiera kolumn-centra (klustering)
    # Returnera lista av X-koordinater för kolumner
```

### Heuristik 8: Belopp-identifiering

**Beskrivning**: Identifiera numeriska belopp i höger kolumn.

**Regler**:
- Belopp är högerjusterade i höger kolumn
- Format: `\d+[,.]?\d*` (kan ha decimaler med komma eller punkt)
- Belopp kan ha valuta-symbol (SEK, €, $) men ignoreras vid parsing

**Regex-mönster**:
- `(\d+[,.]?\d*)\s*(?:SEK|EUR|€|\$)?` för belopp med valuta

---

## Fortsättningsrader (Wrap)

### Heuristik 9: Wrap-identifiering

**Beskrivning**: Identifiera rader som är fortsättningar av produktbeskrivning.

**Regler**:
- Rad som INTE innehåller belopp = möjlig wrap
- Rad som är närmast under produktrad = trolig wrap
- X-position börjar ungefär samma som beskrivningens start (tolerans)
- Rad som innehåller endast text (ingen kvantitet/pris) = wrap

**Implementation**:
```python
def identify_wrapped_rows(rows: List[Row], invoice_line: InvoiceLine) -> List[Row]:
    # Identifiera rader som är fortsättningar
    # Koppla till InvoiceLine
    # Returnera lista av wrapped rows
```

### Heuristik 10: Beskrivning-konsolidering

**Beskrivning**: Slå samman beskrivning från alla rader i InvoiceLine.

**Regler**:
- Primär rad: rad med belopp (inte wrap)
- Wrapped rader: rader utan belopp
- Konsoliderad beskrivning: primär rad + wrapped rader (separerade med mellanslag)

---

## Footer och summor

### Heuristik 11: Footer-parsing

**Beskrivning**: Extrahera summor från footer-segment.

**Regler**:
- Sök efter nyckelord: "Subtotal", "Totalt", "Moms", "VAT", "Total"
- Numeriska värden efter nyckelord = summa
- Högerjusterade numeriska värden = belopp

**Nyckelord → fält**:
- "Subtotal", "Delsumma" → subtotal
- "Moms", "VAT", "Skatt" → tax
- "Totalt", "Total", "Summa" → total

---

## Spatial analys (Zoner)

### Heuristik 12: Zon-identifiering

**Beskrivning**: Skapa spatiala zoner för kontextuell analys.

**Regler**:
- **Header-zon**: Övre del (y < 0.3 * page_height, hela bredden)
- **Datum-zon**: Övre del, höger sida (x > 0.6 * page_width)
- **Belopps-kolumn**: Höger sida (x > 0.8 * page_width) i items-segment
- **Items-zon**: Mittdel (hela bredden, y mellan 0.3 och 0.8 * page_height)

**Användning**:
- Zoner hjälper till att kontextuellt identifiera data
- Ex: Token i datum-zon = troligen datum

---

## Fält-extraktion

### Heuristik 13: Kvantitet-extraktion

**Beskrivning**: Identifiera kvantitet från produktrad.

**Regler**:
- Kvantitet finns vanligtvis i andra eller tredje kolumnen
- Format: numerisk + enhet (ex: "2 st", "10 kg", "1.5 h")
- Om ingen enhet hittas → tolkas som numerisk värde

**Regex-mönster**:
- `(\d+[,.]?\d*)\s*(st|pcs|kg|g|h|m|m²)?` för kvantitet med enhet

### Heuristik 14: Enhetspris-extraktion

**Beskrivning**: Identifiera enhetspris från produktrad.

**Regler**:
- Enhetspris finns vanligtvis i tredje eller fjärde kolumnen
- Format: numeriskt belopp (kan ha decimaler)
- Enhetspris är vanligtvis högerjusterat

---

## Fallback och felhantering

### Heuristik 15: Toleranta matchningar

**Beskrivning**: Använd när exakta matchningar misslyckas.

**Regler**:
- Om fakturanummer inte hittas med nyckelord → sök efter numeriska/alfanumeriska värden i header
- Om datum inte hittas med format → sök efter alla datum-mönster i header
- Om kvantitet saknas → sätt till 1.0 (default)

### Heuristik 16: Konfidens-baserad extraktion

**Beskrivning**: Tilldela konfidenspoäng till extraherade fält.

**Regler**:
- Hög konfidens (0.8-1.0): Exakt matchning med nyckelord + format
- Medium konfidens (0.5-0.8): Trolig matchning baserat på position/format
- Låg konfidens (0.0-0.5): Osäker matchning, flagga för granskning

---

## Implementation-anvisningar

1. **Prioritera**: Använd heuristik i ordning (viktigast först)
2. **Fallback**: Om en heuristik misslyckas, använd nästa
3. **Validering**: Alla extraherade värden valideras mot `docs/05_validation.md`
4. **Logging**: Logga vilka heuristiker som användes för felsökning

## Exempel

### Exempel 1: Produktrad-identifiering

```
Input Row: "Produkt A    2 st    100.00    200.00"

Heuristik 7: Identifiera kolumner
  - Kolumn 1 (x=50): "Produkt A" → description
  - Kolumn 2 (x=200): "2 st" → quantity
  - Kolumn 3 (x=250): "100.00" → unit_price
  - Kolumn 4 (x=300): "200.00" → total_amount

Heuristik 1 (Regel 1): Rad med belopp (200.00) = produktrad ✓
```

### Exempel 2: Fakturanummer-extraktion

```
Input Header Row: "Fakturanummer: INV-2024-001"

Heuristik 5: Sök efter nyckelord "fakturanummer"
  - Match: "fakturanummer"
  - Efter kolon: "INV-2024-001" → invoice_number ✓
  - Konfidens: 1.0 (exakt matchning)
```
