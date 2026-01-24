# Architecture Research

**Domain:** Invoice parsing with confidence scoring, manual validation, learning systems, and AI integration
**Researched:** 2026-01-24
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer (PySide6)                    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PDF Viewer   │  │ Validation   │  │ Candidate   │      │
│  │ (Clickable)  │  │ UI           │  │ Selector    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘      │
│         │                  │                 │              │
├─────────┴──────────────────┴─────────────────┴──────────────┤
│                    Pipeline Layer                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Total        │  ─→│ Confidence  │  ─→│ AI Fallback │      │
│  │ Extractor    │     │ Scorer     │     │ (if < 0.95)│      │
│  └──────────────┘  ┌──┴────────────┴──┐ └──────────────┘      │
│                    │  Candidate       │                       │
│                    │  Generator       │                       │
│                    └──────────────────┘                       │
├─────────────────────────────────────────────────────────────┤
│                    Learning Layer                            │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Correction   │  │ Pattern      │  │ Supplier    │      │
│  │ Collector    │  →│ Matcher      │  →│ Database    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                    Data Layer                                │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ Learning DB  │  │ Invoice      │                        │
│  │ (SQLite)     │  │ Cache        │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| PDF Viewer (Clickable) | Display PDF, detect clicks on totals, highlight candidates | PySide6 QGraphicsView with PDF.js or PyMuPDF rendering |
| Candidate Selector | Show multiple total candidates, let user choose | PySide6 dialog with list of candidates + confidence |
| Confidence Scorer | Calculate confidence for total extraction | Multi-factor scoring (position, keywords, math validation) + ML model |
| AI Fallback | Call AI when confidence < 0.95 | OpenAI/Claude API with structured output schema |
| Correction Collector | Save user corrections to learning database | SQLite insert with supplier, pattern, correction |
| Pattern Matcher | Match new invoices to learned patterns | SQLite queries, similarity matching |
| Supplier Database | Store supplier-specific patterns | SQLite table: supplier_name, pattern_hash, correct_total, confidence_boost |
| Learning Engine | Update confidence scoring based on corrections | Background process, pattern analysis, model retraining |

## Recommended Project Structure

```
src/
├── pipeline/              # Existing pipeline
│   ├── footer_extractor.py    # Total extraction (enhance)
│   ├── confidence_scoring.py  # Confidence scoring (enhance)
│   └── ...
├── ai/                    # AI integration (NEW)
│   ├── __init__.py
│   ├── client.py          # AI API client (OpenAI/Claude)
│   ├── schemas.py         # AI request/response models
│   └── fallback.py        # AI fallback when confidence < 0.95
├── learning/              # Learning system (NEW)
│   ├── __init__.py
│   ├── database.py        # SQLite learning database
│   ├── collector.py       # Collect user corrections
│   ├── matcher.py         # Match patterns to learned data
│   └── patterns.py        # Pattern extraction and matching
├── ui/                    # Existing UI
│   ├── views/
│   │   ├── main_window.py     # Enhance with validation UI
│   │   └── pdf_viewer.py      # NEW: Clickable PDF viewer
│   └── ...
└── models/                # Existing models
    ├── invoice_header.py      # Enhance with learning metadata
    └── ...
```

### Structure Rationale

- **ai/:** Separates AI integration from pipeline logic, easier to swap providers
- **learning/:** Isolated learning system, can be enabled/disabled, testable
- **ui/views/pdf_viewer.py:** New component for clickable PDF viewing
- **pipeline/confidence_scoring.py:** Enhance existing, don't replace

## Architectural Patterns

### Pattern 1: Fallback Chain

**What:** Try heuristics first, then AI if confidence low
**When to use:** When you have fast heuristics but need AI backup
**Trade-offs:** 
- Pros: Fast for common cases, accurate for edge cases
- Cons: Two code paths to maintain

**Example:**
```python
def extract_total_with_fallback(footer_segment, invoice_lines):
    # Try heuristics first
    total, confidence = extract_total_heuristic(footer_segment, invoice_lines)
    
    if confidence < 0.95:
        # Fallback to AI
        total, confidence = extract_total_ai(footer_segment, invoice_lines)
    
    return total, confidence
```

### Pattern 2: Learning Feedback Loop

