# Test-korpus Beskrivning

## Översikt

Detta dokument beskriver test-korpusen för invoice-parser, inklusive `sample_invoice_1.pdf` och förväntade resultat.

## Test-filer

### sample_invoice_1.pdf

**Beskrivning**: En representativ faktura-PDF som används för grundläggande testing av pipeline.

**Läge**: `tests/fixtures/pdfs/sample_invoice_1.pdf`

**Obs**: Detta är en placeholder-beskrivning. Den faktiska PDF-filen ska läggas till i mappen när den finns tillgänglig.

---

## Förväntade resultat

**VIKTIGT**: **Analys correctness är första acceptans**. Innan fältextraktion testas måste analyskvaliteten (tokenisering, rad-gruppering, segmentering) vara korrekt och verifierad.

### Analyskvalitet (första acceptans)

För att säkerställa korrekt analys måste följande verifieras:

- [x] **Debug-representation**: För varje sida, exportera en debug-representation (rows med bbox) och verifiera manuellt på minst 5 fakturor
- [x] **Radordning**: Radordning top-to-bottom verifieras korrekt
- [x] **Segmentering**: Header/items/footer identifieras korrekt (minst grov segmentering)
- [x] **Spårbarhet**: Varje row kan spåras tillbaka till ursprungliga tokens med korrekt bbox

**Debug-format för rows**:
```
Page 1:
  Row 1 (y=50.0, x_min=50.0, x_max=500.0): "Fakturanummer: INV-2024-001"
  Row 2 (y=80.0, x_min=50.0, x_max=500.0): "Leverantör: Acme AB"
  ...
```

### Förväntad struktur

En typisk test-faktura bör innehålla:

#### Header-segment
- Fakturanummer: T.ex. "INV-2024-001" eller numeriskt "12345"
- Fakturadatum: T.ex. "2024-01-15" eller "15/01/2024"
- Leverantörsnamn: T.ex. "Acme AB"
- Leverantörsadress: T.ex. "Storgatan 1, 123 45 Stockholm"
- Kundnamn: T.ex. "Kundföretag AB" (valfritt)
- Kundadress: T.ex. "Kundgatan 2, 678 90 Göteborg" (valfritt)

#### Items-segment
- Minst 2-3 produktrader med:
  - Beskrivning: T.ex. "Produkt A", "Tjänst B"
  - Kvantitet: T.ex. "2 st", "10 kg", "1.5 h"
  - Enhetspris: T.ex. "100.00 SEK", "50.00"
  - Totalt belopp: T.ex. "200.00 SEK", "500.00"

#### Footer-segment
- Subtotal: T.ex. "Subtotal: 700.00 SEK"
- Moms (om tillämpligt): T.ex. "Moms (25%): 175.00 SEK"
- Totalt: T.ex. "Totalt: 875.00 SEK"

---

## Förväntade pipeline-resultat

### Steg 1-3: PDF → Page → Tokens
- [x] PDF läsbar och kan parsas
- [x] Minst en sida extraheras
- [x] Tokens extraheras med korrekt positioner (x, y, width, height)
- [x] Alla tokens har text-innehåll

### Steg 4: Tokens → Rows
- [x] Tokens grupperas i rader baserat på Y-position
- [x] Radordning bevaras (top-to-bottom)
- [x] **Radordning verifieras på testkorpus** (debug-representation exporteras och manuellt kontrollerad)
- [x] Produktrader identifieras (rader med belopp)

### Steg 5: Rows → Segments
- [x] Header-segment identifieras (övre del)
- [x] Items-segment identifieras (mittdel)
- [x] Footer-segment identifieras (nedre del)

### Steg 6-8: Segments → Zoner → Header → Specifikation
- [x] Spatiala zoner skapas korrekt
- [x] Header-scoring identifierar korrekt header-segment
- [x] Fakturanummer extraheras: "INV-2024-001" (eller motsvarande)
- [x] Fakturadatum extraheras: "2024-01-15" (eller motsvarande format)
- [x] Leverantörsnamn extraheras

### Steg 9: Segments → InvoiceLine
- [x] Minst 2-3 produktrader extraheras
- [x] Varje InvoiceLine har:
  - `description`: Extraherat korrekt
  - `quantity`: Extraherat (om tillgängligt)
  - `unit_price`: Extraherat (om tillgängligt)
  - `total_amount`: Extraherat korrekt

### Steg 10: InvoiceLine → Reconciliation
- [x] Subtotal beräknas korrekt: `sum(InvoiceLine.total_amount)`
- [x] Footer-parsing extraherar subtotal/total från PDF
- [x] Skillnader beräknas korrekt

### Steg 11: Reconciliation → Validation
- [x] Status sätts korrekt:
  - **OK**: Om alla summor stämmer och obligatoriska fält finns
  - **Warning**: Om små avvikelser eller valfria fält saknas
  - **Review**: Om stora avvikelser eller kritiska fält saknas

### Steg 12: Validation → Export
- [x] CSV genereras med korrekt struktur
- [x] Header-rad inkluderar metadata (fakturanummer, datum, leverantör)
- [x] Produktrader exporteras korrekt
- [x] Footer med summor inkluderas
- [x] UTF-8 kodning fungerar (ä, ö, å hanteras)

---

## Edge cases

### Edge case 1: Saknad kvantitet
**Scenario**: Produktrad utan kvantitet, endast enhetspris och total.

