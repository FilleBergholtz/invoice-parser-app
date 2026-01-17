# Phase 2: Header + Wrap - Research

**Researched:** 2026-01-17
**Confidence:** HIGH
**Context:** .planning/phases/02-header-wrap/02-CONTEXT.md

## Executive Summary

Phase 2 adds field extraction and confidence scoring to Phase 1's document normalization foundation. Research focuses on: confidence scoring algorithms for invoice number and total amount extraction, traceability implementation patterns, wrap detection strategies, and mathematical validation for total amount reconciliation. Key finding: Multi-factor confidence scoring with weighted components (keyword proximity, position, format validation, mathematical validation) provides robust accuracy while maintaining hard gates (≥0.95 = OK, otherwise REVIEW).

## Research Questions Addressed

1. **Confidence scoring algorithms:** How to score multiple candidates for invoice number and total amount?
2. **Traceability patterns:** How to store and link evidence (page, bbox, text) back to source?
3. **Wrap detection:** How to identify and group multi-line item descriptions?
4. **Mathematical validation:** How to validate total amount against line item sums with tolerance?

## Key Findings

### 1. Confidence Scoring Algorithms

#### Invoice Number Scoring

**Multi-factor weighted scoring** is standard approach:
- **Position (0.30 weight):** Header zone (y < 0.3 * page_height) → high score
- **Keyword proximity (0.35 weight):** "fakturanummer/invoice number/nr/no" on same row or within 1 row → high score
- **Format validation (0.20 weight):** Alphanumeric, length 3-25, not date/amount/org number
- **Uniqueness (0.10 weight):** Appears once in document
- **OCR/Token confidence (0.05 weight):** Average confidence of tokens in candidate area

**Implementation pattern:**
```python
def score_invoice_number_candidate(candidate: str, row: Row, page: Page, all_rows: List[Row]) -> float:
    score = 0.0
    
    # Position scoring (0.30)
    if row.y < 0.3 * page.height:
        score += 0.30
    
    # Keyword proximity (0.35)
    keyword_pattern = r"(?:fakturanummer|invoice\s*number|no\.|nr|number)"
    if re.search(keyword_pattern, row.text, re.IGNORECASE):
        score += 0.35
    elif _has_keyword_in_adjacent_row(row, all_rows, keyword_pattern):
        score += 0.25  # Slightly lower for adjacent
    
    # Format validation (0.20)
    if _validate_invoice_number_format(candidate):
        score += 0.20
    
    # Uniqueness (0.10)
    if _appears_once_in_document(candidate, all_rows):
        score += 0.10
    
    # OCR confidence (0.05)
    avg_conf = _average_token_confidence(row.tokens)
    score += 0.05 * avg_conf
    
    return min(score, 1.0)  # Normalize to 0.0-1.0
```

**Threshold:** ≥0.95 = OK, otherwise REVIEW (hard gate)

#### Total Amount Scoring

**Mathematical validation weighted highest:**
- **Keyword match (0.35 weight):** "Att betala" strongest, "Total/Totalt" next
- **Position (0.20 weight):** Footer zone (y > 0.8 * page_height) + right-aligned
- **Mathematical validation (0.35 weight):** If subtotal + VAT + rounding ≈ total → full score
- **Relative size (0.10 weight):** Total should be largest amount in summation rows

**Implementation pattern:**
```python
def score_total_amount_candidate(candidate: float, row: Row, page: Page, 
                                 line_items: List[InvoiceLine], footer_rows: List[Row]) -> float:
    score = 0.0
    
    # Keyword match (0.35)
    keyword_scores = {
        "att betala": 0.35,
        "totalt": 0.30,
        "total": 0.30,
        "summa att betala": 0.30
    }
    row_lower = row.text.lower()
    for keyword, kw_score in keyword_scores.items():
        if keyword in row_lower:
            score += kw_score
            break
    
    # Position (0.20)
    if row.y > 0.8 * page.height:
        score += 0.20
    
    # Mathematical validation (0.35)
    if _validate_against_line_items(candidate, line_items, tolerance=1.0):
        score += 0.35
    elif line_items:
        score += 0.15  # Partial: has line items but doesn't validate
    
    # Relative size (0.10)
    if _is_largest_in_footer(candidate, footer_rows):
        score += 0.10
    
    return min(score, 1.0)
```

