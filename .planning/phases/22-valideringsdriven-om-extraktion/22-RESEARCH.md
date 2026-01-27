# Phase 22: Position-Based Table Parsing (Mode B) - Research

**Researched:** 2026-01-26
**Domain:** Position-based table parsing, column detection, spatial text analysis
**Confidence:** HIGH

## Summary

Position-based table parsing (mode B) uses X-position clustering to identify columns and extract fields, making it more robust than text-based parsing for invoices with variable layouts, inconsistent spacing, or complex table structures. Unlike text-based parsing that relies on regex patterns from row.text, position-based parsing groups tokens by X-coordinate and maps columns to fields using spatial relationships.

The established approach for deterministic position-based parsing is:
1. **Column detection** via X-position clustering (k-means or gap-based) to identify column boundaries
2. **Token-to-column mapping** by assigning tokens to nearest column center based on X-position
3. **Field identification** using hybrid approach: position (which column) + content (VAT% patterns, unit keywords)
4. **Row-by-row extraction** with column-based field extraction (more robust than text-based for variable layouts)
5. **Fallback to content-based** when position fails (VAT% patterns, unit keywords still used)

**Primary recommendation:** Use gap-based column detection (simpler than k-means, more robust for invoices) combined with content-based field identification (VAT% patterns, unit keywords). Position-based parsing is fallback for mode A failures, not replacement - use when validation detects mismatch.

## Standard Stack

The established libraries/tools for position-based table parsing:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pdfplumber | 0.11.9+ (Jan 2026) | PDF text extraction with character-level positioning | Provides `chars` with `x0`, `y0`, `x1`, `y1` attributes; enables X-position clustering and column detection |
| statistics (stdlib) | Python 3.8+ | Median/mean calculations for column detection | Calculate column centers from token X-positions; robust against outliers |
| collections (stdlib) | Python 3.8+ | defaultdict, Counter for token grouping | Group tokens by column, count column usage |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | 1.24+ (optional) | Array operations for clustering | If using k-means for column detection (overkill for most invoices) |
| scipy | 1.10+ (optional) | Clustering algorithms | If using advanced clustering (DBSCAN, hierarchical) - not recommended for invoices |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| k-means clustering | Gap-based column detection | k-means requires knowing column count; gap-based is simpler and more robust for variable layouts |
| Fixed column positions | Adaptive column detection | Fixed positions break with layout variations; adaptive detection handles variable layouts |
| Pure position-based | Hybrid position+content | Pure position fails when columns overlap or merge; hybrid uses content (VAT%, unit keywords) as validation |

**Installation:**
```bash
# No additional dependencies needed beyond Phase 20-21 stack
# Already have: pdfplumber, statistics, collections
# Optional: numpy/scipy for advanced clustering (not recommended)
```

## Architecture Patterns

### Recommended Project Structure
```
src/pipeline/
├── invoice_line_parser.py      # Mode A (text-based) + Mode B (position-based)
├── column_detection.py          # Column detection algorithms (new)
├── position_parser.py           # Position-based field extraction (new)
└── validation.py                # Validation logic (existing, enhanced)
```

### Pattern 1: Gap-Based Column Detection

**What:** Identify columns by analyzing gaps (spaces) between token clusters in X-direction.

**When to use:** Always for invoice tables. Simpler and more robust than k-means for variable layouts.

**Example:**
```python
def detect_columns_gap_based(rows: List[Row], min_gap: float = 20.0) -> List[float]:
    """Detect columns using gap-based algorithm.
    
    Args:
        rows: List of table rows
        min_gap: Minimum gap between columns (default 20pt)
        
    Returns:
        List of column center X-positions (sorted left to right)
    """
    # Collect all token X-positions
    x_positions = []
    for row in rows:
        for token in row.tokens:
            x_center = token.x + (token.width / 2)  # Use center, not left edge
            x_positions.append(x_center)
    
    if not x_positions:
        return []
    
    # Sort X-positions
    x_positions.sort()
    
    # Find gaps (large spaces between consecutive X-positions)
    gaps = []
    for i in range(len(x_positions) - 1):
        gap = x_positions[i + 1] - x_positions[i]
        if gap > min_gap:
            gaps.append((x_positions[i], x_positions[i + 1], gap))
    
    # Column boundaries are midpoints of large gaps
    column_boundaries = []
    for left_x, right_x, gap_size in gaps:
        boundary = (left_x + right_x) / 2
        column_boundaries.append(boundary)
    
    # Column centers are midpoints between boundaries
    column_centers = []
    if column_boundaries:
        # First column: from 0 to first boundary
        column_centers.append(column_boundaries[0] / 2)
        
        # Middle columns: between boundaries
        for i in range(len(column_boundaries) - 1):
            center = (column_boundaries[i] + column_boundaries[i + 1]) / 2
            column_centers.append(center)
        
        # Last column: from last boundary to page width
        page_width = rows[0].page.width if rows else 595.0
        last_center = (column_boundaries[-1] + page_width) / 2
        column_centers.append(last_center)
    else:
        # No gaps found - single column (description only)
        column_centers.append(statistics.median(x_positions))
    
    return sorted(column_centers)
```

