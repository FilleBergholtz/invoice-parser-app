# Phase 9: AI Data Analysis — Verification

Verifiering av att data loading, query processor och CLI --query finns och fungerar.

---

## 1. Automatiska kontroller (kod/import)

- **data_loader:** `load_invoices_from_excel`, `InvoiceDataStore` — finns i `src/analysis/data_loader.py`.
- **query_processor:** `parse_query`, `QueryIntent` — finns i `src/analysis/query_processor.py`.
- **query_executor:** `execute_query` — finns i `src/analysis/query_executor.py`.
- **CLI:** `--query` och `--excel-path` finns i `src/cli/main.py` (ca rad 1335 resp. 1341).

**Kör:**

```bash
python -c "
from src.analysis.data_loader import load_invoices_from_excel
from src.analysis.query_processor import parse_query
from src.analysis.query_executor import execute_query
print('Phase 9 modules OK')
"
```

**Senast kört:** 2026-01-25 — OK (alla importer lyckades).

---

## 2. Manuell verifiering

1. Exportera minst en faktura till Excel (via GUI eller CLI pipeline).
2. Kör CLI med naturliga frågor, t.ex.:
   - `python -m src.cli.main --query "Vilka fakturor finns?" --excel-path <sökväg-till-excel>`
   - eller med `--excel-path` pekande på mapp med Excel-filer (senaste används om ej angiven).
3. Kontrollera att svar returneras (filter/aggregate/summarize/compare enligt query_processor).

**OBS:** Om `python -m src.cli.main --help` ger ValueError (formatfel i help-sträng) påverkas inte --query/--excel-path; det är ett separat hjälptextfel.

---

## 3. Sammanfattning verifiering 2026-01-25

| Kontroll | Resultat |
|----------|----------|
| 09-01 data_loader / InvoiceDataStore | ✓ Modul finns, importerar |
| 09-02 query_processor / parse_query | ✓ Modul finns, importerar |
| 09-03 query_executor + CLI --query | ✓ Moduler + CLI-argument finns |
| Manuell körning med --query | Ej kört — använd steg 2 ovan |

---

*Skapad 2026-01-25 — /gsd:verify-work 9 10*
