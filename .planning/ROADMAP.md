# Roadmap: Invoice Parser App

## Overview

v2.1 fokuserar på deterministisk parsing för EDI-liknande fakturor med text-layer, robust tabellsegmentering och valideringsdriven om-extraktion. OCR och AI används bara som fallback, med tydliga regler och debug-artefakter för spårbarhet.

## Milestones

- ✅ **v1.0 MVP** - Phases 1-3 (shipped 2026-01-17)
- ✅ **v2.0 Features + polish** - Phases 5-15 (shipped 2026-01-26)
- ✅ **v2.1 Parsing robustness / EDI** - Phases 16-22 (complete, UAT pending)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-3) - SHIPPED 2026-01-17</summary>

See archived roadmap: `.planning/milestones/v1.0-ROADMAP.md`.

</details>

<details>
<summary>✅ v2.0 Features + polish (Phases 5-15) - SHIPPED 2026-01-26</summary>

See archived roadmap: `.planning/milestones/v2.0-ROADMAP.md`.

</details>

### ✅ v2.1 Parsing robustness / EDI (Complete, UAT pending)

**Milestone Goal:** Deterministisk parsing för EDI‑liknande PDF:er med text‑layer, robust tabellsegmentering och valideringsdriven om‑extraktion.

#### Phase 16: Text-layer routing (OCR-skip)
**Goal**: Text-layer styr parsing per sida; OCR används endast när text-layer inte räcker.
**Depends on**: Phase 15
**Requirements**: OCR-01, OCR-02, OCR-03, OCR-04
**Success Criteria** (what must be TRUE):
  1. Sidor med tillräcklig text-layer körs utan OCR och ger stabilt resultat.
  2. OCR används bara när text-layer saknas eller inte uppfyller tröskeln.
  3. Konfigurerade ankare och `min_text_chars` styr beslutet per sida.
  4. OCR/pdfplumber-jämförelse kraschar inte.
**Plans**: 2 plans

Plans:
- [x] 16-01: Text-layer routing (OCR-skip)

#### Phase 17: AI-policy (fallback only)
**Goal**: AI används endast som sista fallback och aldrig som normalväg för EDI-liknande fakturor.
**Depends on**: Phase 16
**Requirements**: AI-01, AI-02
**Success Criteria** (what must be TRUE):
  1. EDI-liknande fakturor med text-layer parsas deterministiskt utan AI.
  2. AI används bara när deterministiska regler saknas eller mönster är ovanliga.
**Plans**: 2 plans

Plans:
- [x] 17-01: AI-policy (fallback only)
- [x] 17-02: AI-policy gating i compare-path (gap-closure)

#### Phase 18: Fakturaboundaries för multi-page PDFs
**Goal**: Sidor grupperas korrekt per faktura utan att bero på totalsumma.
**Depends on**: Phase 17
**Requirements**: BOUND-01, BOUND-02, BOUND-03
**Success Criteria** (what must be TRUE):
  1. Fler-sidiga fakturor grupperas korrekt via fakturanummer per sida.
  2. Sidnummer används som stöd för att samla sidor per faktura.
  3. Segmentering fungerar utan att vänta på “total found”.
**Plans**: 1 plan

Plans:
- [x] 18-01: Fakturaboundaries (invoice_no grouping)

#### Phase 19: Svensk talnormalisering
**Goal**: Alla belopp parsas konsekvent som Decimal med svensk notation.
**Depends on**: Phase 18
**Requirements**: NUM-01, NUM-02, NUM-03, NUM-04
**Success Criteria** (what must be TRUE):
  1. Alla belopp tolkas som `Decimal` från en gemensam normaliseringsfunktion.
  2. Belopp med mellanslag som tusentalsseparator tolkas korrekt.
  3. Belopp med punkt som tusentalsseparator (endast följt av tre siffror) tolkas korrekt.
  4. Belopp med svensk decimal-komma tolkas korrekt.
**Plans**: 2 plans

Plans:
- [x] 19-01: Svensk talnormalisering (Decimal)
- [x] 19-02: Decimal ut i pipeline (gap-closure)

#### Phase 20: Tabellsegment & kolumnregler
**Goal**: Tabellblock och kolumnlogik parsas deterministiskt från text-layer.
**Depends on**: Phase 19
**Requirements**: TABLE-01, TABLE-02, TABLE-03, TABLE-04
**Success Criteria** (what must be TRUE):
  1. Tabellblocket lokaliseras korrekt mellan rubrikrad och slutrad.
  2. Rader parsas rad-för-rad inom tabellblocket.
  3. Nettobelopp identifieras som sista valuta-tal efter moms% enligt reglerna.
  4. Alternativ moms%+belopp-regex används för att undvika felkolumn.
**Known Limitations**: 
  - ⚠️ CRITICAL: Single VAT rate only (25%) - must address in Phase 21/22
  - See: `.planning/phases/20-tabellsegment-kolumnregler/20-LIMITATIONS.md`
**Plans**: 1 plan

Plans:
- [x] 20-01: Tabellsegment & kolumnregler

#### Phase 21: Multi-line items
**Goal**: Fortsättningsrader blir del av item-beskrivning utan att skapa falska nya rader.
**Depends on**: Phase 20
**Requirements**: LINE-01, LINE-02
**Success Criteria** (what must be TRUE):
  1. Rader utan moms% + nettobelopp läggs till i föregående beskrivning.
  2. Nytt item startar när start-mönster eller individnr/konto/startdatum matchar.
**Research**: Complete (2026-01-26) - Adaptive Y-threshold, start-pattern detection, X-alignment tolerance
**Plans**: 1 plan

Plans:
- [x] 21-01: Multi-line items (wrap detection enhancement)

#### Phase 22: Valideringsdriven om-extraktion (mode B)
**Goal**: Validering styr om-extraktion och sparar debug vid mismatch.
**Depends on**: Phase 21
**Requirements**: VAL-01, VAL-02, VAL-03, VAL-04, VAL-05
**Success Criteria** (what must be TRUE):
  1. Nettosumma och moms kontrolleras mot fakturans totalsummor inom ±0,50 SEK.
  2. Vid valideringsfel körs table-parser mode B enligt konfigurerat läge.
  3. Vid kvarstående mismatch markeras REVIEW och debug-artefakter sparas.
**Research**: Complete (2026-01-26) - Gap-based column detection, hybrid position+content, token-to-column mapping
**Plans**: 1 plan

Plans:
- [x] 22-01: Valideringsdriven om-extraktion (mode B)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 16. Text-layer routing (OCR-skip) | v2.1 | 1/1 | Complete | 2026-01-26 |
| 17. AI-policy (fallback only) | v2.1 | 2/2 | Complete | 2026-01-26 |
| 18. Fakturaboundaries | v2.1 | 1/1 | Complete | 2026-01-26 |
| 19. Svensk talnormalisering | v2.1 | 2/2 | Complete | 2026-01-26 |
| 20. Tabellsegment & kolumnregler | v2.1 | 1/1 | Complete | 2026-01-26 |
| 21. Multi-line items | v2.1 | 1/1 | Complete | 2026-01-26 |
| 22. Valideringsdriven om-extraktion | v2.1 | 1/1 | Complete | 2026-01-26 |
