# Phase 7: Learning System - Context

**Gathered:** 2026-01-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Build learning system that stores user corrections in SQLite database, extracts patterns from corrected invoices (supplier, layout, position), matches new invoices to learned patterns, and uses patterns to improve confidence scoring.

**Core Problem:** System needs to learn from user corrections to improve over time. Must extract supplier-specific patterns and apply them to similar invoices.

**Goal:** System learns from corrections and improves confidence scoring for similar invoices, resulting in measurable accuracy improvement over time.

</domain>

<decisions>
## Implementation Decisions

### 1. SQLite Learning Database

**Approach:**
- Use SQLite (embedded, no external dependencies)
- Store corrections, patterns, and pattern matches
- Tables: corrections, patterns, pattern_matches

**Schema:**
- `corrections`: Store user corrections from Phase 6 (import from JSON)
- `patterns`: Extracted patterns (supplier, layout hash, position, correct_total)
- `pattern_matches`: Matches between new invoices and learned patterns

### 2. Pattern Extraction

**Pattern Components:**
- Supplier name (normalized)
- Layout hash (hash of footer structure/position)
- Position (bbox coordinates of total amount)
- Correct total amount (from user correction)
- Confidence boost (how much to boost confidence when matched)

**Pattern Matching:**
- Supplier-specific only (no cross-supplier matching per LEARN-07)
- Similarity matching on layout hash
- Position proximity matching
- High similarity threshold to avoid false positives

### 3. Confidence Score Boosting

**Approach:**
- When pattern matches, boost candidate confidence score
- Boost amount based on pattern confidence (how often pattern was correct)
- Apply boost before calibration
- Don't override hard gates (still need ≥0.95 for OK status)

### 4. Pattern Consolidation

**Approach:**
- Consolidate similar patterns (same supplier, similar layout/position)
- Merge patterns with high similarity
- Keep pattern with highest confidence/usage count
- Prevent database bloat

### 5. Cleanup Strategy

**Approach:**
- Remove old patterns (not used in X days)
- Remove conflicting patterns (same supplier, different totals)
- Keep patterns with high confidence/usage
- Regular cleanup job (can be manual or scheduled)

</decisions>

<current_state>
## Current Implementation

**Files:**
- `src/learning/correction_collector.py` - Stores corrections in JSON format
- `src/learning/__init__.py` - Learning module package

**Current Features:**
- Correction collection to JSON (Phase 6)
- JSON format: invoice_id, supplier_name, original/corrected totals, confidence scores, timestamp

**Missing:**
- SQLite database schema
- Pattern extraction from corrections
- Pattern matching for new invoices
- Confidence score boosting
- Pattern consolidation
- Cleanup mechanisms

</current_state>

<requirements>
## Phase Requirements

- **LEARN-01**: System stores user corrections in SQLite learning database
- **LEARN-02**: System extracts patterns from corrected invoices (supplier, layout, position)
- **LEARN-03**: System matches new invoices to learned patterns (supplier-specific matching)
- **LEARN-04**: System uses learned patterns to improve confidence scoring for similar invoices
- **LEARN-05**: System consolidates similar patterns to prevent database bloat
- **LEARN-06**: System performs regular cleanup of old or conflicting patterns
- **LEARN-07**: System isolates patterns by supplier (no cross-supplier pattern matching)

</requirements>

<research>
## Research References

- `.planning/research/SUMMARY.md`: Supplier-specific learning, pattern matching, batch learning
- `.planning/research/ARCHITECTURE.md`: Learning Database component, Pattern Matcher component, Learning Flow
- `.planning/research/PITFALLS.md`: Pattern matching false positives (supplier isolation, high similarity threshold)

</research>