**Threshold:** ≥0.95 = OK, otherwise REVIEW

### 2. Traceability Implementation Patterns

**JSON structure for evidence storage:**
```json
{
  "field": "invoice_no|total",
  "value": "...",
  "confidence": 0.95,
  "evidence": {
    "page_number": 1,
    "bbox": [x, y, width, height],
    "row_index": 12,
    "text_excerpt": "Fakturanummer: INV-2024-001",
    "tokens": [
      {"text": "Fakturanummer", "bbox": [100, 50, 80, 12], "conf": 0.98},
      {"text": "INV-2024-001", "bbox": [190, 50, 90, 12], "conf": 0.95}
    ]
  }
}
```

**Implementation pattern:**
- Store as dataclass internally for type safety
- Serialize to JSON for review folder export
- BBox = union of all tokens in match (not just first token)
- Text excerpt = max 120 characters or full row if shorter
- Link via InvoiceHeader model (traceability for invoice_no and total)

**Key insight:** Evidence structure enables clickable PDF navigation (Phase 3) and manual verification during review workflow.

### 3. Wrap Detection Strategies

**Spatial position-based detection (robust across DPI):**
- X-position tolerance: ±2% of page width (not absolute pixels)
- Stop conditions: next row contains amount, X-start deviates > tolerance, max 3 wraps per line item
- Consolidation: append wrap text with space separator (Excel-friendly)

**Implementation pattern:**
```python
def detect_wrapped_rows(product_row: Row, following_rows: List[Row], page: Page) -> List[Row]:
    wraps = []
    tolerance = 0.02 * page.width  # 2% of page width
    description_start_x = _get_description_column_start(product_row)
    
    for next_row in following_rows:
        # Stop if next row has amount (new product row)
        if _contains_amount(next_row):
            break
        
        # Stop if X-start deviates beyond tolerance
        next_row_start_x = next_row.x_min
        if abs(next_row_start_x - description_start_x) > tolerance:
            break
        
        # Stop if max wraps reached
        if len(wraps) >= 3:
            break
        
        wraps.append(next_row)
    
    return wraps
```

**Key insight:** Spatial position (X-coordinates) more reliable than text indentation (spaces/tabs), handles OCR variations and formatting inconsistencies.

### 4. Mathematical Validation

**Formula:** `subtotal_ex_vat + vat_total + rounding ≈ total`

**Tolerance:** ±1 SEK (matches Phase 1 context decision for rounding, shipping, discounts)

**Implementation pattern:**
```python
def validate_total_against_line_items(total: float, line_items: List[InvoiceLine], 
                                      tolerance: float = 1.0) -> bool:
    lines_sum = sum(line.total_amount for line in line_items)
    diff = abs(total - lines_sum)
    return diff <= tolerance
```

**Edge cases:**
- Missing VAT breakdown: Only validate against lines_sum (no penalty, but lower confidence)
- Shipping/discount rows: Should be included in validation or handled separately?
- Multi-currency: Normalize before validation (Phase 2 scope: SEK only)

**Key insight:** Mathematical validation provides strongest signal (0.35 weight) for total amount confidence scoring.

## Architecture Patterns

### Pipeline Integration

**Execution order:**
1. After segment identification (Phase 1)
2. Extract header fields (invoice number, vendor, date) from header segment
3. Extract total amount from footer segment
4. Handle wrap detection during/after line item extraction
5. Store traceability for invoice number and total

**Data flow:**
```
Document → Segments (header, items, footer)
  → Header Segment → InvoiceHeader (invoice_no, vendor, date, confidence scores)
  → Footer Segment → Total Amount (with confidence scoring)
  → Items Segment → InvoiceLines → Wrap Detection → Consolidated InvoiceLines
  → Traceability → JSON evidence storage
```

### Confidence Score Storage

**InvoiceHeader model (from docs/02_data-model.md):**
- `invoice_number: Optional[str]` (extracted value or None)
- `invoice_number_confidence: float` (0.0-1.0)
- `total_amount: Optional[float]` (extracted or None)
- `total_confidence: float` (0.0-1.0)
- `traceability: Dict` (JSON structure with evidence)

