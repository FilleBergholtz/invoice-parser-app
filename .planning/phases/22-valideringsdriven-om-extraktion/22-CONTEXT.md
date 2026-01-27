# Phase 22: Valideringsdriven om-extraktion - Context

**Phase:** 22 - Valideringsdriven om-extraktion (mode B)  
**Created:** 2026-01-26  
**Milestone:** v2.1 Parsing robustness / EDI

---

## Phase Goal

Validering styr om-extraktion och sparar debug vid mismatch. Systemet kör table-parser mode B (position/kolumn-baserad) när text-baserad parsing misslyckas validering.

---

## Background

**Problem:**
Nuvarande parsing (mode A, text-based) fungerar bra för de flesta fakturor men kan misslyckas på fakturor med:
- Ovanliga kolumnlayouts
- Varierande spacing
- Komplexa tabellstrukturer
- Mixed formatting

När parsing misslyckas finns ingen automatisk fallback, och validering upptäcker felet först efter extraction.

**Current State:**
- Text-based parsing (mode A) i `invoice_line_parser.py`
- Validation kod i `validation.py` och `confidence_scoring.py`
- Debug artifacts system finns men används inte för table parsing failures
- Ingen position-based parsing (mode B)
- Ingen automatisk om-extraktion vid valideringsfel

**Desired State:**
- Validering körs direkt efter mode A extraction
- Vid valideringsfel → automatisk mode B (position-based) om-extraktion
- Vid kvarstående mismatch → status REVIEW + debug artifacts
- Konfigurerbart mode: auto (A→B fallback), text (alltid A), pos (alltid B)

---

## Requirements

### VAL-01: Netto Sum Validation
`sum(line_items.netto)` matchar "Nettobelopp exkl. moms" inom ±0,50 SEK.

**Technical Details:**
- Extract "Nettobelopp exkl. moms" från footer (redan implementerat i footer_extractor.py)
- Calculate `sum(line.netto for line in line_items)` (använd line.netto, inte total_amount)
- Compare med tolerance ±0,50 SEK
- Return validation result (passed/failed, diff)

**Success Criteria:**
- Validation passes när nettosumma matchar inom tolerance
- Validation fails när diff > 0,50 SEK
- Diff beräknas korrekt (signed difference)

### VAL-02: Total with VAT Validation
`netto + moms` matchar "Att betala" inom ±0,50 SEK.

**Technical Details:**
- Extract "Att betala" från footer (redan implementerat)
- Calculate `netto_sum + vat_amount` (vat_amount = netto_sum × 0.25 för 25% moms)
- Compare med tolerance ±0,50 SEK
- Return validation result

**Success Criteria:**
- Validation passes när total with VAT matchar
- Hanterar 25% moms korrekt (kan utökas till 12%/6% i framtida iteration)

### VAL-03: Mode B Re-extraction
Om VAL-01 fallerar körs **table-parser mode B** (position/kolumn-baserad andra pass).

**Technical Details:**
- Mode B: Position-based parsing via X-position clustering
- Kolumn-identifiering: Clustera tokens per X-position
- Mappa kolumner till fält: description, quantity, unit, unit_price, vat%, netto
- Använd samma VAT%-anchored extraction som mode A

**Success Criteria:**
- Mode B körs automatiskt när VAL-01 failar (auto mode)
- Mode B returnerar line items med korrekt nettosumma
- Mode B använder position-baserad parsing (inte text-based)

### VAL-04: Debug Artifacts on Mismatch
Om mismatch kvarstår → status REVIEW och **debug-artefakter** sparas.

**Technical Details:**
- Sparar tabellblockets råtext (alla rows.text)
- Sparar tolkade line items (JSON format)
- Sparar validation result (diff, status, errors)
- Sparas i `artifacts_dir/invoices/{invoice_id}/table_debug/`

**Success Criteria:**
- Debug artifacts sparas när mismatch kvarstår efter mode B
- Status sätts till REVIEW
- Artifacts är läsbara och användbara för debugging

### VAL-05: Configurable Mode
`table_parser_mode` är konfigurerbart: `auto|text|pos`.

**Technical Details:**
- `auto`: Kör mode A, fallback till mode B vid valideringsfel
- `text`: Alltid mode A (text-based)
- `pos`: Alltid mode B (position-based)
- Konfigurerbart per supplier profile eller globalt

**Success Criteria:**
- Mode kan sättas i config/supplier profile
- Auto mode fungerar korrekt (A → B fallback)
- Text/pos modes fungerar (alltid respektive mode)

---

## Dependencies

### Phase 21 (Complete)
- Multi-line item detection (wrap detection)
- Adaptive Y-threshold
- Start-pattern detection
- Table block boundary detection

### Phase 20 (Complete)
- VAT%-anchored net amount extraction
- Table block boundary detection
- Footer filtering

### Existing Implementation
- `src/pipeline/validation.py` (213 lines) - Validation logic
- `src/pipeline/confidence_scoring.py` (745 lines) - Confidence scoring, validation helpers
- `src/pipeline/footer_extractor.py` (750 lines) - Footer extraction, "Nettobelopp exkl. moms", "Att betala"
- `src/pipeline/invoice_line_parser.py` (812 lines) - Mode A (text-based) parsing
- `src/debug/artifact_manifest.py` - Debug artifacts system
- `src/config.py` - Configuration management

