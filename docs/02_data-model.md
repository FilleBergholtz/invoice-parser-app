# Datamodell

## Översikt

Detta dokument fastlåser alla datastrukturer, fältnamn och typer som används i invoice-parser pipeline. **Ändra INTE fältnamn eller strukturer utan att först diskutera med användaren.**

## Grundläggande strukturer

### Document

Representerar ett PDF-dokument.

```python
Document:
    - filename: str              # Filnamn på PDF-filen
    - filepath: str              # Full sökväg till filen
    - page_count: int            # Antal sidor i dokumentet
    - pages: List[Page]          # Lista av Page-objekt
    - metadata: Dict[str, Any]   # Ytterligare metadata (valfritt)
```

### Page

Representerar en sida från PDF-dokumentet.

```python
Page:
    - page_number: int           # Sidnummer (börjar på 1)
    - document: Document         # Referens till föräldradokumentet
    - width: float               # Sidbredd i punkter
    - height: float              # Sidhöjd i punkter
    - tokens: List[Token]        # Lista av Token-objekt på sidan
    - rendered_image_path: Optional[str]  # Sökväg till renderad sida (bild) för layout-visualisering (valfritt)
```

**Viktigt**: `rendered_image_path` används för att senare steg kan härleda layout visuellt. Detta hjälper till vid felsökning och layout-analys.

### Token

Representerar en text-enhet med spatial information (position och dimensioner).

**KÄLLSANING**: Token är grundläggande dataenheten med full spårbarhet. Alla senare steg måste kunna spåras tillbaka till tokens.

```python
Token:
    - text: str                  # Texten i tokenen
    - x: float                   # X-koordinat (vänster kant)
    - y: float                   # Y-koordinat (övre kant)
    - width: float               # Bredd av tokenen
    - height: float              # Höjd av tokenen
    - page: Page                 # Referens till sidan
    - font_size: float           # Typsnittsstorlek (valfritt)
    - font_name: str             # Typsnittsnamn (valfritt)
```

**Koordinatsystem**: 
- Ursprung (0, 0) är i **övre vänstra hörnet**
- X ökar åt höger
- Y ökar nedåt

### Row

Representerar en logisk rad med tokens grupperade på Y-position.

```python
Row:
    - tokens: List[Token]        # Tokens i raden (KÄLLSANING - använd denna för spårbarhet)
    - y: float                   # Y-koordinat för raden (median eller första token)
    - x_min: float               # Minsta X-koordinat i raden
    - x_max: float               # Största X-koordinat i raden
    - text: str                  # Sammanfogad text från alla tokens (CONVENIENCE - använd tokens vid behov)
    - page: Page                 # Referens till sidan
```

**Viktigt**: 
- `tokens` är **källsanning** - all spårbarhet och exakt positionering kommer från tokens
- `text` är endast en **convenience-representation** för enkel textåtkomst
- **Downstream kod måste använda tokens/bbox** för spårbarhet och exakt positionering
- Vid behov av exakt text eller positioner, använd `tokens` direkt, inte `text`

### Segment

Representerar ett logiskt avsnitt (header, items/body, footer).

```python
Segment:
    - segment_type: str          # "header", "items", eller "footer"
    - rows: List[Row]            # Rader i segmentet
    - y_min: float               # Minsta Y-koordinat
    - y_max: float               # Största Y-koordinat
    - page: Page                 # Referens till sidan
```

**segment_type värden**:
- `"header"`: Övre del med metadata
- `"items"`: Mittdel med produktrader
- `"footer"`: Nedre del med summor

### Zone

Representerar ett spatialt område på sidan för kontextuell analys.

```python
Zone:
    - zone_type: str             # "header", "date", "amount", "items", etc.
    - x_min: float               # Vänster gräns
    - x_max: float               # Höger gräns
    - y_min: float               # Övre gräns
    - y_max: float               # Nedre gräns
    - page: Page                 # Referens till sidan
    - tokens: List[Token]        # Tokens inom zonen
```

## Invoice-specifika strukturer

### InvoiceHeader

Representerar extraherad header-data från fakturan.