**Why this works:** Invoice tables have consistent column spacing. Large gaps (>20pt) indicate column boundaries. Gap-based detection is simpler than k-means and doesn't require knowing column count in advance.

### Pattern 2: Header Row Column Mapping

**What:** Use header row to identify which column contains which field (description, quantity, unit, price, VAT%, netto).

**When to use:** When header row is available (most invoices have header rows).

**Example:**
```python
def map_columns_from_header(header_row: Row, column_centers: List[float]) -> Dict[str, int]:
    """Map columns to fields using header row keywords.
    
    Args:
        header_row: Table header row (e.g., "Artikelnr Benämning Antal Enhet Pris Moms% Nettobelopp")
        column_centers: List of column center X-positions
        
    Returns:
        Dict mapping field names to column indices: {'description': 1, 'quantity': 2, ...}
    """
    field_keywords = {
        'description': ['benämning', 'beskrivning', 'artikel', 'produkt', 'text'],
        'quantity': ['antal', 'kvantitet', 'qty', 'st', 'mängd'],
        'unit': ['enhet', 'unit', 'st', 'kg', 'tim'],
        'unit_price': ['pris', 'á-pris', 'a-pris', 'enhetspris', 'price'],
        'vat_percent': ['moms', 'moms%', 'vat', 'vat%'],
        'netto': ['nettobelopp', 'netto', 'belopp', 'total', 'summa']
    }
    
    column_map = {}
    
    # For each token in header, find which column it belongs to
    for token in header_row.tokens:
        token_center = token.x + (token.width / 2)
        token_text_lower = token.text.lower()
        
        # Find nearest column
        nearest_col_idx = min(
            range(len(column_centers)),
            key=lambda i: abs(column_centers[i] - token_center)
        )
        
        # Check if token matches any field keywords
        for field_name, keywords in field_keywords.items():
            if any(keyword in token_text_lower for keyword in keywords):
                column_map[field_name] = nearest_col_idx
                break
    
    return column_map
```

**Why this works:** Header rows explicitly label columns. Using header keywords is more reliable than inferring column purpose from content alone.

### Pattern 3: Token-to-Column Assignment

**What:** Assign each token to its nearest column based on X-position.

**When to use:** Always. Required for position-based parsing.

**Example:**
```python
def assign_tokens_to_columns(
    row: Row,
    column_centers: List[float]
) -> Dict[int, List[Token]]:
    """Assign tokens to columns based on X-position.
    
    Args:
        row: Row to process
        column_centers: List of column center X-positions
        
    Returns:
        Dict mapping column index to list of tokens in that column
    """
    column_tokens = {i: [] for i in range(len(column_centers))}
    
    for token in row.tokens:
        token_center = token.x + (token.width / 2)
        
        # Find nearest column
        nearest_col_idx = min(
            range(len(column_centers)),
            key=lambda i: abs(column_centers[i] - token_center)
        )
        
        column_tokens[nearest_col_idx].append(token)
    
    return column_tokens
```

**Why this works:** Tokens naturally cluster around column centers. Nearest-neighbor assignment is simple and robust.

### Pattern 4: Hybrid Position+Content Field Extraction

**What:** Use position (which column) + content (VAT% patterns, unit keywords) to identify fields.

**When to use:** Always. Pure position fails when columns overlap or merge.

