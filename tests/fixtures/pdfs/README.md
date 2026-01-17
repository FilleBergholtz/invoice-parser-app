# Test-PDF:er

## Översikt

Denna mapp innehåller PDF-filer som används för testing av invoice-parser pipeline.

## Test-filer

### sample_invoice_1.pdf

**Status**: Placeholder - fil ska läggas till när tillgänglig

**Beskrivning**: En representativ faktura-PDF som används för grundläggande testing av pipeline.

**Se**: `docs/06_test-corpus.md` för detaljerad beskrivning av förväntade resultat och edge cases.

## Användning

1. Lägg PDF-filer i denna mapp för testing
2. Referera till `docs/06_test-corpus.md` för test-specifikationer
3. Använd `sample_invoice_1.pdf` för grundläggande end-to-end testing

## Placeholder

Om `sample_invoice_1.pdf` inte finns tillgänglig ännu:
- Skapa en test-PDF med faktura-innehåll enligt `docs/06_test-corpus.md`
- Eller vänta tills faktisk test-fil finns tillgänglig
- Pipeline kan testas med riktiga faktura-PDF:er när implementerad

## OBS

- PDF-filer i denna mapp ska vara test-data, inte känslig information
- Om faktiska faktura-PDF:er används, se till att de inte innehåller känslig data eller anonymisera dem innan testning
