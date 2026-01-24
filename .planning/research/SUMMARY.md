# Project Research Summary

**Project:** Invoice Parser App v2.0
**Domain:** Invoice parsing with confidence scoring, manual validation, learning systems, and AI integration
**Researched:** 2026-01-24
**Confidence:** HIGH

## Executive Summary

v2.0 fokuserar på att förbättra totalsumma-confidence, lägga till manuell validering med inlärning, och integrera AI som fallback. Research visar att experter bygger sådana system med en **fallback-kedja** (heuristics → AI när confidence låg), **feedback-loopar** för inlärning, och **supplier-specific pattern matching**. 

Rekommenderad approach: Förbättra confidence-scoring först (färre REVIEW-status), sedan manuell validering med inlärning, och slutligen AI-integration som fallback. Viktigaste risken är **over-reliance på AI** (dyrt, långsamt) — undvik genom strikt fallback-pattern (AI endast när confidence < 0.95).

## Key Findings

### Recommended Stack

**Core technologies:**
- **Python 3.11+**: Redan etablerat, utmärkt ML/AI-ekosystem
- **SQLite 3.x**: Embedded database för learning data, perfekt för desktop app
- **OpenAI API / Claude API**: Industry standard för document understanding, structured outputs
- **scikit-learn 1.3+**: ML-modeller för confidence prediction, feature engineering
- **PySide6 6.6.0+**: Redan i bruk, native PDF rendering support

**Supporting libraries:**
- `openai>=1.0.0` eller `anthropic>=0.7.0` för AI-integration
- `scikit-learn>=1.3.0` för confidence prediction models
- `sqlalchemy>=2.0.0` (optional) för enklare database management

**Alternatives:**
- Claude API ofta bättre för structured outputs än OpenAI
- Local LLM (Llama, Mistral) om privacy-critical, men kräver GPU
- PostgreSQL om multi-user/cloud, men SQLite räcker för desktop

### Expected Features

**Must have (table stakes):**
- **Manual validation UI** — Användare förväntar sig kunna korrigera när confidence låg
- **Learning from corrections** — Systemet ska förbättras över tid
- **AI fallback (confidence < 0.95)** — Moderna system använder AI som backup
- **Candidate alternatives** — Visa alternativ när osäker
- **Confidence score display** — Redan finns, behöver förbättras

**Should have (competitive):**
- **Supplier-specific learning** — Systemet lär sig varje leverantörs format
- **Confidence prediction model** — ML-modell för att förutsäga confidence
- **Batch learning** — Lär från flera korrigeringar samtidigt
- **AI-powered pattern discovery** — Hitta ovanliga mönster automatiskt

**Defer (v3.0+):**
- **Natural language queries** — Ställa frågor om fakturdata (komplex, låg prioritet)
- **Multi-user learning** — Dela learning mellan användare (privacy concerns)
- **Cloud AI training** — Kontinuerlig AI-förbättring (komplex, dyr)

### Architecture Approach

Systemet byggs med **fallback-kedja** (heuristics → AI), **learning feedback-loop** (korrigeringar → patterns → förbättrad confidence), och **candidate generation** (flera alternativ, användare väljer). Major components: PDF Viewer (clickable), Confidence Scorer (enhanced), AI Fallback (when confidence < 0.95), Learning Database (SQLite), Pattern Matcher (supplier-specific).

**Major components:**
1. **PDF Viewer (Clickable)** — Visa PDF, detektera klick på totalsumma, highlighta kandidater
2. **Confidence Scorer (Enhanced)** — Multi-factor scoring + ML-modell för confidence prediction
3. **AI Fallback** — Aktiveras när confidence < 0.95, förbättrar extraktion
4. **Learning Database** — SQLite-databas för supplier-specific patterns
5. **Pattern Matcher** — Matcha nya fakturor mot lärda mönster

### Critical Pitfalls

1. **Over-reliance on AI** — Använd AI endast när confidence < 0.95, mät användning, sätt budgetar
2. **Learning database bloat** — Pattern consolidation, supplier-specific limits, regelbunden cleanup
3. **Confidence score inflation** — Kalibrera scoring mot faktisk accuracy, validera regelbundet
4. **Manual validation UX friction** — One-click selection, keyboard shortcuts, visual highlighting
5. **AI prompt engineering failure** — Structured outputs, error handling, response validation, fallback chain
6. **Pattern matching false positives** — Supplier-specific matching, high similarity threshold, confidence weighting

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Improved Confidence Scoring

**Rationale:** Core problem (för många REVIEW-status) måste lösas först. Bättre confidence = färre AI-anrop = lägre kostnad och högre hastighet.

**Delivers:** Förbättrad confidence-scoring algoritm, kalibrering mot faktisk accuracy, ML-modell för confidence prediction (optional).

**Addresses:** 
- Table stakes: Confidence score display (förbättrad)
- Differentiator: Confidence prediction model

**Avoids:** 
- Confidence score inflation (kalibrering från start)
- Over-reliance on AI (bättre heuristics = färre AI-anrop)