**Example:**
```python
def extract_fields_from_columns(
    column_tokens: Dict[int, List[Token]],
    column_map: Optional[Dict[str, int]] = None
) -> Dict[str, Any]:
    """Extract fields from columns using hybrid position+content approach.
    
    Args:
        column_tokens: Dict mapping column index to tokens
        column_map: Optional mapping from header row (if available)
        
    Returns:
        Dict with extracted fields: {'description': str, 'quantity': Decimal, ...}
    """
    fields = {}
    
    # Method 1: Use column_map if available (header-based)
    if column_map:
        for field_name, col_idx in column_map.items():
            if col_idx in column_tokens:
                tokens = column_tokens[col_idx]
                fields[field_name] = extract_field_from_tokens(tokens, field_name)
    
    # Method 2: Content-based fallback (VAT% patterns, unit keywords)
    # If column_map missing or incomplete, use content patterns
    if 'vat_percent' not in fields:
        # Search all columns for VAT% pattern
        for col_idx, tokens in column_tokens.items():
            text = " ".join(t.text for t in tokens)
            if re.search(r'\b25[.,]00\b', text):
                fields['vat_percent'] = Decimal("25.00")
                # Net amount is rightmost amount after VAT% column
                fields['netto'] = find_rightmost_amount_after_column(col_idx, column_tokens)
                break
    
    if 'unit' not in fields:
        # Search for unit keywords
        unit_keywords = ['st', 'kg', 'tim', 'ea', 'pcs', 'm²', 'm3']
        for col_idx, tokens in column_tokens.items():
            for token in tokens:
                if token.text.lower() in unit_keywords:
                    fields['unit'] = token.text
                    # Quantity is typically left of unit
                    if col_idx > 0:
                        fields['quantity'] = extract_quantity_from_column(column_tokens[col_idx - 1])
                    break
    
    return fields
```

**Why this works:** Position identifies which column, content validates field type. Hybrid approach is more robust than pure position or pure content alone.

### Pattern 5: Column Width Normalization

**What:** Normalize column positions relative to page width to handle different PDF sizes.

**When to use:** When processing invoices from different sources with varying page sizes.

**Example:**
```python
def normalize_column_positions(
    column_centers: List[float],
    page_width: float
) -> List[float]:
    """Normalize column positions to 0.0-1.0 range (percentage of page width).
    
    Args:
        column_centers: List of absolute X-positions
        page_width: Page width in points
        
    Returns:
        List of normalized positions (0.0-1.0)
    """
    return [x / page_width for x in column_centers]

def denormalize_column_positions(
    normalized_centers: List[float],
    page_width: float
) -> List[float]:
    """Convert normalized positions back to absolute X-positions."""
    return [x * page_width for x in normalized_centers]
```

**Why this works:** Different PDFs have different page sizes (A4, Letter, custom). Normalization makes column detection consistent across page sizes.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Column detection | Custom clustering algorithm | Gap-based detection or simple k-means | Column detection is well-studied; gap-based is simpler and more robust for invoices |
| Token-to-column mapping | Complex spatial analysis | Nearest-neighbor assignment | Simple nearest-neighbor is sufficient for invoice tables; complex algorithms add overhead |
| Field identification | Pure position-based | Hybrid position+content | Pure position fails when columns overlap; content patterns (VAT%, unit keywords) provide validation |
| Column width variation | Fixed column positions | Adaptive column detection | Fixed positions break with layout variations; adaptive detection handles variable layouts |
| Multi-column descriptions | Single column assumption | Column span detection | Descriptions can span multiple columns; detect column spans for accurate extraction |

**Key insight:** Position-based parsing is complementary to text-based parsing, not replacement. Use position when text-based fails (validation detects mismatch), but still leverage content patterns (VAT%, unit keywords) for field identification.

## Common Pitfalls

### Pitfall 1: Over-Clustering (Too Many Columns)

**What goes wrong:** Column detection identifies too many columns (treats every token gap as column boundary).

**Why it happens:** Small gaps between tokens (e.g., space between words in description) are treated as column boundaries.

**How to avoid:**
- Use minimum gap threshold (e.g., 20pt) to filter small gaps
- Analyze gap distribution: use median gap × 2 as threshold
- Consider column count from header row (if available)

**Warning signs:**
- Column count >> expected (e.g., 15 columns when invoice has 5)
- Many single-token columns
- Description split across multiple columns

### Pitfall 2: Under-Clustering (Too Few Columns)

**What goes wrong:** Column detection identifies too few columns (misses column boundaries).

**Why it happens:** Columns are tightly spaced (small gaps), or gap threshold is too high.

**How to avoid:**
- Use adaptive gap threshold (median gap × 1.5 instead of fixed 20pt)
- Analyze header row for column count hint
- Fallback to content-based detection if column count seems wrong

