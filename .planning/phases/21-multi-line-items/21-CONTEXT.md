# Phase 21: Multi-line items - Context

**Phase:** 21 - Multi-line items  
**Created:** 2026-01-26  
**Milestone:** v2.1 Parsing robustness / EDI

---

## Phase Goal

Fortsättningsrader blir del av item-beskrivning utan att skapa falska nya rader.

---

## Background

**Problem:**
Fakturor har ofta line items med beskrivningar som spänner över flera rader (wrapped text). Nuvarande implementation i `wrap_detection.py` har grundläggande spatial proximity detection men saknar:
- Adaptiv Y-distance threshold (använder fast logik)
- Start-pattern detection för nya items (artikelnr, datum, individnr)
- Hantering av indenterade sub-items (strict X-alignment)
- Naturliga stopp-villkor (arbitrary max 3 wraps limit)

**Current State:**
- Befintlig `wrap_detection.py` (148 lines) med basic wrap detection
- X-tolerance ±2% page width
- Amount detection som stopp-villkor
- Max 3 wraps limit (arbitrary)
- Används av `invoice_line_parser.py` via `consolidate_wrapped_description()`

**Desired State:**
- Adaptiv Y-threshold baserad på median line height (1.5×)
- Start-pattern detection som övertrumfar spatial proximity
- Right-indent allowance för bullet points och sub-items
- Naturliga stopp-villkor utan arbitrary limits
- Robust hantering av edge cases (footer proximity, tight spacing, etc.)

---

## Requirements

### LINE-01: Continuation by Amount Absence
Om en rad saknar moms% + nettobelopp behandlas den som fortsättning på föregående item-beskrivning.

**Technical Details:**
- Primary signal: Row lacks VAT% (25.00/25,00) + net amount
- More reliable than spatial analysis alone
- Use existing `_contains_amount()` from wrap_detection.py

**Success Criteria:**
- Rows without amount+VAT% are added to previous description
- Multi-line descriptions consolidated with space separator

### LINE-02: New Item Start Patterns
Nytt item startar när raden matchar start-mönster (t.ex. `^\w{3,}\d+` eller `^\d{5,}`) eller innehåller individnr/konto/startdatum-mönster.

**Technical Details:**
- Article numbers: `^\d{5,}` (5+ digits), `^\w{3,}\d+` (alphanumeric)
- Dates: `^\d{4}-\d{2}-\d{2}` (ISO), `^\d{2}/\d{2}` (Swedish)
- Individnr: `^\d{6,8}-\d{4}` (YYYYMMDD-XXXX)
- Account codes: `^\d{4}\s` (4-digit followed by space)

**Success Criteria:**
- Start-pattern detection overrides spatial proximity
- Tightly-spaced separate items not incorrectly merged
- Article numbers at row start trigger new item

---

## Dependencies

### Phase 20 (Complete)
- Table block boundary detection (provides filtered rows)
- VAT%-anchored net amount extraction (provides `require_moms` flag)
- Footer filtering (prevents wrapping footer rows to items)
- Swedish Decimal normalization (amount detection)

### Existing Implementation
- `src/pipeline/wrap_detection.py` (148 lines) - Enhancement target
- `src/pipeline/invoice_line_parser.py` (802 lines) - Integration point
- `tests/test_invoice_line_parser.py` (380 lines) - Regression baseline

---

## Research Findings (Summary)

**Key Findings:**
1. **Adaptive Y-distance thresholds essential** - 1.5× median line height (WCAG)
2. **Amount absence = primary signal** - More reliable than spatial alone
3. **Start-pattern overrides proximity** - Prevents false merges
4. **X-alignment = secondary validation** - ±2% + right-indent allowance
5. **Multi-page requires header detection** - Out of scope for Plan 21-01

**Standard Stack:**
- pdfplumber for font size extraction (`char['size']`)
- statistics.median for adaptive threshold calculation
- re (stdlib) for start-pattern matching

**Existing Implementation Gaps:**
- ❌ No adaptive Y-threshold (uses fixed logic)
- ❌ No start-pattern detection
- ❌ No right-indent allowance for X-alignment
- ❌ Arbitrary max 3 wraps limit
- ✅ X-tolerance ±2% (good)
- ✅ Amount detection stop (good)

**Full Research:** `.planning/phases/21-multi-line-items/21-RESEARCH.md` (1125 lines)

---

## Constraints

