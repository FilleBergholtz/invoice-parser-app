# Phase 14: Research R1–R4 — Extraction fallback optimization

**Datum:** 2026-01-25  
**Syfte:** Konkreta leverabler för R1–R4 enligt 14-DISCUSS.md. Alla beslut ska kunna översättas till konstanter/regler i kod.

---

## R1 — OCR Rendering Parameters

### Frågor besvarade

- **Är 300 DPI tillräckligt för majoriteten av fakturor?**  
  Ja. Tesseract-dokumentationen (tessdoc ImproveQuality) anger uttryckligen: *"Tesseract works best on images which have a DPI of at least 300 dpi"*. 300 DPI är vedertagen standard för dokument-OCR.

- **Behövs retry vid 400 DPI?**  
  Endast som undantagsåtgärd. Ökning till 400 DPI ger inte generellt bättre noggrannhet; vissa tester visar att det kan ge fler fel (t.ex. förväxling av tecken) och ökar fillstorlek och körtid. Retry vid högre DPI är motiverat **endast** när OCR-kvaliteten på 300 DPI är dålig.

- **Förbättrar omrendering av enbart misslyckade sidor OCR-confidence mätbart?**  
  Ja, om orsaken till låg confidence är för liten text eller otydlig rendering. Omrendering av *enbart* sidor med låg OCR-confidence begränsar kostnad och tid.

- **Finns tydliga fall där högre DPI sänker prestanda utan noggrannhetsvinst?**  
  Ja. Rapporter (t.ex. Tesseract-användarforum) visar att 400 DPI ibland ger sämre recognition (t.ex. "i"→"1"). Högre upplösning ökar också filstorlek och Tesseract-körtid utan garanterad förbättring.

### Leverabler (kodrelevanta)

| Beslut | Värde / regel |
|--------|----------------|
| **Baseline DPI** | **300** |
| **Retry DPI** | **400** |
| **Retry-regel** | Omrendera en sida vid **400 DPI endast om** `ocr_mean_conf < 55` efter OCR på 300 DPI, och endast för den sidan. Max **en** retry per sida. |
| **Övrigt** | Nuvarande `pdf_renderer` använder redan effektivt 300 DPI (Matrix 300/72). Säkerställ att DPI är dokumenterat eller metadata där det behövs för artefakter. |

**Rekommendation B (mean vs median):** Vi använder **mean_conf** för DPI-retry (känsligare för att fånga dåliga sidor) och **median_conf** för routing till AI (robustare mot utslag). Dokumentera i kodkommentar: *"Mean is used for DPI retry sensitivity, median for routing robustness."* så att framtida ändringar inte slår ihop dem.