**Warning signs:**
- Column count << expected (e.g., 2 columns when invoice has 5)
- Multiple fields merged into single column
- Validation fails (mismatch between extracted and expected)

### Pitfall 3: Column Overlap (Tokens in Multiple Columns)

**What goes wrong:** Tokens are assigned to wrong column due to overlap or misalignment.

**Why it happens:** Columns are not perfectly aligned, or tokens span column boundaries.

**How to avoid:**
- Use token center (not left edge) for column assignment
- Allow column assignment tolerance (±5% of column width)
- Use content validation (VAT% patterns, unit keywords) to correct misassignments

**Warning signs:**
- Same token appears in multiple columns
- Field extraction produces unexpected values
- Validation fails with large differences

### Pitfall 4: Variable Column Widths

**What goes wrong:** Column detection assumes fixed column widths, fails when columns vary.

**Why it happens:** Description column is wider than quantity/unit columns, or columns have inconsistent spacing.

**How to avoid:**
- Use gap-based detection (handles variable widths naturally)
- Don't assume fixed column positions
- Use header row to identify column boundaries (if available)

**Warning signs:**
- Column detection works for some rows but not others
- Description tokens assigned to wrong column
- Validation fails for some line items but not others

### Pitfall 5: Merged Cells / Multi-Column Fields

**What goes wrong:** Fields spanning multiple columns (e.g., description + article number) are split incorrectly.

**Why it happens:** Position-based parsing assumes one field per column, but some fields span columns.

**How to avoid:**
- Detect column spans: if tokens in adjacent columns have similar content, merge columns
- Use content-based validation: if description seems incomplete, check adjacent columns
- Allow flexible column mapping (description can span columns 0-2, not just column 0)

**Warning signs:**
- Descriptions are truncated
- Article numbers separated from descriptions
- Validation fails due to incomplete field extraction

### Pitfall 6: Ragged Columns (Variable Alignment)

**What goes wrong:** Columns are not perfectly aligned across rows (ragged right/left alignment).

**Why it happens:** PDF layout uses variable spacing, or columns are right-justified with varying widths.

**How to avoid:**
- Use column center (not left edge) for token assignment
- Allow tolerance for column assignment (±10% of column width)
- Use content-based validation to correct misalignments

**Warning signs:**
- Same field appears in different columns across rows
- Validation fails inconsistently
- Field extraction produces varying results for similar rows

### Pitfall 7: Header Row Missing or Incorrect

**What goes wrong:** Column mapping fails because header row is missing or doesn't match actual columns.

**Why it happens:** Some invoices don't have header rows, or header row format differs from data rows.

**How to avoid:**
- Fallback to content-based field identification when header missing
- Validate header row: check if it contains expected keywords
- Use hybrid approach: header for hint, content for validation

**Warning signs:**
- Column map is empty or incomplete
- Fields extracted from wrong columns
- Validation fails with systematic errors

### Pitfall 8: Position-Based Parsing Slower Than Text-Based

**What goes wrong:** Mode B (position-based) is significantly slower than mode A (text-based).

**Why it happens:** Column detection and token-to-column mapping add overhead.