```python
InvoiceHeader:
    - segment: Segment           # Referens till header-segmentet
    - invoice_number: Optional[str]    # Fakturanummer (extraherat)
    - invoice_date: Optional[datetime.date]  # Fakturadatum
    - supplier_name: Optional[str]     # Leverantörsnamn
    - supplier_address: Optional[str]  # Leverantörsadress
    - customer_name: Optional[str]     # Kundnamn
    - customer_address: Optional[str]  # Kundadress
    - raw_text: str              # Råtext från header-segmentet
    - confidence_score: float    # Konfidenspoäng för header-identifiering (0.0-1.0)
```

### InvoiceSpecification

Representerar strukturerad metadata från InvoiceHeader.

```python
InvoiceSpecification:
    - invoice_number: str        # Fakturanummer (validerat)
    - invoice_date: datetime.date  # Fakturadatum
    - supplier_name: str         # Leverantörsnamn
    - supplier_address: Optional[str]  # Leverantörsadress
    - customer_name: Optional[str]     # Kundnamn
    - customer_address: Optional[str]  # Kundadress
    - currency: Optional[str]    # Valuta (t.ex. "SEK", "EUR")
    - tax_rate: Optional[float]  # Skattesats (t.ex. 0.25 för 25%)
```

### InvoiceLine

Representerar en produktrad på fakturan.

```python
InvoiceLine:
    - rows: List[Row]            # Rader som tillhör denna produktrad (inkl. wraps) - KÄLLSANING för spårbarhet
    - description: str           # Produktbeskrivning
    - quantity: Optional[float]  # Kvantitet
    - unit: Optional[str]        # Enhet (t.ex. "st", "kg", "h", "m²")
    - unit_price: Optional[float]  # Enhetspris
    - discount: Optional[float]  # Rabatt (som decimal, t.ex. 0.10 för 10%, eller som belopp)
    - total_amount: float        # Totalt belopp för raden
    - vat_rate: Optional[float]  # Moms-sats för denna rad
    - line_number: int           # Radnummer (för ordning)
    - segment: Segment           # Referens till items-segmentet
```

**Viktigt**: 
- `rows` kan innehålla flera rader om produktbeskrivningen är uppdelad på flera rader (wrapped text)
- `rows` är **källsanning** - använd för spårbarhet tillbaka till Page/Token
- `unit` och `discount` är valfria fält som extraheras för export (Enhet och Rabatt-kolumner)

### Reconciliation

Representerar beräknade och extraherade summor för validering.

```python
Reconciliation:
    - invoice_lines: List[InvoiceLine]  # Alla produktrader
    - calculated_subtotal: float        # Beräknad summa (sum av InvoiceLine.total_amount)
    - extracted_subtotal: Optional[float]  # Extraherad subtotal från PDF
    - calculated_tax: Optional[float]   # Beräknad skatt
    - extracted_tax: Optional[float]    # Extraherad skatt från PDF
    - calculated_total: float           # Beräknad total (subtotal + tax)
    - extracted_total: Optional[float]  # Extraherad total från PDF
    - subtotal_difference: float        # Skillnad: |calculated - extracted|
    - tax_difference: Optional[float]   # Skillnad i skatt
    - total_difference: float           # Skillnad i total
```

### Validation

Representerar kvalitetskontroll-resultat.

```python
Validation:
    - status: str                # "OK", "Warning", eller "Review"
    - reconciliation: Reconciliation  # Referens till reconciliation
    - messages: List[str]        # Meddelanden (fel, varningar, etc.)
    - missing_fields: List[str]  # Lista av saknade fält
    - warnings: List[str]        # Lista av varningar
    - errors: List[str]          # Lista av fel
```

**status värden**:
- `"OK"`: Alla summor stämmer, alla fält extraherade
- `"Warning"`: Små avvikelser eller vissa fält saknas
- `"Review"`: Större avvikelser eller kritiska fält saknas

## Export-strukturer

### InvoiceExport

Representerar slutlig data för export till Excel.

```python
InvoiceExport:
    - specification: InvoiceSpecification  # Metadata
    - invoice_lines: List[InvoiceLine]    # Produktrader
    - reconciliation: Reconciliation       # Summor
    - validation: Validation               # Valideringsstatus
    - export_timestamp: datetime.datetime  # När export skapades
```

