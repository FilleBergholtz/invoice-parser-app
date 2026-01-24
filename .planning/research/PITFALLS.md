# Pitfalls Research

**Domain:** Invoice parsing with confidence scoring, manual validation, learning systems, and AI integration
**Researched:** 2026-01-24
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Over-Reliance on AI

**What goes wrong:**
System calls AI for every invoice, becomes slow and expensive. Users wait for AI responses even when heuristics work fine.

**Why it happens:**
Developers think "AI is better, use it always" without considering cost/performance trade-offs.

**How to avoid:**
Strict fallback pattern: AI only when confidence < 0.95. Measure AI usage, set budgets, monitor costs.

**Warning signs:**
- AI called for >50% of invoices
- Processing time increases significantly
- API costs growing unexpectedly
- Users complaining about slowness

**Phase to address:**
Phase 1 (Improved Confidence Scoring) — Better heuristics reduce AI need

---

### Pitfall 2: Learning Database Bloat

**What goes wrong:**
Learning database grows unbounded, queries slow down, patterns become outdated or conflicting.

**Why it happens:**
No cleanup strategy, storing every correction without pattern consolidation or expiration.

**How to avoid:**
- Pattern consolidation: Merge similar patterns
- Supplier-specific limits: Max patterns per supplier
- Pattern expiration: Remove old patterns if not used
- Database maintenance: Regular cleanup, indexing

**Warning signs:**
- Database size growing linearly
- Query performance degrading
- Conflicting patterns for same supplier
- Learning not improving accuracy

**Phase to address:**
Phase 3 (Learning System) — Build cleanup and consolidation from start

---

### Pitfall 3: Confidence Score Inflation

**What goes wrong:**
Confidence scores become inflated (always high) or deflated (always low), losing meaning. Users can't trust scores.

**Why it happens:**
Scoring algorithm not calibrated, or learning system over-corrects, or AI always returns high confidence.

**How to avoid:**
- Calibration: Map confidence to actual accuracy (e.g., 0.95 = 95% correct in validation)
- Validation: Track actual accuracy vs. predicted confidence
- Regular recalibration: Adjust scoring based on real performance
- Hard gates remain: Don't lower threshold, improve scoring instead

**Warning signs:**
- All confidences > 0.9 (inflated)
- All confidences < 0.5 (deflated)
- Confidence doesn't correlate with actual accuracy
- Users ignore confidence scores

**Phase to address:**
Phase 1 (Improved Confidence Scoring) — Calibration from start

---

### Pitfall 4: Manual Validation UX Friction

**What goes wrong:**
Manual validation is too slow or confusing. Users skip it, or it takes too long, defeating the purpose.

**Why it happens:**
UI not optimized for speed, too many clicks, unclear instructions, candidates not visible.

**How to avoid:**
- One-click selection: Show candidates clearly, single click to select
- Keyboard shortcuts: Arrow keys to navigate, Enter to confirm
- Visual highlighting: Highlight candidates in PDF
- Default selection: Pre-select most likely candidate
- Batch mode: Validate multiple invoices at once

**Warning signs:**
- Users skip manual validation
- Average validation time > 30 seconds
- Low correction rate (users not using feature)
- Support requests about "how to validate"

**Phase to address:**
Phase 2 (Manual Validation UI) — UX testing and optimization

---

### Pitfall 5: AI Prompt Engineering Failure

**What goes wrong:**
AI returns wrong results, or inconsistent formats, or times out. System breaks when AI fails.

**Why it happens:**
Poor prompt design, no error handling, no validation of AI responses, no fallback when AI fails.

**How to avoid:**
- Structured outputs: Use schema validation (Pydantic)
- Error handling: Retry logic, timeout handling, graceful degradation
- Response validation: Check AI output before using
- Fallback chain: If AI fails, return to heuristics with lower confidence
- Prompt testing: Test prompts on edge cases

**Warning signs:**
- AI returns invalid formats
- AI timeouts common
- AI confidence always 1.0 (overconfident)
- System crashes when AI fails

**Phase to address:**
Phase 4 (AI Integration) — Robust error handling and validation

---

### Pitfall 6: Pattern Matching False Positives

**What goes wrong:**
Learning system matches wrong patterns, applies incorrect corrections, makes accuracy worse.

**Why it happens:**
Pattern matching too loose, not supplier-specific enough, or patterns conflict.

**How to avoid:**
- Supplier-specific matching: Only match patterns for same supplier
- Pattern similarity threshold: Require high similarity (>0.8)
- Confidence weighting: Lower confidence boost for learned patterns
- Validation: Track if learned patterns improve or worsen accuracy
- Pattern conflicts: Detect and resolve conflicting patterns