---

## Research Findings

**No separate research needed** - Phase 22 bygger på:
- Phase 20 research: Table segmentation patterns
- Phase 21 research: Multi-line item detection
- Existing validation patterns: `validation.py`, `confidence_scoring.py`

**Key Insights:**
1. **Position-based parsing** är mer robust för varierande layouts än text-based
2. **Validation-driven re-extraction** förbättrar accuracy utan att påverka normalväg
3. **Debug artifacts** är kritiska för troubleshooting och continuous improvement

---

## Constraints

### Must Maintain
- Backward compatibility med mode A (default behavior)
- Phase 20-21 functionality (table blocks, wrap detection, VAT% extraction)
- Existing validation logic (don't break current validation)
- Performance: Mode B ska inte köras om inte nödvändigt

### Must Not
- Break Phase 20-21 regression tests
- Introducera ML/AI dependencies (deterministic rules only)
- Automatisk korrigering utan REVIEW (osäkra fall → REVIEW)
- Ändra default beteende (mode A är default)

### Performance
- Mode B ska bara köras när nödvändigt (valideringsfel)
- Validation overhead: <5ms per invoice
- Debug artifact sparning: <10ms per invoice (async om möjligt)

---

## Out of Scope (Phase 22)

### Deferred to Future Phases
- **Multipla momssatser (12%, 6%)** - Kan addresseras i framtida iteration
- **AI-baserad om-extraktion** - Deterministiska regler först
- **Automatisk korrigering** - Osäkra fall går alltid till REVIEW
- **Multi-page table continuation** - Phase 21 scope (deferred)

### Explicitly Out of Scope
- OCR-based re-extraction - Text-layer only (Phase 16 decision)
- Real-time processing - Batch processing only
- Web-UI - Desktop GUI only

---

## Success Criteria (Detailed)

### Functional
1. ✅ VAL-01: Nettosumma valideras korrekt (±0,50 SEK tolerance)
2. ✅ VAL-02: Total with VAT valideras korrekt (±0,50 SEK tolerance)
3. ✅ VAL-03: Mode B körs automatiskt vid VAL-01 fail (auto mode)
4. ✅ VAL-04: Debug artifacts sparas vid kvarstående mismatch
5. ✅ VAL-05: `table_parser_mode` konfiguration fungerar

### Technical
1. ✅ Mode B parsing fungerar (position-based, kolumn-identifiering)
2. ✅ Validation overhead <5ms per invoice
3. ✅ Debug artifacts format är läsbart och användbart
4. ✅ Phase 20-21 regression tests passerar
5. ✅ Code coverage >90% för nya validation och mode B kod

### Quality
1. ✅ No false positives: Mode B körs bara när nödvändigt
2. ✅ No false negatives: Validering upptäcker alla mismatches
3. ✅ Debug artifacts innehåller all nödvändig information
4. ✅ Mode switching är transparent (ingen breaking change)

---

## Testing Strategy

### Unit Tests
- Netto sum validation (VAL-01)
- Total with VAT validation (VAL-02)
- Tolerance edge cases (±0,49 SEK, ±0,50 SEK, ±0,51 SEK)
- Mode B column detection
- Mode B parsing logic

### Integration Tests
- Full pipeline: Mode A → validation fail → mode B → success
- Auto mode fallback behavior
- Text/pos mode behavior
- Debug artifact sparning

### Regression Tests
- Phase 20-21 tests continue to pass
- Existing validation logic unchanged
- Backward compatibility verified

---

## Handoff from Phase 21

**Completed:**
- ✅ Multi-line item detection working
- ✅ Adaptive thresholds for wrap detection
- ✅ Start-pattern detection
- ✅ Table block boundary detection

**Integration Points for Phase 22:**
- `invoice_line_parser.py`: Extract line items → validate → mode B if needed
- `validation.py`: Add netto sum and VAT validation
- `footer_extractor.py`: Extract "Nettobelopp exkl. moms" and "Att betala"
- `debug/artifact_manifest.py`: Save table debug artifacts

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Mode B parsing too complex | MEDIUM | HIGH | Start with simple column detection, iterate |
| Validation overhead too high | LOW | MEDIUM | Optimize validation (cache calculations) |
| Mode B doesn't improve accuracy | MEDIUM | HIGH | Test with diverse invoice corpus first |
| Debug artifacts too large | LOW | LOW | Compress or limit artifact size |
| Breaking backward compatibility | LOW | HIGH | Comprehensive regression tests |

---

## Next Steps After Phase 22

### v2.1 Milestone Complete
- All Phase 16-22 requirements implemented
- Deterministic parsing for EDI-like invoices
- Validation-driven re-extraction
- Debug artifacts for troubleshooting

### Future Considerations
- Multiple VAT rates (12%, 6%) support
- AI-based re-extraction as additional fallback
- Multi-page table continuation
- Supplier-specific mode B tuning

---

*Phase: 22-valideringsdriven-om-extraktion*  
*Context created: 2026-01-26*  
*Dependencies: Phase 21 complete*
