# Feature Research

**Domain:** Invoice parsing with confidence scoring, manual validation, learning systems, and AI integration
**Researched:** 2026-01-24
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Manual validation UI | When confidence is low, users expect to correct it | MEDIUM | PDF viewer with clickable totals, candidate selection |
| Learning from corrections | System should improve over time | MEDIUM | Database of corrections, pattern matching |
| AI fallback when confidence low | Modern systems use AI as backup | HIGH | API integration, prompt engineering, error handling |
| Confidence score display | Users need to see why system is uncertain | LOW | Already exists, just needs improvement |
| Candidate alternatives | When uncertain, show options | MEDIUM | Extract multiple candidates, present in UI |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Learning database per supplier | System learns each supplier's format | MEDIUM | Supplier-specific patterns improve accuracy |
| AI-powered pattern discovery | Find unusual patterns automatically | HIGH | AI analyzes edge cases, suggests improvements |
| Natural language queries | Ask questions about invoice data | HIGH | RAG system over processed invoices |
| Confidence prediction model | ML model predicts confidence before extraction | MEDIUM | Train on historical data, predict success |
| Batch learning | Learn from multiple corrections at once | LOW | Aggregate corrections, update patterns |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Auto-correct everything | Users want zero manual work | Breaks hard gates, reduces trust | Manual validation with learning |
| Real-time AI for all invoices | Better accuracy | Expensive, slow, unnecessary for high-confidence | AI only when confidence < 0.95 |
| Override hard gates | Users want to force OK status | Breaks core value (100% accuracy guarantee) | Keep hard gates, improve confidence instead |
| Cloud-based learning | Share learning across users | Privacy concerns, data ownership | Local learning database per user |
| Continuous AI training | Improve AI over time | Complex, expensive, overkill | Use AI as fallback, not primary |

## Feature Dependencies

```
[Manual Validation UI]
    └──requires──> [PDF Viewer with Clickable Areas]
                       └──requires──> [Candidate Extraction]
                                          └──requires──> [Multiple Candidate Scoring]

[Learning System]
    └──requires──> [Manual Validation UI] (to collect corrections)
    └──requires──> [Database] (to store learning data)
    └──enhances──> [Confidence Scoring] (uses learned patterns)

[AI Integration]
    └──requires──> [Confidence Scoring] (to know when to activate)
    └──enhances──> [Total Amount Extraction] (when confidence < 0.95)
    └──enhances──> [Confidence Scoring] (AI can boost confidence)

[Improved Confidence Scoring]
    └──enhances──> [Status Assignment] (fewer REVIEW status)
    └──enhanced by──> [Learning System] (learned patterns)
    └──enhanced by──> [AI Integration] (AI validation)

[Natural Language Queries]
    └──requires──> [Processed Invoice Database]
    └──requires──> [AI Integration] (for query understanding)
```

### Dependency Notes

- **[Manual Validation UI] requires [PDF Viewer with Clickable Areas]:** Users need to see PDF and click on totals
- **[Learning System] requires [Manual Validation UI]:** Learning needs user corrections as input
- **[Learning System] enhances [Confidence Scoring]:** Learned patterns improve future confidence
- **[AI Integration] requires [Confidence Scoring]:** AI only activates when confidence is low
- **[AI Integration] enhances [Confidence Scoring]:** AI validation can boost confidence scores

## MVP Definition

### Launch With (v2.0)

Minimum viable product — what's needed to validate the concept.

- [x] **Improved confidence scoring** — Core problem: too many REVIEW status
- [ ] **Manual validation UI** — Essential for user to correct low-confidence cases
- [ ] **Learning database** — System must learn from corrections to improve
- [ ] **AI fallback (confidence < 0.95)** — AI helps when heuristics fail
- [ ] **Candidate selection** — Users need alternatives to choose from

### Add After Validation (v2.1)

Features to add once core is working.

- [ ] **Supplier-specific learning** — Learn patterns per supplier
- [ ] **Confidence prediction model** — ML model predicts confidence
- [ ] **Batch learning** — Learn from multiple corrections at once
- [ ] **AI pattern discovery** — AI finds unusual patterns automatically

### Future Consideration (v3.0+)

Features to defer until product-market fit is established.

- [ ] **Natural language queries** — Ask questions about invoice data
- [ ] **Multi-user learning** — Share learning across users (privacy concerns)
- [ ] **Cloud AI training** — Continuous AI improvement (complexity, cost)
- [ ] **Real-time AI for all** — AI for every invoice (expensive, slow)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Improved confidence scoring | HIGH | MEDIUM | P1 |
| Manual validation UI | HIGH | MEDIUM | P1 |
| Learning database | HIGH | MEDIUM | P1 |
| AI fallback (confidence < 0.95) | HIGH | HIGH | P1 |
| Candidate selection | HIGH | LOW | P1 |
| Supplier-specific learning | MEDIUM | MEDIUM | P2 |
| Confidence prediction model | MEDIUM | HIGH | P2 |
| Natural language queries | LOW | HIGH | P3 |
| Batch learning | MEDIUM | LOW | P2 |

**Priority key:**
- P1: Must have for v2.0 launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Competitor A (Generic OCR) | Competitor B (AI Invoice) | Our Approach |
|---------|---------------------------|--------------------------|--------------|
| Confidence scoring | Basic (0/1) | ML-based | Multi-factor heuristics + ML + AI |
| Manual correction | Text editor | Dropdown | Clickable PDF with candidates |
| Learning | None | Cloud-based | Local database, supplier-specific |
| AI integration | None | Always-on | Fallback only (confidence < 0.95) |
| Hard gates | None | Soft | Hard gates (100% accuracy guarantee) |

## Sources

- Existing codebase analysis — Current confidence scoring implementation
- User feedback — Too many REVIEW status due to low confidence
- AI API documentation — OpenAI/Claude structured outputs
- Learning system patterns — Feedback loops, pattern matching
- Competitor analysis — Generic OCR tools, AI invoice parsers

---
*Feature research for: Invoice parsing with confidence, learning, and AI*
*Researched: 2026-01-24*
