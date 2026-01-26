# Requirements: Invoice Parser App (v2.1)

**Defined:** 2026-01-26  
**Core Value:** 100% korrekt på fakturanummer och totalsumma, eller tydlig REVIEW-status. Allt som systemet exporterar som OK är garanterat korrekt. Osäkra fall går alltid till REVIEW.

**Scope:** v2.1 Parsing robustness / EDI  
**Goal:** Deterministisk parsing för EDI‑liknande PDF:er med text‑layer, robust tabellsegmentering och valideringsdriven om‑extraktion. OCR och AI används endast som fallback.

---

## v2.1 Requirements

### Text‑layer routing (OCR‑skip)

- [ ] **OCR-01**: Systemet detekterar text‑layer per sida och kör inte OCR om text‑layer är “tillräcklig”.
- [ ] **OCR-02**: “Tillräcklig text” är **konfigurerbar** och består av:
  - `min_text_chars` (default 500), **och**
  - ankare som matchar `"Faktura "` (inkl. tab/regex), **och**
  - minst ett extra ankare (t.ex. `"Sida 1/2"` eller `"Ramirent"`).
- [ ] **OCR-03**: OCR används endast som fallback för sidor utan tillräcklig text‑layer.
- [ ] **OCR-04**: OCR/pdfplumber‑jämförelse kraschar inte (fix av `KeyError: 4`).

### Tabellsegment + kolumnregler

- [ ] **TABLE-01**: Systemet lokaliserar tabellblocket mellan rubrikraden (t.ex. “Artikelnr/ … Nettobelopp”) och slutraden “Nettobelopp exkl. moms:”.
- [ ] **TABLE-02**: Rader parsas inom tabellblocket rad‑för‑rad.
- [ ] **TABLE-03**: Nettobelopp identifieras som **sista valuta‑talet** efter moms% (25.00) på raden.
- [ ] **TABLE-04**: Alternativ regex stöds för moms% + belopp, t.ex. `\\s25\\.00\\s<belopp>`, för att undvika felkolumn (t.ex. 35.1/38.9).

### Multi‑line items

- [ ] **LINE-01**: Om en rad saknar moms% + nettobelopp behandlas den som fortsättning på föregående item‑beskrivning.
- [ ] **LINE-02**: Nytt item startar när raden matchar start‑mönster (t.ex. `^\\w{3,}\\d+` eller `^\\d{5,}`) eller innehåller individnr/konto/startdatum‑mönster.

### Svensk talnormalisering

- [ ] **NUM-01**: All valutaparssning använder **en gemensam normaliseringsfunktion** som returnerar `Decimal`.
- [ ] **NUM-02**: Normalisering tar bort mellanslag som tusentalsseparator.
- [ ] **NUM-03**: Normalisering tar bort punkt som tusentalsseparator **endast** när den följs av tre siffror.
- [ ] **NUM-04**: Normalisering byter `,` → `.` innan `Decimal`‑parsning.

### Valideringsdriven om‑extraktion

- [ ] **VAL-01**: `sum(line_items.netto)` matchar “Nettobelopp exkl. moms” inom ±0,50 SEK.
- [ ] **VAL-02**: `netto + moms` matchar “Att betala” inom ±0,50 SEK.
- [ ] **VAL-03**: Om VAL‑01 fallerar körs **table‑parser mode B** (position/kolumn‑baserad andra pass).
- [ ] **VAL-04**: Om mismatch kvarstår → status REVIEW och **debug‑artefakter** sparas (tabellblockets råtext + tolkade rader).
- [ ] **VAL-05**: `table_parser_mode` är konfigurerbart: `auto|text|pos` (auto kör A och fallback till B).

### Fakturaboundaries

- [ ] **BOUND-01**: Fakturor segmenteras genom att läsa fakturanummer per sida och groupby `invoice_no`.
- [ ] **BOUND-02**: Sidnummer (“Sida 1/2”, “Sida 2/2”) används som hjälp för att samla sidor per faktura.
- [ ] **BOUND-03**: Segmentering ska inte bero på “total found”.

### AI‑policy

- [ ] **AI-01**: AI används **endast** som fallback för fält utan mönster eller ovanliga layouter.
- [ ] **AI-02**: För EDI‑liknande fakturor med text‑layer ska parsing vara deterministisk och AI inte vara normalväg.

---

## Out of Scope (v2.1)

- Web‑UI (desktop‑GUI gäller)
- Realtidsflöde (batch)
- Automatisk korrigering utan REVIEW‑status
- AI som standardväg när deterministiska regler fungerar

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| OCR-01 | Phase 16: Text-layer routing (OCR-skip) | Pending |
| OCR-02 | Phase 16: Text-layer routing (OCR-skip) | Pending |
| OCR-03 | Phase 16: Text-layer routing (OCR-skip) | Pending |
| OCR-04 | Phase 16: Text-layer routing (OCR-skip) | Pending |
| AI-01  | Phase 17: AI-policy (fallback only) | Pending |
| AI-02  | Phase 17: AI-policy (fallback only) | Pending |
| BOUND-01 | Phase 18: Fakturaboundaries | Pending |
| BOUND-02 | Phase 18: Fakturaboundaries | Pending |
| BOUND-03 | Phase 18: Fakturaboundaries | Pending |
| NUM-01 | Phase 19: Svensk talnormalisering | Pending |
| NUM-02 | Phase 19: Svensk talnormalisering | Pending |
| NUM-03 | Phase 19: Svensk talnormalisering | Pending |
| NUM-04 | Phase 19: Svensk talnormalisering | Pending |
| TABLE-01 | Phase 20: Tabellsegment & kolumnregler | Pending |
| TABLE-02 | Phase 20: Tabellsegment & kolumnregler | Pending |
| TABLE-03 | Phase 20: Tabellsegment & kolumnregler | Pending |
| TABLE-04 | Phase 20: Tabellsegment & kolumnregler | Pending |
| LINE-01 | Phase 21: Multi-line items | Pending |
| LINE-02 | Phase 21: Multi-line items | Pending |
| VAL-01 | Phase 22: Valideringsdriven om-extraktion | Pending |
| VAL-02 | Phase 22: Valideringsdriven om-extraktion | Pending |
| VAL-03 | Phase 22: Valideringsdriven om-extraktion | Pending |
| VAL-04 | Phase 22: Valideringsdriven om-extraktion | Pending |
| VAL-05 | Phase 22: Valideringsdriven om-extraktion | Pending |

---
*Requirements defined: 2026-01-26*
