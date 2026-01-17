# Invoice Pipeline v1 - Specifikation

## Översikt

Denna pipeline definierar 12 steg för att transformera en PDF-faktura till strukturerad tabell-data. Varje steg beskriver transformationen, ingångsdata, utgångsdata och regler för bearbetning.

## Pipeline-steg

### Steg 1: PDF → Document

**Beskrivning**: Läser in PDF-filen och skapar en Document-struktur.

**Input**: 
- Filväg till PDF-fil

**Output**: 
- Document-objekt med metadata (filnamn, sökväg, sidantal)

**Regler**:
- PDF:en måste kunna läsas (inte korrupt)
- Alla sidor extraheras från dokumentet
- Metadata sparas för senare referens

---

### Steg 2: Document → Page

**Beskrivning**: Extraherar individuella sidor från Document.

**Input**: 
- Document-objekt

**Output**: 
- Lista av Page-objekt (en per sida)
- Varje Page innehåller sidnumret och referens till ursprunglig PDF-sida

**Regler**:
- Varje sida bearbetas separat
- Sidnumrering börjar på 1
- Multi-sidiga fakturor hanteras sekventiellt

---

### Steg 3: Page → Tokens

**Beskrivning**: Tokeniserar textinnehållet på varje sida med spatial information (positioner).

**Input**: 
- Page-objekt

**Output**: 
- Lista av Token-objekt
- Varje Token innehåller: text, x, y, width, height (position och dimensioner)

**Regler**:
- Tokens identifieras genom OCR eller PDF-textextraktion
- Positionsdata (x, y, width, height) måste sparas exakt
- Tokens behåller sin ordning i dokumentflödet
- Whitespace och formatering bevaras i position-data

---

### Steg 4: Tokens → Rows

**Beskrivning**: Grupperar tokens i logiska rader baserat på Y-position.

**Input**: 
- Lista av Token-objekt

**Output**: 
- Lista av Row-objekt
- Varje Row innehåller tokens som har samma (eller närmaste) Y-position

**Regler**:
- **Rad med belopp = produktrad**: En rad som innehåller ett numeriskt belopp tolkas som en produktrad
- Tokens på samma Y-position (med liten tolerans) grupperas i samma rad
- Radordning behålls (top-to-bottom)
- Varje rad har en unik Y-position

---

### Steg 5: Rows → Segments

**Beskrivning**: Identifierar logiska segment (header, items/body, footer) baserat på innehåll och position.

**Input**: 
- Lista av Row-objekt

**Output**: 
- Lista av Segment-objekt med typ: header, items, footer

**Regler**:
- **Header**: Övre del av dokumentet (vanligtvis topp 20-30%)
- **Items**: Mittdel med produktrader
- **Footer**: Nedre del med totaler och summor
- Segment-identifiering baseras på position och innehållsanalys

---

### Steg 6: Segments → Zoner

**Beskrivning**: Skapar spatiala zoner för kontextuell analys och positionering.

**Input**: 
- Lista av Segment-objekt

**Output**: 
- Lista av Zone-objekt med spatiala gränser och typ

**Regler**:
- Zoner definierar rektangulära områden på sidan
- Olika zoner kan överlappa eller vara disjunkta
- Zoner hjälper till att identifiera kontext (ex: datum-område, belopps-kolumn)

---

### Steg 7: Zoner → Header

**Beskrivning**: Identifierar fakturahuvudet (header-segment) och dess innehåll.

**Input**: 
- Lista av Zone-objekt
- Segment-objekt av typ "header"

**Output**: 
- InvoiceHeader-objekt med identifierade fält

**Regler**:
- Header-scoring används för att identifiera mest troliga header-segment
- Fält som identifieras: fakturanummer, datum, leverantörsnamn, kundnamn
- Scoring baseras på position, formatering och nyckelord

---

### Steg 8: Header → Specifikation

**Beskrivning**: Extraherar metadata från InvoiceHeader (fakturanummer, datum, leverantör, etc.).

**Input**: 
- InvoiceHeader-objekt