**What:** Collect corrections, learn patterns, improve future extractions
**When to use:** When user corrections can improve system accuracy
**Trade-offs:**
- Pros: System improves over time, supplier-specific learning
- Cons: Requires database, pattern matching complexity

**Example:**
```python
def process_correction(invoice, user_selected_total):
    # Save correction
    learning_db.save_correction(
        supplier=invoice.supplier_name,
        pattern=extract_pattern(invoice),
        correct_total=user_selected_total
    )
    
    # Update confidence for similar future invoices
    update_confidence_model(pattern, user_selected_total)
```

### Pattern 3: Candidate Generation

**What:** Extract multiple candidates, let user choose
**When to use:** When confidence is low, show alternatives
**Trade-offs:**
- Pros: User can correct, system learns from choice
- Cons: Requires UI, more complex extraction

**Example:**
```python
def extract_total_candidates(footer_segment):
    candidates = []
    # Extract multiple candidates with different strategies
    candidates.append(extract_by_keyword(footer_segment))
    candidates.append(extract_by_position(footer_segment))
    candidates.append(extract_by_format(footer_segment))
    
    # Score and return top candidates
    return sorted(candidates, key=lambda c: c.confidence, reverse=True)[:3]
```

## Data Flow

### Total Extraction Flow

```
[Footer Segment] 
    ↓
[Heuristic Extractor] → [Confidence Scorer] → confidence >= 0.95?
    ↓ (yes)                                    ↓ (no)
[Return Total]                          [AI Fallback] → [Confidence Scorer]
    ↓                                            ↓
[Return Total]                            [Return Total]
```

### Learning Flow

```
[User Correction]
    ↓
[Correction Collector] → [Learning Database]
    ↓
[Pattern Extractor] → [Pattern Matcher]
    ↓
[Confidence Model Update] → [Future Invoices Benefit]
```

### Manual Validation Flow

```
[Low Confidence Total]
    ↓
[Candidate Generator] → [UI: Show Candidates]
    ↓
[User Selects] → [Correction Collector]
    ↓
[Learning Database] → [Pattern Learning]
```

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k invoices/month | SQLite fine, no caching needed |
| 1k-10k invoices/month | Add invoice cache, batch learning updates |
| 10k+ invoices/month | Consider PostgreSQL, async AI calls, learning queue |

### Scaling Priorities

1. **First bottleneck:** Learning database queries — Add indexes on supplier_name, pattern_hash
2. **Second bottleneck:** AI API calls — Batch requests, cache results, rate limiting

## Anti-Patterns

### Anti-Pattern 1: AI for Everything

**What people do:** Call AI for every invoice
**Why it's wrong:** Expensive, slow, unnecessary for high-confidence cases
**Do this instead:** Use AI only when confidence < 0.95 (fallback pattern)

### Anti-Pattern 2: No Learning Feedback

**What people do:** Collect corrections but don't use them
**Why it's wrong:** System never improves, users keep correcting same issues
**Do this instead:** Active learning loop: corrections → patterns → improved confidence

### Anti-Pattern 3: Override Hard Gates

**What people do:** Let users override hard gates to force OK status
**Why it's wrong:** Breaks core value (100% accuracy guarantee)
**Do this instead:** Improve confidence scoring, keep hard gates intact

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| OpenAI API | REST API with structured outputs | Rate limiting, error handling, retry logic |
| Claude API | REST API with structured outputs | Alternative to OpenAI, better structured outputs |
| SQLite | Embedded database | No external service, but included for completeness |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| UI ↔ Pipeline | Direct function calls | UI calls pipeline functions directly |
| Pipeline ↔ AI | API client abstraction | Abstract AI client, swap providers easily |
| Pipeline ↔ Learning | Database interface | Learning system isolated, can be disabled |
| Learning ↔ UI | Event/callback | UI notifies learning system of corrections |

## Sources

- Existing codebase — Current pipeline architecture
- AI API documentation — OpenAI/Claude integration patterns
- Learning system patterns — Feedback loops, pattern matching
- PySide6 documentation — PDF viewer implementation
- SQLite best practices — Embedded database patterns

---
*Architecture research for: Invoice parsing with confidence, learning, and AI*
*Researched: 2026-01-24*