**Warning signs:**
- Accuracy decreases after learning enabled
- Wrong corrections applied
- Patterns matching across different suppliers
- Low pattern similarity scores

**Phase to address:**
Phase 3 (Learning System) — Strict pattern matching, supplier isolation

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| JSON files for learning | Faster to implement | No queries, no indexing, poor performance | MVP only, migrate to SQLite quickly |
| Hardcode AI prompts | Faster development | Can't improve prompts without code changes | Never — use config files |
| No confidence calibration | Faster to ship | Confidence scores meaningless | Never — calibrate from start |
| Single AI provider | Simpler code | Vendor lock-in, no fallback | MVP acceptable, add second provider later |
| No learning cleanup | Faster to implement | Database bloat, performance issues | Never — build cleanup from start |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| OpenAI API | No rate limiting | Implement exponential backoff, rate limiting |
| OpenAI API | No error handling | Handle API errors, timeouts, retries |
| OpenAI API | Hardcoded API key | Use environment variables, config files |
| Claude API | Same as OpenAI | Same patterns apply |
| SQLite | No connection pooling | Use connection per thread, close properly |
| SQLite | No indexes | Add indexes on supplier_name, pattern_hash |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| AI calls synchronous | UI freezes during AI calls | Async AI calls, background processing | >10 invoices with low confidence |
| Learning queries unindexed | Slow pattern matching | Add indexes, optimize queries | >1000 learned patterns |
| No caching | Repeated AI calls for same invoice | Cache AI results, invoice fingerprinting | >100 invoices processed |
| Pattern matching O(n) | Slow learning lookups | Use hash-based matching, indexed queries | >500 patterns per supplier |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| API keys in code | Key exposure, unauthorized usage | Environment variables, secure storage |
| Learning data unencrypted | Privacy breach if database stolen | Encrypt sensitive data (supplier names, totals) |
| No input validation on corrections | Injection attacks, data corruption | Validate user corrections, sanitize inputs |
| AI prompts include sensitive data | Data leakage to AI provider | Sanitize prompts, exclude PII if possible |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Too many clicks to validate | Users skip validation | One-click selection, keyboard shortcuts |
| Candidates not visible | Users can't see options | Highlight in PDF, clear list |
| No feedback on learning | Users don't know if system improved | Show "learned from your correction" message |
| Validation required for all | Users frustrated with high-confidence cases | Only prompt when confidence < 0.95 |
| No batch validation | Slow for multiple invoices | Batch mode, validate all at once |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Manual Validation:** Often missing keyboard shortcuts — verify arrow keys work
- [ ] **Learning System:** Often missing pattern cleanup — verify consolidation works
- [ ] **AI Integration:** Often missing error handling — verify graceful degradation
- [ ] **Confidence Scoring:** Often missing calibration — verify scores match actual accuracy
- [ ] **Candidate Generation:** Often missing visual highlighting — verify PDF highlights work

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Over-reliance on AI | MEDIUM | Add confidence threshold, reduce AI usage, monitor costs |
| Learning database bloat | LOW | Run cleanup script, consolidate patterns, add limits |
| Confidence inflation | HIGH | Recalibrate scoring, validate against ground truth, adjust algorithm |
| Manual validation friction | MEDIUM | UX improvements, keyboard shortcuts, batch mode |
| AI prompt failure | MEDIUM | Improve prompts, add validation, implement fallback |
| Pattern matching false positives | HIGH | Tighten matching, supplier isolation, validate improvements |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Over-reliance on AI | Phase 1 (Confidence) | Measure AI usage, should be <20% of invoices |
| Learning database bloat | Phase 3 (Learning) | Database size stable, queries fast |
| Confidence inflation | Phase 1 (Confidence) | Confidence correlates with actual accuracy |
| Manual validation friction | Phase 2 (Validation UI) | Average validation time <10 seconds |
| AI prompt failure | Phase 4 (AI Integration) | AI error rate <1%, graceful degradation works |
| Pattern matching false positives | Phase 3 (Learning) | Accuracy improves, not decreases, after learning |

## Sources

- Existing codebase analysis — Current confidence scoring issues
- AI integration patterns — Common mistakes in AI systems
- Learning system patterns — Feedback loop pitfalls
- UX research — Manual validation best practices
- Performance optimization — Database and API patterns

---
*Pitfalls research for: Invoice parsing with confidence, learning, and AI*
*Researched: 2026-01-24*