**Förväntat resultat**:
- `quantity` = None eller 1.0 (default)
- `total_amount` extraheras korrekt
- Status: **Warning** ("Varning: Produktrad X saknar kvantitet")

---

### Edge case 2: Fortsättningsrader (wrapped text)
**Scenario**: Produktbeskrivning uppdelad på flera rader.

**Förväntat resultat**:
- Wrapped rader kopplas till samma InvoiceLine
- `description` konsolideras från alla rader
- `total_amount` finns bara på sista raden

---

### Edge case 3: Saknad moms
**Scenario**: Faktura utan moms eller nollmoms.

**Förväntat resultat**:
- `tax` = None eller 0.0
- `calculated_total` = `calculated_subtotal`
- Status: **OK** (om summor stämmer)

---

### Edge case 4: Aritmetiska avvikelser
**Scenario**: `quantity * unit_price ≠ total_amount` (p.g.a. avrundning eller rabatt).

**Förväntat resultat**:
- Avvikelse < 0.01 SEK → Status: **OK**
- Avvikelse 0.01-1.00 SEK → Status: **Warning**
- Avvikelse > 1.00 SEK → Status: **Review**

---

### Edge case 5: Saknade obligatoriska fält
**Scenario**: Faktura utan fakturanummer eller datum.

**Förväntat resultat**:
- `invoice_number` eller `invoice_date` = None
- Status: **Review**
- Error: "Kritisk: Fakturanummer saknas (obligatoriskt)" eller "Fakturadatum saknas"

---

### Edge case 6: Stora summa-avvikelser
**Scenario**: Beräknad subtotal skiljer sig mycket från extraherad subtotal.

**Förväntat resultat**:
- Avvikelse > 1.00 SEK → Status: **Review**
- Error: "Kritisk: Stor subtotal-avvikelse: X.XX SEK"

---

### Edge case 7: Olika datumformat
**Scenario**: Faktura med datum i format "15/01/2024" eller "15.01.2024".

**Förväntat resultat**:
- Datum parsas korrekt till `datetime.date`-objekt
- Status: **OK** (om format är känt)

---

### Edge case 8: Olika decimalseparatorer
**Scenario**: Belopp med komma som decimalseparator (t.ex. "100,50").

**Förväntat resultat**:
- Belopp parsas korrekt (100.50)
- Status: **OK**

---

### Edge case 9: Multi-sidig faktura
**Scenario**: Faktura som spänner över flera sidor (2+ sidor).

**Förväntat resultat**:
- **Korrekt page_count**: PDF med 2 sidor identifieras som `page_count = 2`
- **Items på sida 2..n**: Produktrader på sida 2 och framåt identifieras korrekt
- **Segmentering över sidor**: Varje sida segmenteras korrekt (header/items/footer)
- **Spårbarhet**: Items på sida 2 kan spåras tillbaka till `page_number = 2` och korrekt token bbox
- **Radordning**: Radordning bevaras korrekt över sidor (top-to-bottom, sida 1 → sida 2)

**Test-krav**:
- Multi-sidig faktura ska ha korrekt `page_count`
- InvoiceLine-objekt från sida 2 ska ha `rows` som spåras tillbaka till `Page(page_number=2)`
- Debug-representation för varje sida verifieras separat

---

## Test-utfall

### Success-kriterier

För att en test ska anses lyckad måste **analyskvalitet** verifieras först:

**Första acceptans: Analyskvalitet**
1. **Debug-representation verifierad**: Rows med bbox exporterade och manuellt kontrollerade på minst 5 fakturor
2. **Radordning korrekt**: Top-to-bottom ordning verifierad på testkorpus
3. **Segmentering korrekt**: Header/items/footer identifieras korrekt (minst grov)
4. **Spårbarhet verifierad**: Varje row kan spåras tillbaka till Page/Token med korrekt bbox
5. **Multi-sidiga fakturor**: Korrekt page_count och items på sida 2..n identifieras

**Andra acceptans: Fältextraktion** (efter analyskvalitet är verifierad)
1. **Alla obligatoriska fält extraherade**: Fakturanummer, datum, minst en produktrad
2. **Summa-avvikelse ≤ 1.00 SEK**: Tolerans för små avrundningsfel
3. **Alla produktrader har total_amount**: Kritiskt för korrekt summa-beräkning
4. **CSV export fungerar**: Korrekt struktur och UTF-8 kodning

### Förväntad output-fil

**Exempel CSV** (med placeholder-data):

```csv
Invoice Number,Invoice Date,Supplier,Description,Quantity,Unit Price,Total Amount
INV-2024-001,2024-01-15,Acme AB,Produkt A,2,100.00,200.00
INV-2024-001,2024-01-15,Acme AB,Tjänst B,10,50.00,500.00
```

---

## Ytterligare test-filer (framtida)

När pipeline är mer mogen kan ytterligare test-filer läggas till:

- `sample_invoice_2.pdf`: Faktura med wraps
- `sample_invoice_3.pdf`: Faktura med nollmoms
- `sample_invoice_4.pdf`: Faktura med saknade fält (edge case testing)
- `sample_invoice_5.pdf`: Multi-sidig faktura

## Implementation-anvisningar

1. **Testa varje steg**: Använd `sample_invoice_1.pdf` för att testa varje pipeline-steg
2. **Validera mot förväntade resultat**: Jämför output med detta dokument
3. **Edge cases**: Testa edge cases när grundfunktionalitet fungerar
4. **Uppdatera dokumentation**: Om nya edge cases upptäcks, uppdatera detta dokument