**Källreferenser:**  
- [Tesseract ImproveQuality — Rescaling](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html)  
- [Stack Overflow: Best resolution for Tesseract-OCR](https://stackoverflow.com/questions/18563433/best-resolution-for-tesseract-ocr)

---

## R2 — OCR Confidence Aggregation

### Frågor besvarade

- **Ska routing använda mean, median eller trimmed mean?**  
  **Median.** Median är robust mot utslag (t.ex. enstaka ord med conf 0 eller -1 som missats) och speglar typisk sidkvalitet bättre än mean.

- **Vilken andel low-confidence-tokens (t.ex. conf < 50) korrelerar med parsing-fel?**  
  Ingen exakt siffra finns i kodbasen än. Som **operativ tröskel**: om `low_conf_fraction` (andelen ord med conf < 50) > **0.25** (25 %), anta att textkvaliteten är dålig och använd den som stöd för att gå till AI/vision.

- **Skall TSV-rader med conf == -1 uteslutas från word confidence?**  
  **Ja.** I Tesseract TSV gäller: `conf == -1` för nivåer 1–4 (page, block, paragraph, line); endast **level 5 (word)** har conf 0–100. Aggregering ska baseras enbart på ordnivå.  
  **Implementation:**  
  - Antingen: bara ta med rader där `level == 5`, eller  
  - Uteslut alla rader där `conf < 0` vid beräkning av sidmedel/median och vid `low_conf_fraction`.  
  Nuvarande kod i `ocr_abstraction.py` skippar rader med tom `text` (nivå 1–4 har ofta tom text), men confidence skickas inte till Token och används inte. När Token får `confidence` måste aggregeringen uttryckligen utesluta `conf == -1` (eller endast inkludera level 5).

### Leverabler (kodrelevanta)

| Beslut | Värde / regel |
|--------|----------------|
| **Primär OCR-confidence-mått** | **median_conf** = median av `conf` över alla ord (exkl. conf < 0). |
| **Sekundärt** | **mean_conf** = medel av conf (exkl. conf < 0). **low_conf_fraction** = andel ord med `0 <= conf < 50`. |
| **Exkludering** | Vid aggregering: endast rader med **conf >= 0** (eller level == 5). Conf == -1 räknas aldrig som ord. |
| **Routing-tröskel** | Om **median_conf < 70** → gå till nästa steg (AI text eller vision, enligt R4). |
| **Low-conf som stöd** | Om **low_conf_fraction > 0.25** → kan användas som extra signal för "dålig textkvalitet" i routing till vision. |

**Rekommendation B (mean vs median):** Se R1. **Median** används för routing (robusthet); **mean** för DPI-retry (känslighet). Kodkommentar: *"Mean is used for DPI retry sensitivity, median for routing robustness."*

**Källreferens:**  
- [Tesseract TSV-format (conf per level)](https://www.tomrochette.com/tesseract-tsv-format) — level 5 = word, conf 0–100; övriga level conf = -1.

---

## R3 — AI Vision Capabilities and Limits

### Frågor besvarade

- **Vilken AI-leverantör/modell används för vision?**  
  Kodbasen har idag **OpenAI** och **Anthropic (Claude)** som providers; båda har vision-kapabilitet.  
  - **OpenAI:** t.ex. `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo` med vision.  
  - **Anthropic:** t.ex. `claude-3-5-sonnet`, `claude-3-opus` med bild-input.  
  Vision ska implementeras genom samma provider-abstraktion som idag (openai/claude), med ny metod för bild-input.

- **Stödda format (PNG/JPEG)? Max upplösning/filstorlek? Flera bilder per request?**  
  - **OpenAI:** PNG, JPEG; filstorlek max **20 MB**; mycket stora bilder kan trigga token-gränser.  
  - **Claude API:** JPEG, PNG, GIF, WebP; max **8000 px** per dimension (enstaka bild); vid flera bilder lägre gräns (t.ex. 2000 px).  
  För att vara kompatibel med båda och hålla kostnad och latens nere: begränsa till **en bild per request**, **max 4096 px** på längsta sidan, **PNG eller JPEG**, **max filstorlek 20 MB**.

- **Kostnad mot text-only?**  
  Vision förbrukar betydligt fler tokens (bilder räknas som många tokens). Vision ska därför användas **endast när** text-only inte bedöms tillräcklig (enligt R4).

### Leverabler (kodrelevanta)

| Beslut | Värde / regel |
|--------|----------------|
| **Bildformat** | **PNG eller JPEG**. Ingen GIF/WebP krävs i första implementationen. |
| **Max upplösning** | **4096 px** på längsta sidan. Skala ned större renderade sidor innan API-anrop. |
| **Max filstorlek** | **20 MB** (överens med OpenAI; inom Claude’s gräns). |
| **Bilder per anrop** | **1 bild per request** (en sida = en bild). |
| **När vision är tillåten** | När routing enligt R4 bestämmer "AI vision" (både pdfplumber- och OCR-textkvalitet under tröskel). |
| **När vision är förbjuden** | Om konfiguration stänger av vision; eller om bilden efter skalning ändå överstiger max upplösning/storlek (fall tillbaka till AI text-only och flagga). |

**Källreferenser:**  
- [OpenAI — Images and vision](https://platform.openai.com/docs/guides/vision)  
- [Anthropic — Vision](https://docs.anthropic.com/en/docs/build-with-claude/vision)

---

## R4 — AI Routing Rules (Text-only vs Vision)

### Frågor besvarade

- **När räcker text-only AI trots låg parser-confidence?**  
  När **textkvaliteten** (pdf_text_quality eller ocr_text_quality) är **≥** en tröskel (t.ex. **0.5**), dvs. texten är tillräckligt ren och läsbar för att AI ska kunna tolka den. Då använd **AI text-only** även om extraktionsconfidence < 0.95.

- **När måste vision användas?**  
  När **både** pdf_text_quality **och** ocr_text_quality är **<** tröskel (t.ex. **0.5**), eller när OCR inte körts men pdf_text_quality < tröskel. Då är risken hög att AI missförstår av text alone → **AI vision** med sidbild.

- **Ska AI retryas i vision-läge om text-only AI failar schema-validering?**  
  **Ja, med begränsning.** Om text-only returnerar ogiltig JSON/schema: **max 1 retry** med strängare instruktion. Om retry fortfarande failar **eller** om textkvaliteten redan var låg: gå till **vision** (om tillåtet enligt R3) och skicka sidbild + text; max 1 retry även för vision.

### Leverabler (kodrelevanta)

**Routing-tabell (per sida):**

| # | Villkor | Åtgärd |
|---|--------|--------|
| 1 | pdfplumber körbar **och** critical_fields_conf ≥ 0.95 **och** pdf_text_quality ≥ text_quality_threshold | **Acceptera** pdfplumber. |
| 2 | Ej 1 **och** OCR körbar **och** critical_fields_conf ≥ 0.95 **och** ocr_quality ≥ threshold (t.ex. median_conf ≥ 70, ocr_text_quality ≥ 0.5) | **Acceptera** OCR. |
| 3 | Ej 1–2 **och** bästa tillgängliga text_quality ≥ text_quality_threshold (t.ex. 0.5) | **AI text-only.** Max 1 retry vid ogiltig JSON. |
| 4 | Ej 1–3 **eller** (AI text-only gjordes **och** retry failade **och** text_quality < tröskel) | **AI vision** (om tillåtet). Max 1 retry vid ogiltig JSON. |
| 5 | Vision ej tillåten / ej tillgänglig | Behåll AI text-only resultat eller flagga som REVIEW. |

**Tröskelkonstanter (rekommenderade startvärden):**

- `text_quality_threshold = 0.5` — under detta anses text "för dålig" för text-only; över detta tillåts text-only AI.
- `ocr_median_conf_threshold = 70` — under detta betraktas OCR som otillförlitlig för att acceptera direkt (se R2).
- `critical_fields_conf_threshold = 0.95` — oförändrat; redan beslut i projektet.

**Retry-regler:**

- **AI text-only:** Vid ogiltig JSON/schema → **1 retry** med tydlig instruktion om strikt JSON och schema. Om retry också misslyckas **och** text_quality < text_quality_threshold → gå till **vision** (steg 4).
- **AI vision:** Vid ogiltig JSON/schema → **1 retry** med strängare schema-instruktion. Efter det, ingen ytterligare vision-retry; flagga som REVIEW vid behov.

---

## Sammanfattning: konstanter för implementation

```text
# R1
BASELINE_DPI = 300
RETRY_DPI = 400
OCR_MEAN_CONF_RETRY_THRESHOLD = 55   # Retry at 400 DPI only if mean_conf < this
MAX_DPI_RETRIES_PER_PAGE = 1

# R2
OCR_EXCLUDE_CONF_BELOW = 0            # Exclude conf == -1 (and any < 0) from aggregation
OCR_MEDIAN_CONF_ROUTING_THRESHOLD = 70   # Below → go to AI
OCR_LOW_CONF_FRACTION_THRESHOLD = 0.25   # Fraction of words with conf < 50; above → poor quality signal

# R3
VISION_MAX_PIXELS_LONGEST_SIDE = 4096
VISION_MAX_FILE_BYTES = 20 * 1024 * 1024   # 20 MB
VISION_ALLOWED_FORMATS = ("png", "jpeg")

# R4
TEXT_QUALITY_THRESHOLD = 0.5          # Below → prefer vision over text-only AI
CRITICAL_FIELDS_CONF_THRESHOLD = 0.95 # Existing
AI_JSON_RETRY_COUNT = 1
```

**Implementation-rekommendationer (ej blockerande):**

- **Rekommendation A — `vision_reason` i run_summary:** När `method_used == "ai_vision"`, skriv även `vision_reason`: lista med de tröskelvillkor som drev valet, t.ex. `["pdf_text_quality < 0.5", "ocr_median_conf < 70"]`. Viktigt för debugging, användarstöd och threshold-justering.
- **Rekommendation B — mean vs median i kod:** R1 använder **mean_conf** (DPI-retry), R2 **median_conf** (routing). Lägg kodkommentar: *"Mean is used for DPI retry sensitivity, median for routing robustness."* för att undvika framtida förvirring.

---

**Nästa steg:** Använd dessa värden i `14-CONTEXT.md` och i planeringsdokument (14-01 …). Justering av trösklar efter benchmark på fakturakorpus kan göras i senare iteration; detta ger ett stabilt utgångsläge för implementation.