**Uses:** scikit-learn för ML-modell (optional), befintlig confidence_scoring.py (enhance)

---

### Phase 2: Manual Validation UI

**Rationale:** Användare behöver kunna korrigera när confidence låg. UI måste vara snabb och enkel (one-click).

**Delivers:** Clickable PDF viewer, candidate selector, validation workflow, correction collection.

**Addresses:**
- Table stakes: Manual validation UI, candidate alternatives
- Differentiator: Supplier-specific learning (foundation)

**Uses:** PySide6 QGraphicsView, PDF.js eller PyMuPDF rendering

**Implements:** PDF Viewer component, Candidate Selector component

**Avoids:**
- Manual validation UX friction (UX testing, keyboard shortcuts, visual highlighting)

---

### Phase 3: Learning System

**Rationale:** Systemet måste lära sig från korrigeringar för att förbättras. Kräver database och pattern matching.

**Delivers:** SQLite learning database, correction collector, pattern matcher, supplier-specific learning.

**Addresses:**
- Table stakes: Learning from corrections
- Differentiator: Supplier-specific learning, batch learning

**Uses:** SQLite (embedded), SQLAlchemy (optional), pattern matching algorithms

**Implements:** Learning Database component, Pattern Matcher component

**Avoids:**
- Learning database bloat (cleanup, consolidation från start)
- Pattern matching false positives (supplier isolation, high similarity threshold)

**Enhances:** Phase 1 (Confidence Scoring) — learned patterns förbättrar confidence

---

### Phase 4: AI Integration

**Rationale:** AI som fallback när confidence < 0.95. Förbättrar extraktion för edge cases.

**Delivers:** AI API client, fallback integration, structured outputs, error handling.

**Addresses:**
- Table stakes: AI fallback when confidence low
- Differentiator: AI-powered pattern discovery (foundation)

**Uses:** OpenAI API eller Claude API, structured outputs (Pydantic)

**Implements:** AI Fallback component

**Avoids:**
- Over-reliance on AI (strikt fallback pattern, confidence < 0.95 only)
- AI prompt engineering failure (structured outputs, validation, error handling)

**Enhances:** Phase 1 (Confidence Scoring) — AI kan boosta confidence

---

### Phase 5: AI Data Analysis (Optional)

**Rationale:** Natural language queries och dataanalys. Komplex, kan deferras till v3.0 om inte kritisk.

**Delivers:** RAG system över processade fakturor, natural language query interface.

**Addresses:**
- Future: Natural language queries

**Uses:** AI API (OpenAI/Claude), vector database (optional), RAG patterns

---

### Phase Ordering Rationale

- **Phase 1 → Phase 2:** Bättre confidence = färre korrigeringar behövs, men UI behövs för att samla in korrigeringar
- **Phase 2 → Phase 3:** Learning system behöver korrigeringar från Phase 2 som input
- **Phase 3 → Phase 4:** Learning system kan förbättra confidence, vilket minskar AI-behov, men AI kan också boosta confidence
- **Phase 1 & 4 kan delvis parallellt:** Confidence scoring och AI-integration är relativt oberoende
- **Phase 5 är optional:** Kan deferras till v3.0 om inte kritisk

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (AI Integration):** Prompt engineering, structured outputs, error handling patterns — behöver API-specifik research
- **Phase 3 (Learning System):** Pattern matching algorithms, similarity thresholds — behöver algoritm-research

Phases with standard patterns (skip research-phase):
- **Phase 1 (Confidence Scoring):** scikit-learn patterns väl dokumenterade
- **Phase 2 (Manual Validation UI):** PySide6 PDF viewer patterns väl dokumenterade

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Etablerade teknologier, väl dokumenterade |
| Features | HIGH | Tydliga user needs, väl definierade features |
| Architecture | HIGH | Standard patterns, väl kända mönster |
| Pitfalls | HIGH | Kända problem i liknande system, väl dokumenterade |

**Overall confidence:** HIGH

### Gaps to Address

- **AI prompt engineering:** Specifika prompts behöver testas under Phase 4 planning
- **Pattern matching algorithms:** Optimal similarity threshold behöver valideras under Phase 3 planning
- **Confidence calibration:** Optimal calibration curve behöver valideras mot faktisk data under Phase 1

## Sources

### Primary (HIGH confidence)
- Existing codebase — Current confidence scoring implementation, pipeline architecture
- AI API documentation — OpenAI/Claude structured outputs, best practices
- scikit-learn documentation — Confidence scoring, ML patterns
- PySide6 documentation — PDF viewer implementation
- SQLite best practices — Embedded database patterns

### Secondary (MEDIUM confidence)
- Learning system patterns — Feedback loops, pattern matching (community consensus)
- UX research — Manual validation best practices (industry standards)

### Tertiary (LOW confidence)
- Supplier-specific learning patterns — Specifika algoritmer behöver valideras (inference från generella patterns)

---
*Research completed: 2026-01-24*
*Ready for roadmap: yes*