**How to avoid:**
- Cache column detection results (columns don't change within table)
- Optimize token-to-column assignment (use sorted column centers for binary search)
- Only run mode B when necessary (validation detects mismatch)

**Warning signs:**
- Mode B takes >100ms per invoice (vs <10ms for mode A)
- Performance degradation in batch processing
- User complaints about slow processing

## Code Examples

Verified patterns from research and existing codebase:

### Gap-Based Column Detection
```python
# Source: Based on Phase 20 research and heuristics.md
def detect_columns_gap_based(rows: List[Row], min_gap: float = 20.0) -> List[float]:
    """Detect columns using gap-based algorithm.
    
    Algorithm:
    1. Collect all token X-positions (centers)
    2. Sort X-positions
    3. Find gaps > min_gap (column boundaries)
    4. Calculate column centers (midpoints between boundaries)
    """
    x_positions = []
    for row in rows:
        for token in row.tokens:
            x_center = token.x + (token.width / 2)
            x_positions.append(x_center)
    
    if not x_positions:
        return []
    
    x_positions.sort()
    
    # Find large gaps (column boundaries)
    gaps = []
    for i in range(len(x_positions) - 1):
        gap = x_positions[i + 1] - x_positions[i]
        if gap > min_gap:
            gaps.append((x_positions[i], x_positions[i + 1], gap))
    
    # Calculate column centers
    if not gaps:
        # Single column
        return [statistics.median(x_positions)]
    
    column_centers = []
    page_width = rows[0].page.width if rows else 595.0
    
    # First column
    column_centers.append(gaps[0][0] / 2)
    
    # Middle columns
    for i in range(len(gaps) - 1):
        center = (gaps[i][1] + gaps[i + 1][0]) / 2
        column_centers.append(center)
    
    # Last column
    last_center = (gaps[-1][1] + page_width) / 2
    column_centers.append(last_center)
    
    return sorted(column_centers)
```

### Token-to-Column Assignment
```python
# Source: Based on Pattern 3
def assign_tokens_to_columns(
    row: Row,
    column_centers: List[float]
) -> Dict[int, List[Token]]:
    """Assign tokens to columns using nearest-neighbor."""
    column_tokens = {i: [] for i in range(len(column_centers))}
    
    for token in row.tokens:
        token_center = token.x + (token.width / 2)
        
        # Binary search for nearest column (optimization)
        nearest_col_idx = min(
            range(len(column_centers)),
            key=lambda i: abs(column_centers[i] - token_center)
        )
        
        column_tokens[nearest_col_idx].append(token)
    
    return column_tokens
```

### Hybrid Field Extraction
```python
# Source: Based on Pattern 4 and Phase 20 VAT%-anchored extraction
def extract_netto_from_columns(
    column_tokens: Dict[int, List[Token]],
    column_map: Optional[Dict[str, int]] = None
) -> Optional[Decimal]:
    """Extract net amount using hybrid position+content approach.
    
    Strategy:
    1. If column_map available: use mapped 'netto' column
    2. Else: find VAT% column, take rightmost amount after it
    """
    # Method 1: Use column_map if available
    if column_map and 'netto' in column_map:
        col_idx = column_map['netto']
        if col_idx in column_tokens:
            tokens = column_tokens[col_idx]
            text = " ".join(t.text for t in tokens)
            return extract_amount_from_text(text)
    
    # Method 2: Content-based (VAT%-anchored)
    # Find VAT% column
    vat_col_idx = None
    for col_idx, tokens in column_tokens.items():
        text = " ".join(t.text for t in tokens)
        if re.search(r'\b25[.,]00\b', text):
            vat_col_idx = col_idx
            break
    
    if vat_col_idx is None:
        return None
    
    # Find rightmost amount after VAT% column
    amounts = []
    for col_idx in range(vat_col_idx + 1, len(column_tokens)):
        if col_idx in column_tokens:
            tokens = column_tokens[col_idx]
            text = " ".join(t.text for t in tokens)
            amount = extract_amount_from_text(text)
            if amount:
                amounts.append((col_idx, amount))
    
    if amounts:
        # Return rightmost (highest column index)
        return max(amounts, key=lambda x: x[0])[1]
    
    return None
```

### Mode B Integration
```python
# Source: Based on Phase 22 plan
def extract_invoice_lines_mode_b(
    segment: Segment,
    table_rows: List[Row]
) -> List[InvoiceLine]:
    """Extract line items using position-based parsing (mode B).
    
    Algorithm:
    1. Detect columns via gap-based algorithm
    2. Map columns to fields using header row (if available)
    3. For each row:
       a. Assign tokens to columns
       b. Extract fields from columns (hybrid position+content)
       c. Create InvoiceLine object
    """
    # Step 1: Detect columns
    column_centers = detect_columns_gap_based(table_rows)
    
    if not column_centers:
        # Fallback to mode A if column detection fails
        return extract_invoice_lines_mode_a(segment, table_rows)
    
    # Step 2: Map columns to fields (if header available)
    header_row = find_header_row(table_rows)
    column_map = None
    if header_row:
        column_map = map_columns_from_header(header_row, column_centers)
    
    # Step 3: Extract line items
    line_items = []
    for row in table_rows:
        if _is_footer_row(row) or _is_table_header_row(row.text.lower()):
            continue
        
        # Assign tokens to columns
        column_tokens = assign_tokens_to_columns(row, column_centers)
        
        # Extract fields
        fields = extract_fields_from_columns(column_tokens, column_map)
        
        # Create InvoiceLine (same as mode A)
        if fields.get('netto'):
            line_item = InvoiceLine(
                description=fields.get('description', ''),
                quantity=fields.get('quantity'),
                unit=fields.get('unit'),
                unit_price=fields.get('unit_price'),
                discount=fields.get('discount'),
                total_amount=fields.get('netto')
            )
            line_items.append(line_item)
    
    return line_items
```

## State of the Art (2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed column positions | Adaptive column detection | 2020+ | Handles variable layouts across suppliers |
| Pure text-based parsing | Hybrid text+position | 2022+ | More robust for complex table structures |
| k-means clustering | Gap-based detection | 2023+ | Simpler, doesn't require knowing column count |
| Single parsing mode | Multi-mode with validation-driven fallback | 2024-2025 | Improves accuracy without affecting normal path |
| Manual column mapping | Header-based + content-based | 2024+ | Reduces configuration burden |

**New tools/patterns to consider:**
- **Validation-driven re-extraction:** Emerging pattern where validation triggers alternative parsing mode. More efficient than always running multiple modes.
- **Hybrid position+content:** Combining spatial analysis with content patterns (VAT%, unit keywords) provides robustness without complexity.

**Deprecated/outdated:**
- **Fixed column indices:** Brittle across layout variations; adaptive detection is now standard
- **Pure position-based (no content validation):** Fails when columns overlap; hybrid approach is required
- **Always running multiple modes:** Inefficient; validation-driven fallback is better

## Open Questions

Things that couldn't be fully resolved:

1. **Optimal gap threshold for column detection:**
   - What we know: 20pt works for most invoices
   - What's unclear: Whether threshold should be adaptive (median gap × multiplier) or fixed
   - Recommendation: Start with fixed 20pt, make adaptive if needed based on test corpus

2. **Column span detection for multi-column descriptions:**
   - What we know: Descriptions can span multiple columns
   - What's unclear: How to detect column spans automatically
   - Recommendation: Start with single-column assumption, add span detection if needed

3. **Performance optimization for mode B:**
   - What we know: Mode B adds overhead (column detection, token assignment)
   - What's unclear: Whether caching or other optimizations are needed
   - Recommendation: Measure performance first, optimize if mode B takes >50ms per invoice

4. **Multi-page table column consistency:**
   - What we know: Columns may vary across pages in multi-page invoices
   - What's unclear: Whether to detect columns per-page or per-document
   - Recommendation: Detect columns per-page (more robust for layout variations)

5. **When to prefer mode B over mode A:**
   - What we know: Mode B is fallback for validation failures
   - What's unclear: Whether some invoice types should always use mode B
   - Recommendation: Start with validation-driven fallback, add supplier-specific config if needed

## Sources

### Primary (HIGH confidence)
- **pdfplumber documentation** - https://github.com/jsvine/pdfplumber - Character-level positioning, table extraction capabilities
- **Phase 20 research** - `.planning/phases/20-tabellsegment-kolumnregler/20-RESEARCH.md` - Positional parsing patterns, column identification
- **Heuristics documentation** - `docs/04_heuristics.md` - Column-based parsing heuristics, X-position clustering
- **Existing codebase** - `src/models/row.py`, `src/models/token.py` - Row/Token models with X/Y positioning

### Secondary (MEDIUM confidence)
- **Stack Overflow: PDF table column detection** - Multiple sources (2023-2025) on gap-based vs k-means clustering - Cross-referenced with implementation patterns
- **Camelot documentation** - https://camelot-py.readthedocs.io/ - Table extraction with column detection (different approach but relevant)

### Tertiary (LOW confidence)
- **WebSearch: Position-based text extraction** - Blog posts and articles (2022-2025) - General patterns, not verified with authoritative sources
- **Academic papers: Table structure detection** - Research papers on column detection algorithms - Theoretical, not verified with production code

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pdfplumber is industry-standard, verified with official docs
- Architecture patterns: HIGH - Patterns based on Phase 20 research and existing codebase heuristics
- Pitfalls: MEDIUM-HIGH - Based on logical analysis and cross-referenced with Phase 20 research; some not tested in production
- State of the Art: MEDIUM - Based on general trends and Phase 20 research; position-based parsing is established pattern

**Research date:** 2026-01-26
**Valid until:** ~90 days (April 2026) for library versions; ~180 days (July 2026) for architecture patterns (stable domain)

**Phase 22 implementation status:** PLANNED - This research provides foundation for mode B implementation.
