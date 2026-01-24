# Stack Research

**Domain:** Invoice parsing with AI integration, confidence scoring improvements, and learning systems
**Researched:** 2026-01-24
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.11+ | Core language | Already established, excellent ML/AI ecosystem |
| PySide6 | 6.6.0+ | Desktop GUI | Already in use, native PDF rendering support |
| SQLite | 3.x | Learning database | Lightweight, embedded, perfect for local learning data |
| OpenAI API / Anthropic Claude API | Latest | AI integration | Industry standard for document understanding, structured outputs |
| scikit-learn | 1.3+ | Confidence scoring improvements | Feature engineering, regression models for confidence prediction |
| pandas | 2.0+ | Data analysis | Already in use, essential for learning data analysis |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| openai | 1.0+ | OpenAI API client | When using OpenAI for AI fallback |
| anthropic | 0.7+ | Claude API client | When using Claude for AI fallback |
| scikit-learn | 1.3+ | ML models for confidence | For building confidence prediction models |
| numpy | 1.24+ | Numerical operations | Required by scikit-learn, already in use |
| sqlalchemy | 2.0+ | ORM for learning database | Optional: easier database management |
| pydantic | 2.0+ | Data validation | Already in use, for AI request/response models |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest | Testing | Already in use |
| black | Code formatting | Already in use |
| mypy | Type checking | Already in use |

## Installation

```bash
# AI integration
pip install openai>=1.0.0  # or anthropic>=0.7.0

# Machine learning for confidence scoring
pip install scikit-learn>=1.3.0

# Database for learning (SQLite is built-in, but SQLAlchemy optional)
pip install sqlalchemy>=2.0.0  # Optional: easier ORM

# Already installed:
# - pandas>=2.0.0
# - numpy (dependency)
# - pydantic>=2.0.0
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| OpenAI API | Anthropic Claude API | Claude often better for structured outputs, longer context |
| OpenAI API | Local LLM (Llama, Mistral) | If privacy-critical, but requires GPU and setup complexity |
| SQLite | PostgreSQL | If multi-user or cloud deployment needed |
| SQLite | JSON files | For MVP, but SQLite better for queries and performance |
| scikit-learn | TensorFlow/PyTorch | Overkill for confidence scoring, scikit-learn sufficient |
| scikit-learn | Custom heuristics only | ML can improve beyond heuristics, worth the complexity |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Heavy ML frameworks (TensorFlow/PyTorch) | Overkill for confidence scoring, adds complexity | scikit-learn (simpler, sufficient) |
| MongoDB/NoSQL | Overkill for structured learning data | SQLite (simpler, sufficient) |
| Real-time AI inference | Too expensive, not needed for batch processing | Batch AI calls when confidence < 0.95 |
| Cloud databases | Adds dependency, not needed for desktop app | SQLite (local, embedded) |
| Multiple AI providers simultaneously | Adds complexity, choose one | One primary (OpenAI or Claude) |

## Stack Patterns by Variant

**If using OpenAI:**
- Use `openai>=1.0.0` with structured outputs
- Use `gpt-4o` or `gpt-4-turbo` for best results
- Because: Good balance of cost and quality

**If using Claude:**
- Use `anthropic>=0.7.0` with structured outputs
- Use `claude-3-5-sonnet` or `claude-3-opus`
- Because: Often better structured outputs, longer context windows

**If privacy-critical:**
- Use local LLM (Llama 3, Mistral) via `llama-cpp-python`
- Requires GPU setup and model management
- Because: No data leaves local machine

**If MVP/quick prototype:**
- Start with SQLite + JSON files for learning data
- Upgrade to SQLAlchemy later if needed
- Because: Faster to implement, can refactor later

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Python 3.11+ | scikit-learn 1.3+ | Required for modern ML features |
| pandas 2.0+ | numpy 1.24+ | pandas depends on numpy |
| openai 1.0+ | pydantic 2.0+ | For structured outputs validation |
| PySide6 6.6+ | Python 3.11+ | Qt6 requires Python 3.11+ |

## Sources

- OpenAI API documentation — Structured outputs, function calling
- Anthropic Claude API documentation — Structured outputs, document understanding
- scikit-learn documentation — Confidence scoring, feature engineering
- SQLite documentation — Embedded database patterns
- Existing codebase — Already uses pandas, pydantic, PySide6

---
*Stack research for: Invoice parsing with AI and learning systems*
*Researched: 2026-01-24*