**Hard gate evaluation:**
- `invoice_number_confidence >= 0.95 AND total_confidence >= 0.95` → OK
- Otherwise → REVIEW (no silent guessing)

## Implementation Recommendations

### Priority 1: Total Amount Extraction (Strongest Signal)

1. Extract from footer segment using keyword matching
2. Score candidates using mathematical validation (0.35 weight)
3. Validate against line item sums (if available)
4. Store with traceability evidence

### Priority 2: Invoice Number Extraction

1. Extract from header segment using keyword proximity
2. Score candidates using multi-factor weights (keyword 0.35, position 0.30)
3. Handle top-2 tie-breaking (if within 0.03, mark REVIEW)
4. Store with traceability evidence

### Priority 3: Traceability Implementation

1. Create Traceability dataclass (field, value, confidence, evidence)
2. Store in InvoiceHeader for invoice_no and total
3. Serialize to JSON for review folder export
4. Link to source tokens/rows via bbox and row_index

### Priority 4: Wrap Detection

1. Implement spatial X-position tolerance (±2% page width)
2. Detect wraps during line item extraction or post-processing
3. Consolidate wrap text with space separator
4. Update InvoiceLine.rows to include wrapped rows (already KÄLLSANING)

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Low OCR confidence on invoice number | High | Weight OCR confidence only 0.05, rely on keyword proximity + position |
| Mathematical validation fails (VAT calculation wrong) | Medium | Allow validation without VAT breakdown (lower confidence, not failure) |
| Wrap detection false positives | Medium | Max 3 wraps limit, stop on amount-containing row, strict X-tolerance |
| Confidence threshold too strict | Medium | Calibrate with test corpus, can adjust 0.95 threshold if needed |

## Codebase Integration Points

**Existing code to extend:**
- `src/pipeline/segment_identification.py` - Header/footer segments already identified
- `src/pipeline/invoice_line_parser.py` - Line items extracted, can add wrap detection
- `src/models/invoice_line.py` - InvoiceLine model exists, rows already KÄLLSANING

**New code to create:**
- `src/pipeline/header_extractor.py` - Invoice number, vendor, date extraction
- `src/pipeline/footer_extractor.py` - Total amount extraction with validation
- `src/pipeline/confidence_scoring.py` - Multi-factor scoring algorithms
- `src/pipeline/wrap_detection.py` - Wrap detection logic
- `src/models/invoice_header.py` - InvoiceHeader model (per docs/02_data-model.md)
- `src/models/traceability.py` - Traceability evidence structure

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Confidence scoring | HIGH | Multi-factor weighted scoring is standard pattern, weights calibrated from Phase 2 context |
| Traceability | HIGH | JSON structure clear, bbox/page references already in Phase 1 models |
| Wrap detection | HIGH | Spatial position approach robust, X-tolerance as percentage handles DPI variations |
| Mathematical validation | HIGH | Standard sum reconciliation, ±1 SEK tolerance matches Phase 1 decisions |

**Overall confidence:** HIGH

## Gaps to Address During Planning

- **Confidence threshold calibration:** 0.95 threshold may need adjustment based on test corpus results
- **VAT breakdown detection:** How to identify and extract subtotal, VAT, rounding separately for validation?
- **Vendor name extraction:** Heuristics needed (company name patterns, address separation)
- **Date parsing robustness:** Swedish date formats (e.g., "15 januari 2024") require robust parsing

## Sources

### Primary (HIGH confidence)
- Phase 2 Context: .planning/phases/02-header-wrap/02-CONTEXT.md (scoring weights, thresholds)
- Heuristics: docs/04_heuristics.md (Heuristik 5-11 for field extraction)
- Data model: docs/02_data-model.md (InvoiceHeader, InvoiceSpecification structure)
- Phase 1 codebase: src/pipeline/segment_identification.py, src/pipeline/invoice_line_parser.py

### Secondary (MEDIUM confidence)
- Research summary: .planning/research/SUMMARY.md (confidence scoring, validation patterns)
- Validation rules: docs/05_validation.md (mathematical validation, tolerance)

---
*Research completed: 2026-01-17*
*Ready for planning: yes*