**Output**: 
- InvoiceSpecification-objekt med strukturerad metadata

**Regler**:
- Fakturanummer: identifieras via nyckelord ("invoice", "faktura", "no.", "nr") + efterföljande värde
- Datum: identifieras via datumformat (YYYY-MM-DD, DD/MM/YYYY, etc.)
- Leverantör: oftast i övre vänstra eller högra delen av header
- Kund: kan finnas i header eller separat avsnitt

---

### Steg 9: Segments → InvoiceLine

**Beskrivning**: Identifierar produktrader från items-segment och skapar InvoiceLine-objekt.

**Input**: 
- Segment-objekt av typ "items"
- Row-objekt från items-segment

**Output**: 
- Lista av InvoiceLine-objekt

**Regler**:
- **Rad med belopp = produktrad**: Alla rader som innehåller numeriska belopp tolkas som produktrader
- Varje InvoiceLine innehåller: beskrivning, kvantitet, enhetspris, totalt belopp
- Fortsättningsrader (wrapped text) kopplas till samma InvoiceLine

---

### Steg 10: InvoiceLine → Reconciliation

**Beskrivning**: Beräknar totalsummor och validerar aritmetik (summor, skatt, etc.).

**Input**: 
- Lista av InvoiceLine-objekt
- Footer-segment med totalsummor

**Output**: 
- Reconciliation-objekt med:
  - Beräknade summor (line totals, subtotal, tax, grand total)
  - Skillnader mellan beräknade och extraherade värden

**Regler**:
- Summa av alla InvoiceLine-totals = subtotal
- Subtotal + skatt = grand total
- Avvikelser flaggas för granskning

---

### Steg 11: Reconciliation → Validation

**Beskrivning**: Kvalitetskontroll och statusbestämning (OK/Warning/Review).

**Input**: 
- Reconciliation-objekt

**Output**: 
- Validation-objekt med status (OK/Warning/Review) och meddelanden

**Regler**:
- **OK**: Alla summor stämmer, alla fält extraherade
- **Warning**: Små avvikelser eller vissa fält saknas
- **Review**: Större avvikelser eller kritiska fält saknas

---

### Steg 12: Validation → Export

**Beskrivning**: Genererar slutlig tabell (CSV/Excel) med strukturerad data.

**Input**: 
- Validation-objekt
- InvoiceHeader/Specification
- Lista av InvoiceLine-objekt

**Output**: 
- CSV-fil eller Excel-fil med:
  - Header-rad med metadata
  - Produktrader med alla fält
  - Footer med summor

**Regler**:
- CSV ska vara UTF-8 kodad
- Excel-format ska inkludera formatering
- Alla numeriska värden formateras korrekt

---

## Pipeline-övergångar

Varje steg i pipelinen representerar en transformation mellan två datatyper:

1. PDF → Document
2. Document → Page
3. Page → Tokens
4. Tokens → Rows
5. Rows → Segments
6. Segments → Zoner
7. Zoner → Header
8. Header → Specifikation
9. Segments → InvoiceLine
10. InvoiceLine → Reconciliation
11. Reconciliation → Validation
12. Validation → Export

## Viktiga regler

- **Rad med belopp = produktrad**: Denna regel är central för identifiering av produktrader i steg 4 och 9
- Alla transformationer måste bevara spårbarhet (tracking) mellan steg
- Position-data (x, y, width, height) måste bevaras genom hela pipelinen
- Felhantering måste implementeras för varje steg

## Definitioner

- **Document**: Översta container för PDF-innehållet
- **Page**: En individuell sida från dokumentet
- **Token**: En text-enhet med position och dimensioner
- **Row**: En logisk rad med tokens grupperade på Y-position
- **Segment**: Ett logiskt avsnitt (header/items/footer)
- **Zone**: Ett spatialt område på sidan
- **InvoiceHeader**: Extraherad header-data
- **InvoiceLine**: En produktrad med beskrivning, kvantitet, pris, totalt
- **Reconciliation**: Beräknade och extraherade summor
- **Validation**: Status och kvalitetskontroll-resultat
