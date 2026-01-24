# Atomiska Tasks

## Översikt

Varje task mappar 1:1 till en pipeline-övergång enligt `specs/invoice_pipeline_v1.md`. Tasks implementeras sekventiellt enligt roadmap-faserna i `docs/roadmap.md`.

## Task-format

Varje task följer strikt format:
- **[T#] Titel**
- **Input**: Input-typ från pipeline
- **Output**: Output-typ till pipeline
- **Files**: Filer som ska skapas/modifieras
- **DoD**: Definition of Done (kriterier för att task är klar)

## Fas 1: Vertical Slice Tasks

**OBS**: Tasks T1–T5 är **gates** - de fokuserar på analyskvalitet och stabil representation. DoD mäter explicit analyskvalitet, inte bara att något "fungerar".

### [T1] PDF → Document

**Input**: Filväg till PDF-fil (str)

**Output**: Document-objekt

**Files**: 
- `src/document.py` (Document-klass)
- `src/reader.py` (PDF-läsning)
- `tests/test_document.py` (Unit tests)

**DoD**:
- [x] Document-klass implementerad enligt `docs/02_data-model.md`
- [x] Kan läsa PDF-fil och skapa Document
- [x] Metadata (filename, filepath, page_count) extraheras korrekt
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [T2] Document → Page

**Input**: Document-objekt

**Output**: List[Page]

**Files**:
- `src/page.py` (Page-klass)
- `src/reader.py` (Page-extraktion)
- `tests/test_page.py` (Unit tests)

**DoD**:
- [x] Page-klass implementerad enligt `docs/02_data-model.md`
- [x] Kan extrahera alla sidor från Document
- [x] Sidnumrering börjar på 1
- [x] Varje Page har korrekt width/height
- [x] **Alla sidor extraheras och sparas som Page-objekt även om PDF är 1 sida**
- [x] **Page width/height används konsekvent av senare steg (koordinatsystem)**
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [T3] Page → Tokens

**Input**: Page-objekt

**Output**: List[Token]

**Files**:
- `src/token.py` (Token-klass)
- `src/tokenizer.py` (Tokenisering med pdfplumber eller OCR)
- `tests/test_tokenizer.py` (Unit tests)

**DoD**:
- [x] Token-klass implementerad enligt `docs/02_data-model.md`
- [x] Kan extrahera tokens med positioner (x, y, width, height)
- [x] Alla tokens har text och spatial information
- [x] Token-ordning bevaras
- [x] **Tokens har position (x,y,w,h) och text, samt kan kopplas tillbaka till sida**
- [x] **Logga andel tokens och markera 'scan-like' om embedded text saknas** (det gör OCR-beslutet senare deterministiskt)
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [T4] Tokens → Rows

**Input**: List[Token]

**Output**: List[Row]

**Files**:
- `src/row.py` (Row-klass)
- `src/row_grouping.py` (Token-gruppering till rader)
- `tests/test_row_grouping.py` (Unit tests)

**DoD**:
- [x] Row-klass implementerad enligt `docs/02_data-model.md`
- [x] Kan gruppera tokens i rader baserat på Y-position
- [x] Tolerans för Y-position fungerar korrekt
- [x] Radordning bevaras (top-to-bottom)
- [x] **Radordning top-to-bottom verifieras på testkorpus**
- [x] **Row.text är endast en hjälprepresentation – tokens är källan** (minskar risken att ni börjar semantisera för tidigt)
- [x] Regel: "rad med belopp = produktrad" dokumenterad
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [T5] Rows → Segments

**Input**: List[Row]

**Output**: List[Segment]

**Files**:
- `src/segment.py` (Segment-klass)
- `src/segment_identification.py` (Segment-identifiering)
- `tests/test_segment_identification.py` (Unit tests)

**DoD**:
- [x] Segment-klass implementerad enligt `docs/02_data-model.md`
- [x] Kan identifiera header, items, footer baserat på position
- [x] Segment-typer är korrekt satta
- [x] Header-område: övre 20-30% identifieras
- [x] Footer-område: nedre del identifieras
- [x] Items-område: mittdel identifieras
- [x] **Segmentering (header/items/footer) krävs även om den är grov** (för att styra senare parsing)
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [T6] Segments → InvoiceLine

**Input**: Segment (typ "items") med List[Row]

**Output**: List[InvoiceLine]

**Files**:
- `src/invoice_line.py` (InvoiceLine-klass)
- `src/invoice_line_parser.py` (Produktrad-parsing)
- `tests/test_invoice_line_parser.py` (Unit tests)

**DoD**:
- [x] InvoiceLine-klass implementerad enligt `docs/02_data-model.md`
- [x] Kan identifiera produktrader från items-segment
- [x] Regel: "rad med belopp = produktrad" implementerad
- [x] Beskrivning, kvantitet, pris, total extraheras
- [x] Enklaste implementation (ingen wrap-hantering ännu)
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [T7] InvoiceLine → Export (Interim CSV)

**Input**: InvoiceSpecification (placeholder), List[InvoiceLine]

**Output**: CSV-fil (interim för debugging)

**Files**:
- `src/export.py` (Interim CSV-export för debugging)
- `src/main.py` (CLI-entry point)
- `tests/test_export.py` (Unit tests)

**DoD**:
- [x] Kan exportera InvoiceLine till CSV (interim för debugging)
- [x] CSV innehåller kolumner: description, quantity, unit_price, total_amount
- [x] UTF-8 kodning fungerar korrekt
- [x] CLI-entry point fungerar: `python -m src.main input.pdf output.csv`
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`
- [x] **Fas 1 komplett**: End-to-end pipeline fungerar

**OBS**: Detta är interim-export. Slutleverans är Excel (se T15).

---

## Fas 2: Header + Wrap Tasks

### [T8] Segments → Zoner

**Input**: List[Segment]

**Output**: List[Zone]

**Files**:
- `src/zone.py` (Zone-klass)
- `src/zone_identification.py` (Spatial zonering)
- `tests/test_zone_identification.py` (Unit tests)

**DoD**:
- [x] Zone-klass implementerad enligt `docs/02_data-model.md`
- [x] Kan skapa spatiala zoner baserat på position
- [x] Olika zon-typer identifieras (header, date, amount, items)
- [x] Zoner hjälper till att identifiera kontext
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [T9] Zoner → Header

**Input**: List[Zone], Segment (typ "header")

**Output**: InvoiceHeader

**Files**:
- `src/invoice_header.py` (InvoiceHeader-klass)
- `src/header_identification.py` (Header-scoring och identifiering)
- `tests/test_header_identification.py` (Unit tests)

**DoD**:
- [x] InvoiceHeader-klass implementerad enligt `docs/02_data-model.md`
- [x] Header-scoring fungerar baserat på position och nyckelord
- [x] Konfidenspoäng beräknas korrekt
- [x] Header-segment identifieras korrekt
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [T10] Header → Specifikation

**Input**: InvoiceHeader

**Output**: InvoiceSpecification

**Files**:
- `src/invoice_specification.py` (InvoiceSpecification-klass)
- `src/header_parser.py` (Metadata-extraktion från header)
- `tests/test_header_parser.py` (Unit tests)

**DoD**:
- [x] InvoiceSpecification-klass implementerad enligt `docs/02_data-model.md`
- [x] Fakturanummer extraheras (via nyckelord + värde)
- [x] Datum extraheras (stödjer flera datumformat)
- [x] Leverantörsnamn extraheras
- [x] Kundnamn extraheras (om tillgängligt)
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [T11] Förbättring: Fortsättningsrader (Wrap)

**Input**: List[Row] (med wraps), List[InvoiceLine]

**Output**: List[InvoiceLine] (med kopplade wraps)

**Files**:
- `src/invoice_line_parser.py` (Uppdaterad wrap-hantering)
- `tests/test_invoice_line_wrap.py` (Unit tests)

**DoD**:
- [x] Fortsättningsrader identifieras korrekt
- [x] Wrapped text kopplas till rätt InvoiceLine
- [x] Beskrivning konsolideras från alla rader i InvoiceLine
- [x] Belopp finns bara på sista raden i wrapped text
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf` (om den har wraps)
- [x] **Fas 2 komplett**: Header + wrap fungerar

---

## Fas 3: Validering Tasks

### [T12] InvoiceLine → Reconciliation

**Input**: List[InvoiceLine], Segment (typ "footer")

**Output**: Reconciliation

**Files**:
- `src/reconciliation.py` (Reconciliation-klass)
- `src/reconciliation_calculator.py` (Summa-beräkning)
- `tests/test_reconciliation.py` (Unit tests)

**DoD**:
- [x] Reconciliation-klass implementerad enligt `docs/02_data-model.md`
- [x] Beräknar subtotal från InvoiceLine-totals
- [x] Extraherar subtotal/tax/total från footer
- [x] Beräknar skillnader mellan beräknade och extraherade summor
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [T13] Reconciliation → Validation

**Input**: Reconciliation

**Output**: Validation

**Files**:
- `src/validation.py` (Validation-klass)
- `src/validator.py` (Valideringsregler enligt `docs/05_validation.md`)
- `tests/test_validation.py` (Unit tests)

**DoD**:
- [x] Validation-klass implementerad enligt `docs/02_data-model.md`
- [x] Status sätts korrekt: OK/Warning/Review
- [x] Valideringsregler implementerade enligt `docs/05_validation.md`
- [x] Meddelanden genereras för fel/varningar
- [x] Saknade fält identifieras
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf` och edge cases

---

### [T14] Validation → Validation Result

**Input**: Reconciliation

**Output**: Validation

**Beskrivning**: Valideringsresultat skapas och kontrollerar om Excel-export ska tillåtas.

**Files**:
- `src/validation.py` (Validation-klass)
- `src/validator.py` (Valideringsregler enligt `docs/05_validation.md`)
- `tests/test_validation.py` (Unit tests)

**DoD**:
- [x] Validation-klass implementerad enligt `docs/02_data-model.md`
- [x] Status sätts korrekt: OK/Warning/Review
- [x] Valideringsregler implementerade enligt `docs/05_validation.md`
- [x] Validation failures blockerar Excel-generering om inte explicit overridden
- [x] Meddelanden genereras för fel/varningar
- [x] Saknade fält identifieras
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf` och edge cases

---

### [T15] Build final Excel export

**Input**: InvoiceSpecification, List[InvoiceLine], Reconciliation, Validation

**Output**: Excel-fil (slutresultat)

**Files**:
- `src/excel_export.py` (Excel-export)
- `src/export.py` (Uppdaterad med Excel-support)
- `src/main.py` (Uppdaterad CLI för Excel)
- `tests/test_excel_export.py` (Unit tests)

**DoD**:
- [x] Excel-fil skapas som slutresultat
- [x] En rad per InvoiceLine
- [x] Korrekt kolumnordning (exakt ordning):
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
- [x] Excel öppnas utan varningar
- [x] Numeriska fält är numeriska (ej text) - Antal, Á-pris, Rabatt, Summa, Hela summan
- [x] Textfält är text - Fakturanummer, Referenser, Företag, Fakturadatum, Beskrivning, Enhet
- [x] SUM(Summa) per faktura ≈ Hela summan (verifiering i Excel)
- [x] Tomma valfria fält (t.ex. Rabatt, Referenser) hanteras korrekt (tomma celler eller "-")
- [x] Återkommande fakturafält upprepas korrekt per rad
- [x] Unit tests passerar
- [x] Minst en faktura från testkorpus exporteras korrekt och manuellt kontrollerad i Excel
- [x] **Fas 3 komplett**: Fullständig pipeline med validering och Excel-export

---

## Fas 4: Cleanup (Remove non-target deployment types)

### [U0] Cleanup: Remove non-target deployment modes

**Input**: Repo med flera deploymentspår (Streamlit/FastAPI/Docker/Cloud)

**Output**: Repo med endast Windows Desktop (production) + CLI (advanced) + Dev setup

**Files**:
- `docs/deployment.md` (Uppdatera: endast Desktop/CLI/Dev/Optional AI)
- `README.md` (Uppdatera: endast Desktop/CLI)
- `docs/legacy/deployment_legacy.md` (Ny: flytta gammal info om ni vill behålla)
- `pyproject.toml` (Rensa dependencies)
- (Delete or move to legacy):
  - `run_streamlit.py`
  - `run_api.py`
  - `src/api/`
  - `Dockerfile.*`
  - `docker-compose.yml`
  - cloud-specifika filer/scripts (om finns)

**DoD**:
- [x] “Production target” i docs/README är endast Windows Desktop
- [x] CLI är dokumenterad som secondary/advanced
- [x] Inga Streamlit/FastAPI/Docker/Cloud instruktioner i primär dokumentation
- [x] Streamlit/FastAPI/Docker-relaterade dependencies borttagna ur `pyproject.toml` (om ej använda)
- [x] Tester passerar
- [x] Repo-struktur har tydlig `docs/legacy/` för bortplockat material (om ni behåller historik)

---

## Fas 5: Windows Desktop (Offline-first)

**Mål**: Appen ska kunna installeras och köras lokalt på en Windows-dator utan webbberoende. AI ska kunna anslutas som ett valfritt (opt-in) nätverkssteg.

### [U1] CLI Run Summary + Artifacts Contract

**Input**: PDF-filväg (str), output_dir (str)

**Output**: `run_summary.json` + artifacts-mapp + Excel-fil (via befintlig pipeline)

**Files**:
- `src/run_summary.py` (Ny: RunSummary-modell + serializer)
- `src/main.py` (Uppdaterad CLI: `--artifacts-dir`, `--run-summary`)
- `tests/test_run_summary.py` (Unit tests)

**DoD**:
- [x] `run_summary.json` skapas alltid vid körning
- [x] Innehåller minst: run_id, input_file, output_excel, artifacts_dir, started_at, finished_at, durations_per_stage, validation_status
- [x] Artifacts-mappen skapas deterministiskt (t.ex. `artifacts/<run_id>/...`)
- [x] CLI returnerar exit code 0 vid OK/Warning och !=0 vid Review/Failure (konfigurerbart)
- [x] Unit tests passerar
- [x] Testat med `sample_invoice_1.pdf`

---

### [U2] Windows Engine Executable (No Python Required)

**Input**: Repo + dependencies

**Output**: `invoice_engine.exe` som kan köras utan Python installerat

**Files**:
- `build/windows/build_engine.py` (Ny: build script)
- `build/windows/invoice_engine.spec` (PyInstaller spec)
- `docs/deployment_windows_desktop.md` (Ny: bygginstruktioner)

**DoD**:
- [x] `dist/invoice_engine.exe` byggs deterministiskt
- [x] Kör: `invoice_engine.exe input.pdf --out outdir --artifacts artifactsdir`
- [x] Skapar Excel + `run_summary.json` enligt U1
- [x] Kör på ren Windows-maskin utan Python (verifierat)
- [x] Build-instruktion dokumenterad
- [x] (Valfritt) Code signing placeholder dokumenterad

---

### [U3] Windows Desktop UI (Local, No Browser)

**Input**: PDF-filväg (via filväljare/drag-drop)

**Output**: Lokal GUI-app som kör `invoice_engine.exe` och visar resultat

**Files**:
- `ui/app.py` (Ny: PySide6/Qt app entry)
- `ui/views/main_window.py` (Ny: huvudvy)
- `ui/services/engine_runner.py` (Ny: kör engine + progress/logg)
- `tests/test_ui_smoke.py` (Smoke test, om möjligt)

**DoD**:
- [x] UI kan välja PDF och starta bearbetning
- [x] Visar status (Running/Done/Failed) och valideringsstatus (OK/Warning/Review)
- [x] Visar output paths (Excel + artifacts) och kan öppna output-mapp
- [x] Ingen webbläsare/localhost används
- [x] Appen fungerar offline (utan nät)
- [x] Minst ett manuellt test på Windows med `sample_invoice_1.pdf`

---

### [U4] AI Connector (Optional Online Enrichment)

**Input**: InvoiceSpecification + List[InvoiceLine] (från lokal parsing)

**Output**: Uppdaterad InvoiceSpecification + List[InvoiceLine] + AI-diff för spårbarhet

**Files**:
- `src/ai/client.py` (Ny: HTTP-klient + datakontrakt)
- `src/ai/schemas.py` (Ny: request/response modeller)
- `src/config.py` (Uppdaterad: AI_ENABLED, AI_ENDPOINT, AI_KEY)
- `tests/test_ai_client.py` (Unit tests med mocked HTTP)

**DoD**:
- [x] AI är opt-in: default `AI_ENABLED=false`
- [x] Vid offline/nätfel: pipeline fortsätter utan AI och loggar warning
- [x] AI request/response sparas i artifacts (`ai_request.json`, `ai_response.json`, `ai_diff.json`)
- [x] Unit tests passerar (mockad server)
- [x] Inga secrets hårdkodas (endast env/config)

---

# Nya Tasks – Post-completion Enhancements

Detta dokument innehåller **nya tasks som adderas efter att samtliga befintliga T/U-tasks är färdigställda**.  
Inga befintliga tasks ändras eller öppnas upp igen.

Syftet är att höja **observability, produktvärde, robusthet och förvaltbarhet**.

---

## Fas 6: Observability, Robusthet & Förvaltning

### [N1] Deterministic Debug Artifacts (Post-run Observability)

**Input**: `run_summary.json`, artifacts från pipeline  
**Output**: `artifact_manifest.json` per run

**Files**:
- `src/debug/artifact_index.py`
- `src/debug/artifact_manifest.py`
- `tests/test_artifact_manifest.py`

**DoD**:
- [x] Varje körning genererar `artifact_manifest.json`
- [x] Manifest listar alla artifacts med:
  - filnamn
  - typ (tokens, rows, segments, ai, excel, debug)
  - pipeline-steg
  - checksum/hash
- [x] Manifest är maskinläsbart och versionsmärkt
- [x] Enhetstest verifierar komplett manifest för `sample_invoice_1.pdf`

---

### [N2] Invoice Quality Score

**Input**: Validation, Reconciliation, InvoiceSpecification, InvoiceLines  
**Output**: `quality_score` (0–100)

**Files**:
- `src/quality/score.py`
- `src/quality/model.py`
- `tests/test_quality_score.py`

**DoD**:
- [x] Quality score beräknas deterministiskt
- [x] Score baseras på:
  - validation status (OK / Warning / Review)
  - antal saknade fält
  - reconciliation diff
  - wrap-komplexitet
- [x] Score sparas i `run_summary.json`
- [x] Score är dokumenterad och testad

---

### [N3] Batch Processing Mode

**Input**: Katalog med PDF-filer  
**Output**: En Excel per PDF + batch-sammanställning

**Files**:
- `src/batch/runner.py`
- `src/batch/batch_summary.py`
- `tests/test_batch_runner.py`

**DoD**:
- [ ] CLI-stöd:  
  `invoice_engine.exe --batch <input_dir> --out <output_dir>`
- [ ] Varje PDF körs isolerat (egen artifacts-mapp)
- [ ] `batch_summary.xlsx` skapas med:
  - filnamn
  - validation status
  - quality score
  - output path
- [ ] Fel i en PDF stoppar inte batch-körningen
- [ ] Enhetstest för batch-logik passerar

---

### [N4] Human Review Package Export

**Input**: Validation med status `Review`  
**Output**: Review-paket (mapp eller ZIP)

**Files**:
- `src/review/review_package.py`
- `tests/test_review_package.py`

**DoD**:
- [ ] Review-paket innehåller:
  - original PDF
  - slutlig Excel
  - `run_summary.json`
  - `artifact_manifest.json`
- [ ] `README.txt` genereras automatiskt med instruktioner
- [ ] UI kan öppna review-mappen direkt
- [ ] Enhetstest verifierar komplett paket

---

## Fas 7: Produktifiering & Långsiktig Drift

### [N5] Config Profiles (Customer / Supplier Templates)

**Input**: Profilnamn (valfritt)  
**Output**: Anpassad pipeline-konfiguration

**Files**:
- `configs/profiles/*.yaml`
- `src/config/profile_loader.py`
- `tests/test_profile_loader.py`

**DoD**:
- [ ] Profiler kan styra:
  - header-nyckelord
  - zon-procent (header/items/footer)
  - belopps- och toleransregler
- [ ] CLI-flagga: `--profile <profile_name>`
- [ ] Default-profil ger exakt samma beteende som idag
- [ ] Profilval sparas i `run_summary.json`

---

### [N6] Safe Upgrade & Backward Compatibility Guard

**Input**: Artifacts från tidigare körningar  
**Output**: Kompatibilitetsvarning eller OK-status

**Files**:
- `src/versioning/compat.py`
- `tests/test_backward_compat.py`

**DoD**:
- [ ] Pipeline-version sparas i `run_summary.json`
- [ ] Appen identifierar äldre artifacts
- [ ] Varning visas vid inkompatibla versioner
- [ ] Dokumenterad backward-compat policy
- [ ] Enhetstester verifierar versionslogik

---

## Rekommenderad implementationsordning

1. **N1 – Deterministic Debug Artifacts**
2. **N2 – Invoice Quality Score**
3. **N3 – Batch Processing Mode**
4. **N4 – Human Review Package**
5. **N5 – Config Profiles**
6. **N6 – Compatibility Guard**

---

## Arkitekturell notering

Samtliga N-tasks:
- Kräver inga ändringar i T1–T15
- Bygger ovanpå befintliga contracts
- Är fullt kompatibla med CLI, Windows exe och UI

Detta bekräftar att den nuvarande pipelinen är stabil, utbyggbar och produktionsredo.

## Nästa task

Nästa task väljs från listan ovan. Implementera EN task i taget och uppdatera DoD-kryss vid completion.

## Implementation-regler

- Implementera EN task i taget
- Markera DoD-kriterier innan du går vidare
- Testa varje task med `sample_invoice_1.pdf`
- Följ datamodellen i `docs/02_data-model.md` exakt
- Referera till `docs/checklist.md` för varje implementation