### Must Maintain
- Backward compatibility with existing `wrap_detection.py` API
- Phase 20 table block detection (don't break)
- Swedish invoice format support (Ramirent, Cramo, etc.)
- pdfplumber text-layer extraction compatibility

### Must Not
- Break Phase 20 regression tests
- Introduce ML/AI dependencies (deterministic rules only)
- Implement multi-page continuation in Plan 21-01 (future scope)
- Handle multiple VAT rates (Phase 22 scope)

### Performance
- Adaptive threshold calculation should be O(n) where n = rows
- Start-pattern matching should use compiled regex
- No significant performance degradation vs current implementation

---

## Out of Scope (Phase 21)

### Deferred to Future Phases
- **Multi-page table continuation** - Cross-page wrapped items (consider Plan 21-02 or Phase 22)
- **Multiple VAT rates (12%, 6%)** - Phase 22 scope (validation-driven re-extraction)
- **Multi-column descriptions** - Complex layout, future phase
- **Structured hierarchy preservation** - Flatten for Phase 21, structured approach later

### Explicitly Out of Scope
- AI/ML-based wrap detection - Deterministic rules sufficient
- OCR-based wrap detection - Text-layer only (Phase 16 decision)
- Real-time processing - Batch processing only
- Web-UI - Desktop GUI only

---

## Success Criteria (Detailed)

### Functional
1. ✅ Rader utan moms% + nettobelopp läggs till föregående beskrivning (LINE-01)
2. ✅ Nytt item startar vid start-mönster match (LINE-02)
3. ✅ Adaptiv Y-threshold hanterar 10pt-14pt font variation
4. ✅ Right-indent allowance hanterar bullet points och sub-items
5. ✅ No arbitrary wrap limit (natural stopping conditions only)

### Technical
1. ✅ All edge cases from research covered (8 pitfalls tested)
2. ✅ Phase 20 regression tests pass (backward compatibility)
3. ✅ Performance: <10ms additional overhead per invoice page
4. ✅ Code coverage: >90% for new wrap detection logic

### Quality
1. ✅ No false positives: Separate items not incorrectly merged
2. ✅ No false negatives: Wrapped descriptions not truncated
3. ✅ Footer proximity: Footer rows not wrapped to items
4. ✅ Article number detection: New items correctly identified

---

## Testing Strategy

### Unit Tests
- Adaptive Y-threshold calculation (median, fallback)
- Start-pattern detection (all patterns)
- X-alignment with right-indent allowance
- No arbitrary wrap limit validation

### Edge Case Tests (from Research Pitfalls)
1. Indented sub-items (bullet points, right-indent)
2. Footer proximity (continuation rows near footer)
3. Tightly-spaced separate items (start-pattern prevents merge)
4. Mixed wrapped/non-wrapped items
5. Article numbers vs descriptions
6. Variable font sizes (10pt, 12pt, 14pt)
7. Very long wrapped items (10+ lines)
8. Empty/whitespace-only rows

### Integration Tests
- Full invoice with multi-line items
- Multiple pages with consistent wrapping
- Phase 20 compatibility (table blocks, footer filtering, VAT%)

### Regression Tests
- Phase 20 tests continue to pass
- Existing wrap_detection.py behavior preserved where applicable

---

## Handoff from Phase 20

**Completed:**
- ✅ Table block boundary detection working
- ✅ VAT%-anchored net amount extraction
- ✅ Footer filtering (hard/soft keywords)
- ✅ Swedish Decimal normalization

**Limitations to Address:**
- ⚠️ Single VAT rate (25%) only - Not Phase 21 scope, note for Phase 22
- ℹ️ Multi-page table continuation - Not Phase 21-01 scope

**Integration Points:**
- `invoice_line_parser.py`: Extract line items → detect wraps → consolidate → create InvoiceLine
- `wrap_detection.py`: Enhanced with adaptive threshold + start-patterns
- Tests: Extend test_invoice_line_parser.py + create test_wrap_detection.py

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Adaptive threshold too aggressive (merges separate items) | MEDIUM | HIGH | Start-pattern detection overrides; test with tight-spaced invoices |
| Start-pattern false positives (numbers in descriptions) | LOW | MEDIUM | Anchor patterns to row start (`^` prefix); test with varied descriptions |
| Right-indent allowance too loose (incorrect wraps) | LOW | MEDIUM | Limit to +5% (research-validated); combine with amount absence check |
| Performance degradation (median calculation) | LOW | LOW | O(n) algorithm; cache threshold per page |
| Backward compatibility break | MEDIUM | HIGH | Comprehensive regression tests; preserve existing API signatures |

---

## Next Steps After Phase 21

### Phase 22: Valideringsdriven om-extraktion
- Validate line item totals against invoice totals
- Mode B re-extraction if validation fails
- Multiple VAT rate handling (12%, 6%)
- Debug artifacts for mismatches

### Future Considerations
- Multi-page table continuation (if needed)
- Multi-column description handling
- Structured hierarchy preservation (nested items)
- Supplier-specific configuration (pattern customization)

---

*Phase: 21-multi-line-items*  
*Context created: 2026-01-26*  
*Dependencies: Phase 20 complete*