## Export mapping (Excel)

Datamodellen mappas till Excel-kolumner enligt följande. Detta fastlåser tolkningen och säkerställer korrekt Excel-export.

**Excel-kolumnordning** (exakt ordning):
1. Fakturanummer
2. Referenser
3. Företag
4. Fakturadatum
5. Beskrivning
6. Antal
7. Enhet
8. Á-pris
9. Rabatt
10. Summa
11. Hela summan

**Mappning**:

| Datamodell | Excel-kolumn | Typ | Noter |
|------------|--------------|-----|-------|
| `InvoiceSpecification.invoice_number` | Fakturanummer | Text | |
| `InvoiceSpecification.customer_reference` eller `InvoiceHeader.customer_reference` | Referenser | Text | Valfritt fält |
| `InvoiceSpecification.supplier_name` | Företag | Text | |
| `InvoiceSpecification.invoice_date` | Fakturadatum | Text | Formaterat som datum-sträng (YYYY-MM-DD) |
| `InvoiceLine.description` | Beskrivning | Text | |
| `InvoiceLine.quantity` | Antal | Numerisk | Kan vara tom om saknas |
| `InvoiceLine.unit` | Enhet | Text | T.ex. "st", "kg", "h" |
| `InvoiceLine.unit_price` | Á-pris | Numerisk | Enhetspris |
| `InvoiceLine.discount` | Rabatt | Numerisk | Decimal (0.10 = 10%) eller belopp |
| `InvoiceLine.total_amount` | Summa | Numerisk | Totalt belopp för raden |
| `Reconciliation.extracted_total` eller `Reconciliation.calculated_total` | Hela summan | Numerisk | Totalt belopp för fakturan |

**Viktigt**:
- En rad i Excel = en `InvoiceLine`
- Återkommande fält (Fakturanummer, Referenser, Företag, Fakturadatum) upprepas på varje rad
- Tomma valfria fält (Rabatt, Referenser) visas som tom cell eller "-"
- Numeriska fält måste vara numeriska i Excel (inte text)
- Textfält måste vara text i Excel

## Fastlåsta fältnamn

Dessa fältnamn **får INTE ändras** utan diskussion:

- `Token`: `text`, `x`, `y`, `width`, `height`
- `Row`: `tokens`, `y`, `text`
- `Segment`: `segment_type`, `rows`
- `InvoiceHeader`: `invoice_number`, `invoice_date`, `supplier_name`, `customer_name`
- `InvoiceLine`: `description`, `quantity`, `unit`, `unit_price`, `discount`, `total_amount`
- `Reconciliation`: `calculated_subtotal`, `extracted_subtotal`, `calculated_total`, `extracted_total`
- `Validation`: `status`, `messages`

## Type hints

Alla strukturer ska implementeras med Python type hints:

```python
from typing import List, Optional
from datetime import date, datetime

class Token:
    text: str
    x: float
    y: float
    width: float
    height: float
    # ...
```

## Serialisering

Strukturer kan serialiseras till dict för JSON/CSV-export:

```python
# Exempel: InvoiceLine → dict för CSV
{
    "line_number": 1,
    "description": "Produkt A",
    "quantity": 2.0,
    "unit": "st",
    "unit_price": 100.0,
    "discount": 0.10,  # 10% rabatt
    "total_amount": 200.0,
    "vat_rate": 0.25
}
```

## Spårbarhet och källsanning

**Kritiskt**: Tokens och Rows är **källsanning** med full spårbarhet:

- **Token**: Grundläggande dataenhet med position (x, y, width, height) och text
- **Row**: Gruppering av tokens med spårbarhet via `tokens`-listan
- **InvoiceLine**: Kan spåras tillbaka till `rows`, som i sin tur spåras tillbaka till `tokens` och `page`

**Användning**:
- För exakt positionering eller spårbarhet: Använd `tokens` direkt (inte `Row.text`)
- `Row.text` är endast en hjälprepresentation för enkel textåtkomst
- Alla strukturer måste kunna spåras tillbaka till ursprunglig `Page` och `Token`
