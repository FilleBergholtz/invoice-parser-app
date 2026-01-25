# Invoice Pipeline v1 - Specifikation

## Översikt

Denna pipeline definierar 10 steg för att transformera en PDF-faktura till strukturerad tabell-data. Varje steg beskriver transformationen, ingångsdata, utgångsdata och regler för bearbetning.

> **Notera:** Denna specifikation beskriver den faktiska implementationen. Vissa teoretiska steg (Zones, InvoiceSpecification, Reconciliation som separata datatyper) har optimerats bort eller integrerats i andra steg. Se `SPEC_ANALYSIS.md` för detaljerad jämförelse med tidigare teoretiska versioner.

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
- Tokens identifieras genom OCR eller PDF-textextraktion (pdfplumber)
- **Standardflöde:** Motorn kör både pdfplumber och OCR per faktura, jämför resultat (validering + konfidens) och använder bästa källan. Vid konfidens &lt; 95 % används AI-fallback om aktiverad. Med `--no-compare-extraction` körs endast pdfplumber.
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

### Steg 6: Segments → InvoiceLine

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

### Steg 7: Segments → Header

**Beskrivning**: Identifierar fakturahuvudet (header-segment) och extraherar header-fält.

**Input**: 
- Segment-objekt av typ "header"

**Output**: 
- InvoiceHeader-objekt med identifierade fält (fakturanummer, datum, leverantör, kund)

**Regler**:
- Header-scoring används för att identifiera mest troliga header-segment
- Fält som identifieras: fakturanummer, datum, leverantörsnamn, kundnamn
- Scoring baseras på position, formatering och nyckelord
- Konfidensscoring används för varje fält (0.0-1.0)
- Hard gate: fakturanummer och totalsumma måste ha ≥0.95 konfidens för OK-status

---

### Steg 8: Segments → Footer (Total Amount)

**Beskrivning**: Extraherar totalsumma från footer-segment.

**Input**: 
- Segment-objekt av typ "footer"
- Lista av InvoiceLine-objekt (för matematisk validering)

**Output**: 
- InvoiceHeader uppdateras med total_amount, total_confidence, total_traceability

**Regler**:
- Identifierar "Att betala", "Total", "Summa att betala", "Totalt" och liknande nyckelord
- Validerar mot summa av InvoiceLine-totals (matematisk kontroll)
- Konfidensscoring baseras på position, nyckelord-proximitet och matematisk validering
- Hard gate: totalsumma måste ha ≥0.95 konfidens för OK-status

---

### Steg 9: InvoiceHeader + InvoiceLines → Validation

**Beskrivning**: Kvalitetskontroll, reconciliation (summa-validering) och statusbestämning (OK/PARTIAL/REVIEW).

**Input**: 
- InvoiceHeader-objekt (med fakturanummer, totalsumma, konfidensvärden)
- Lista av InvoiceLine-objekt

**Output**: 
- ValidationResult-objekt med:
  - Status (OK/PARTIAL/REVIEW/FAILED)
  - lines_sum (beräknad summa av alla InvoiceLine-totals)
  - diff (skillnad mellan total_amount och lines_sum)
  - errors och warnings

**Regler**:
- **Reconciliation**: Beräknar lines_sum = SUM(alla InvoiceLine.total_amount)
- **Diff-beräkning**: diff = total_amount - lines_sum
- **Tolerans**: ±1.00 SEK för avrundning och frakt/rabatt-rader
- **Status-logik**:
  - **OK**: Hard gate pass (fakturanummer ≥0.95 AND totalsumma ≥0.95) AND diff ≤ ±1 SEK
  - **PARTIAL**: Hard gate pass AND diff > ±1 SEK (summa-avvikelse men header säker)
  - **REVIEW**: Hard gate fail OR total_amount saknas OR diff stor
- **Hard gate**: Ingen OK-status om inte både fakturanummer och totalsumma har ≥0.95 konfidens

---

### Steg 10: Validation → Export

**Beskrivning**: Genererar slutlig tabell (CSV/Excel) med strukturerad data.

**Input**: 
- ValidationResult-objekt
- InvoiceHeader-objekt
- Lista av InvoiceLine-objekt

**Output**: 
- Excel-fil med:
  - En rad per InvoiceLine (produktrad)
  - Fakturametadata upprepas per rad (fakturanummer, datum, leverantör, etc.)
  - Kontrollkolumner: Status, LinesSum, Diff, InvoiceNoConfidence, TotalConfidence
  - Review-rapporter (PDF + JSON) för REVIEW-status fakturor

**Regler**:
- Excel ska vara UTF-8 kodad
- Excel-format inkluderar formatering
- Alla numeriska värden formateras korrekt
- Review-rapporter skapas automatiskt för fakturor med REVIEW-status

---

## Pipeline-övergångar

Varje steg i pipelinen representerar en transformation mellan två datatyper:

1. PDF → Document
2. Document → Page
3. Page → Tokens
4. Tokens → Rows
5. Rows → Segments
6. Segments → InvoiceLine
7. Segments → Header
8. Segments → Footer (Total Amount)
9. InvoiceHeader + InvoiceLines → Validation (inkluderar reconciliation)
10. Validation → Export

## Viktiga regler

- **Rad med belopp = produktrad**: Denna regel är central för identifiering av produktrader i steg 4 och 9
- Alla transformationer måste bevara spårbarhet (tracking) mellan steg
- Position-data (x, y, width, height) måste bevaras genom hela pipelinen
- Felhantering måste implementeras för varje steg

## Definitioner

- **Document**: Översta container för PDF-innehållet
- **Page**: En individuell sida från dokumentet
- **Token**: En text-enhet med position och dimensioner (x, y, width, height)
- **Row**: En logisk rad med tokens grupperade på Y-position
- **Segment**: Ett logiskt avsnitt (header/items/footer) identifierat från rader
- **InvoiceHeader**: Extraherad header-data med fält (fakturanummer, datum, leverantör, kund, totalsumma) och konfidensvärden
- **InvoiceLine**: En produktrad med beskrivning, kvantitet, enhet, enhetspris, rabatt, totalt belopp
- **ValidationResult**: Status (OK/PARTIAL/REVIEW/FAILED), reconciliation-värden (lines_sum, diff), errors och warnings
- **Zone**: Konceptuellt område på sidan (t.ex. "header zone", "footer zone") - används i confidence scoring men inte som separat datatyp

## Noteringar

- **Zones**: Zones används konceptuellt i confidence scoring (t.ex. "header zone" = topp 20-30% av sidan) men finns inte som separata Zone-objekt i implementationen.
- **InvoiceSpecification**: Fanns i tidigare teoretiska versioner men har ersatts av InvoiceHeader som innehåller alla fält direkt.
- **Reconciliation**: Reconciliation-logiken (beräkning av lines_sum och diff) är integrerad i validation-steget (steg 9) och lagras i ValidationResult, inte som separat Reconciliation-objekt.
