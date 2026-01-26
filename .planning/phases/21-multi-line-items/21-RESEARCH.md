# Phase 21: Multi-line items - Research

**Researched:** 2026-01-26
**Domain:** Multi-line item detection, wrapped text continuation, spatial text layout analysis
**Confidence:** HIGH

## Summary

Multi-line item detection in invoice tables requires spatial proximity analysis combined with content-based heuristics to distinguish continuation lines from new line items. Unlike general text reflow detection, invoice line continuation must account for structured column layouts where missing amounts signal continuation rows, while specific start patterns (article numbers, dates, account codes) signal new items.

The established approach for deterministic multi-line detection is:
1. **Spatial proximity** via Y-distance thresholds (typically 1.2-1.5× font height) and X-alignment tolerance (±2-3% of page width or column width)
2. **Amount absence detection** as primary continuation signal: if row lacks VAT% + net amount, it's likely a continuation
3. **Start-pattern matching** to detect new items regardless of spatial proximity: article numbers (`^\w{3,}\d+`, `^\d{5,}`), dates, account codes, individnr patterns
4. **Multi-page table continuation** via repeated header detection or cross-page spatial analysis
5. **Edge case handling** for indented sub-items, bullet points, and footer proximity

**Primary recommendation:** Use Y-distance < 1.5× median line height AND absence of amount as primary continuation signal. Override with start-pattern detection when article numbers, dates, or individnr patterns match. Use X-alignment (±2% page width) as secondary validation, not primary filter.

## Standard Stack

The established libraries/tools for spatial text analysis in PDF line item parsing:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pdfplumber | 0.11.9+ (Jan 2026) | PDF text extraction with character-level positioning | Provides `chars` with `x0`, `y0`, `x1`, `y1`, `size` (font height), `height` attributes; enables Y-distance and X-alignment calculations |
| Decimal (stdlib) | Python 3.8+ | Precise numeric comparisons for spatial thresholds | Essential for consistent threshold calculations (e.g., 0.02 × page_width); avoids float precision issues |
| regex (re stdlib) | Python 3.8+ | Pattern matching for start patterns, amounts, keywords | Standard for detecting article numbers, dates, individnr, account codes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| statistics (stdlib) | Python 3.8+ | Median/mean calculations for adaptive thresholds | Calculate median line height across table for robust Y-distance threshold |
| itertools (stdlib) | Python 3.8+ | Pairwise iteration for row sequence analysis | Compare consecutive rows for Y-distance, X-alignment checks |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fixed Y-distance (e.g., 5pt) | Adaptive threshold (1.5× median line height) | Fixed thresholds break with font size variations; adaptive thresholds handle mixed font sizes |
| X-alignment as primary filter | Amount absence as primary filter | X-alignment can fail with indented sub-items or multi-column descriptions; amount absence is more robust |
| ML-based clustering (DBSCAN, k-means) | Rule-based spatial + content heuristics | ML adds complexity and unpredictability for structured invoice tables; deterministic rules are faster and more maintainable |

**Installation:**
```bash
# No additional dependencies needed beyond Phase 20 stack
# Already have: pdfplumber, Decimal support
```

## Architecture Patterns

### Recommended Project Structure
```
src/pipeline/
├── wrap_detection.py          # Spatial proximity + amount-based detection (existing)
├── start_pattern_matcher.py   # Start-pattern detection for new items (new)
├── multi_page_table.py         # Cross-page table continuation (new)
└── invoice_line_parser.py      # Orchestrates wrap detection + line parsing (existing)
```

### Pattern 1: Y-Distance Threshold with Adaptive Line Height

**What:** Calculate Y-distance threshold dynamically based on median line height rather than using fixed pixel/point values.

**When to use:** Always. Font sizes vary across invoices and even within tables (header rows, subtotal rows may have different sizes).

**Example:**
```python
# Calculate median line height from table rows
def _calculate_adaptive_y_threshold(rows: List[Row]) -> float:
    """Calculate Y-distance threshold as 1.5× median line height."""
    line_heights = []
    for i in range(len(rows) - 1):
        current_row = rows[i]
        next_row = rows[i + 1]
        # Y-distance between consecutive rows
        y_distance = next_row.y_min - current_row.y_max
        if y_distance > 0:  # Skip overlapping rows
            line_heights.append(y_distance)
    
    if not line_heights:
        return 15.0  # Fallback: ~10-12pt font × 1.5
    
    # Median is more robust than mean (avoids skew from section breaks)
    median_height = statistics.median(line_heights)
    
    # Threshold: 1.5× median line height
    # (Based on WCAG 2.1 line spacing guidelines: 1.5× font size)
    return median_height * 1.5

# Use in wrap detection
def detect_wrapped_rows(product_row: Row, following_rows: List[Row], 
                       all_rows: List[Row]) -> List[Row]:
    """Detect wrapped rows using adaptive Y-distance threshold."""
    y_threshold = _calculate_adaptive_y_threshold(all_rows)
    
    wraps = []
    prev_row = product_row
    
    for next_row in following_rows:
        # Y-distance check
        y_distance = next_row.y_min - prev_row.y_max
        if y_distance > y_threshold:
            break  # Too far apart = not a continuation
        
        # Amount absence check (primary signal)
        if _contains_amount(next_row):
            break  # Has amount = new item
        
        # X-alignment check (secondary validation)
        if not _is_x_aligned(product_row, next_row, tolerance=0.02):
            break  # Different column = not a continuation
        
        wraps.append(next_row)
        prev_row = next_row
    
    return wraps
```

**Why this works:** Line height varies with font size. A 10pt font might have 12pt line spacing, while a 14pt font has 16-18pt spacing. Using 1.5× median line height adapts to the actual document layout. The 1.5 factor comes from WCAG accessibility guidelines for readable line spacing.

### Pattern 2: Amount Absence as Primary Continuation Signal

**What:** Treat absence of VAT% + net amount as the primary signal that a row is a continuation line, not a new item.

**When to use:** Always. This is the most reliable signal for invoice tables where every line item must have an amount.

**Example:**
```python
def _is_continuation_row(row: Row) -> bool:
    """Check if row is a continuation (missing amount and VAT%)."""
    # Check for VAT% pattern (25%, 12%, 6% for Swedish invoices)
    vat_pattern = re.compile(r"\b(25|12|6)[.,]00\b")
    if vat_pattern.search(row.text):
        return False  # Has VAT% = likely a line item
    
    # Check for amount pattern
    if _contains_amount(row):
        return False  # Has amount = likely a line item
    
    # No VAT% and no amount = continuation row
    return True

# Enhanced from Phase 20 implementation
def _contains_amount(row: Row) -> bool:
    """Check if row contains a numeric amount (net amount pattern)."""
    # Amount pattern: numbers with decimal (Swedish format)
    amount_pattern = re.compile(r'[\d\s]+[.,]\d{2}')
    
    for token in row.tokens:
        token_text = token.text.strip()
        
        if amount_pattern.search(token_text):
            # Validate it's a valid amount
            cleaned = token_text.replace(',', '.').replace(' ', '')
            try:
                amount = float(cleaned)
                if amount > 0:
                    return True
            except ValueError:
                continue
    
    return False
```

**Why this works:** Invoice line items are structured data where every product/service row must have a price. Continuation lines (wrapped descriptions) never have amounts—they're pure text. This signal is more reliable than spatial analysis alone because:
- Indented sub-items might have large X-deviations but still lack amounts
- Footer rows have amounts but are filtered separately
- Mixed font sizes can cause Y-distance variations, but amount presence is binary

### Pattern 3: Start-Pattern Detection for New Items

**What:** Detect new line items by matching specific start patterns regardless of spatial proximity: article numbers, dates, account codes, individnr.

**When to use:** After spatial proximity suggests continuation. Start patterns override spatial analysis.

**Example:**
```python
# Swedish invoice start patterns
_ARTICLE_NUMBER_PATTERN = re.compile(
    r'^\s*(?:'
    r'\w{3,}\d+|'              # Alphanumeric: ABC123, PROD456
    r'\d{5,}|'                 # Numeric: 12345, 3838969
    r'\d{3,}-\d+|'             # Dash-separated: 123-456
    r'[A-Z]{2,}\d{2,}'         # Uppercase prefix: AB12, XYZ345
    r')',
    re.IGNORECASE
)

_DATE_PATTERN = re.compile(
    r'^\s*(?:'
    r'\d{4}-\d{2}-\d{2}|'      # ISO: 2026-01-26
    r'\d{2}/\d{2}/\d{4}|'      # US: 01/26/2026
    r'\d{2}\.\d{2}\.\d{4}|'    # EU: 26.01.2026
    r'\d{6,8}'                 # Compact: 20260126, 260126
    r')'
)

_INDIVIDNR_PATTERN = re.compile(
    r'^\s*\d{6,8}-\d{4}'       # Swedish personnummer: YYMMDD-XXXX or YYYYMMDD-XXXX
)

_ACCOUNT_CODE_PATTERN = re.compile(
    r'^\s*\d{4,6}'             # Account codes: 4-6 digits at line start
)

def _matches_start_pattern(row: Row) -> bool:
    """Check if row starts with a pattern indicating a new item."""
    text = row.text.strip()
    
    # Article number pattern (highest priority)
    if _ARTICLE_NUMBER_PATTERN.match(text):
        return True
    
    # Date pattern (e.g., "2026-01-15 Service description")
    if _DATE_PATTERN.match(text):
        return True
    
    # Individnr pattern (Swedish personal ID)
    if _INDIVIDNR_PATTERN.match(text):
        return True
    
    # Account code pattern (lower priority, more ambiguous)
    if _ACCOUNT_CODE_PATTERN.match(text):
        # Validate: must have description text after the code
        tokens = row.tokens
        if len(tokens) >= 2:  # Code + description
            return True
    
    return False

# Integrate into wrap detection
def detect_wrapped_rows_with_start_patterns(
    product_row: Row,
    following_rows: List[Row],
    all_rows: List[Row]
) -> List[Row]:
    """Detect wrapped rows with start-pattern override."""
    y_threshold = _calculate_adaptive_y_threshold(all_rows)
    
    wraps = []
    prev_row = product_row
    
    for next_row in following_rows:
        # START-PATTERN CHECK FIRST (override spatial proximity)
        if _matches_start_pattern(next_row):
            break  # New item starts here
        
        # Y-distance check
        y_distance = next_row.y_min - prev_row.y_max
        if y_distance > y_threshold:
            break
        
        # Amount absence check
        if _contains_amount(next_row):
            break
        
        # X-alignment check
        if not _is_x_aligned(product_row, next_row, tolerance=0.02):
            break
        
        wraps.append(next_row)
        prev_row = next_row
    
    return wraps
```

**Why this works:** Some invoices have tightly-spaced items where Y-distance alone would incorrectly group separate items. Article numbers, dates, and account codes are strong signals of new items because:
- Article numbers always start a new item (suppliers use them for inventory tracking)
- Dates indicate service periods or delivery dates (start of item scope)
- Individnr (Swedish personal IDs) are used in personnel/salary invoices (one row per person)
- Account codes in accounting invoices indicate new cost centers

### Pattern 4: X-Alignment Tolerance as Secondary Validation

**What:** Use X-alignment tolerance (±2% of page width or column width) as secondary validation, not primary filter.

**When to use:** After Y-distance and amount checks. X-alignment can have false negatives (indented sub-items, multi-column descriptions).

**Example:**
```python
def _is_x_aligned(
    reference_row: Row,
    test_row: Row,
    tolerance: float = 0.02,
    page_width: Optional[float] = None
) -> bool:
    """Check if test_row is X-aligned with reference_row within tolerance.
    
    Args:
        reference_row: Primary row (line item)
        test_row: Candidate continuation row
        tolerance: Tolerance as fraction of page width (default 2%)
        page_width: Page width for calculating absolute tolerance
    
    Returns:
        True if test_row X-start is within tolerance of reference_row X-start
    """
    # Get description column start (first token's X)
    ref_x = reference_row.tokens[0].x if reference_row.tokens else reference_row.x_min
    test_x = test_row.tokens[0].x if test_row.tokens else test_row.x_min
    
    # Calculate absolute tolerance
    if page_width is not None:
        abs_tolerance = tolerance * page_width
    else:
        # Fallback: use 2% of reference row width or 20pt default
        abs_tolerance = max(0.02 * reference_row.x_max, 20.0)
    
    # Check alignment
    x_deviation = abs(test_x - ref_x)
    
    return x_deviation <= abs_tolerance

# Enhanced logic: allow slight right-indent for sub-descriptions
def _is_x_aligned_with_indent_allowance(
    reference_row: Row,
    test_row: Row,
    page_width: float,
    tolerance: float = 0.02,
    max_indent: float = 0.05  # Allow up to 5% page width indent
) -> bool:
    """X-alignment check allowing slight right-indent for sub-items."""
    ref_x = reference_row.tokens[0].x if reference_row.tokens else reference_row.x_min
    test_x = test_row.tokens[0].x if test_row.tokens else test_row.x_min
    
    abs_tolerance = tolerance * page_width
    max_indent_abs = max_indent * page_width
    
    x_deviation = test_x - ref_x  # Positive = test is to the right
    
    # Allow: same position ±tolerance OR right-indented up to max_indent
    if abs(x_deviation) <= abs_tolerance:
        return True  # Aligned within tolerance
    if 0 < x_deviation <= max_indent_abs:
        return True  # Acceptable right-indent for sub-item
    
    return False  # Too far left or too far right
```

**Why this works:** X-alignment validates that continuation rows belong to the same column as the primary item. However:
- Some invoices use slight indents for multi-line descriptions (aesthetic formatting)
- Bullet points or numbered lists within descriptions have intentional indents
- Using X-alignment as secondary (not primary) prevents false negatives while still catching major column shifts

### Pattern 5: Multi-Page Table Continuation Detection

**What:** Detect when a table continues across page boundaries without repeating headers on each page.

**When to use:** Multi-page invoices where table headers appear only on first page.

**Example:**
```python
def detect_cross_page_continuation(
    pages: List[Page],
    table_start_page: int
) -> List[Tuple[int, int, int]]:
    """Detect table continuation across pages.
    
    Returns:
        List of (page_num, start_row_idx, end_row_idx) tuples for each page segment
    """
    continuations = []
    
    for page_num in range(table_start_page, len(pages)):
        page = pages[page_num]
        rows = page.rows
        
        if page_num == table_start_page:
            # First page: use header detection
            start_idx, end_idx = _find_table_boundaries_first_page(rows)
        else:
            # Continuation page: check for header repetition or use heuristics
            has_repeated_header = _has_table_header(rows)
            
            if has_repeated_header:
                # Header repeated: treat like first page
                start_idx, end_idx = _find_table_boundaries_first_page(rows)
            else:
                # No header: continuation from previous page
                # Start from top, end at footer or page bottom
                start_idx = 0
                end_idx = _find_table_end_footer_only(rows)
        
        if end_idx > start_idx:
            continuations.append((page_num, start_idx, end_idx))
        
        # Check if table ends on this page
        if _table_ends_on_page(rows, end_idx):
            break
    
    return continuations

def _has_table_header(rows: List[Row]) -> bool:
    """Check if page has table header row."""
    for row in rows[:5]:  # Check first 5 rows only
        text_lower = row.text.lower()
        if _is_table_header_row(text_lower):
            return True
    return False

def _find_table_end_footer_only(rows: List[Row]) -> int:
    """Find table end by detecting footer keywords (no header present)."""
    for idx, row in enumerate(rows):
        text_lower = row.text.lower()
        
        # Footer keyword check
        if _TABLE_END_PATTERN.search(text_lower) or _is_footer_row(row):
            return idx
    
    # No footer found: table goes to end of page
    return len(rows)

def _table_ends_on_page(rows: List[Row], end_idx: int) -> bool:
    """Check if table ends on this page (footer present)."""
    if end_idx < len(rows):
        # Found explicit footer = table ends here
        return True
    # Table goes to page bottom = likely continues
    return False
```

**Why this works:** Multi-page tables present two scenarios:
1. **Repeated headers:** Some suppliers repeat column headers on each page (e.g., "Artikelnr | Benämning | Antal | Nettobelopp"). Use same header detection as first page.
2. **No repeated headers:** Table continues seamlessly from previous page. Detect by:
   - Absence of header row at page top
   - Continuation from page top (no blank space)
   - Footer keywords ("Nettobelopp exkl. moms", "Totalt") to detect end
   - Y-coordinate analysis: small Y-distance between last row of page N and first row of page N+1 suggests continuation

### Anti-Patterns to Avoid

- **Using fixed Y-distance thresholds (e.g., 5pt, 10pt):** Fails with variable font sizes. A 10pt font invoice and 14pt font invoice need different thresholds. Use adaptive calculation (1.5× median line height) instead.

- **X-alignment as primary filter:** Fails with indented sub-items, bullet points, or multi-column descriptions where intentional indentation exists. Use amount absence as primary signal, X-alignment as secondary validation.

- **Ignoring start-pattern detection:** Fails when tightly-spaced items (small Y-distance) would be incorrectly grouped. Article numbers, dates, individnr always start new items regardless of spatial proximity.

- **Hardcoding max wrap count (e.g., "max 3 wraps"):** Arbitrary limit. Some items have 5-6 line descriptions (specifications, terms, conditions). Use footer proximity or amount detection as natural stopping condition instead.

- **Assuming all pages have headers:** Multi-page tables often have header only on first page. Check for header repetition before applying first-page logic to continuation pages.

- **Using greedy consolidation:** Continuing to add rows until hitting a stop condition can incorrectly include footer rows or next item's first line. Validate each candidate row individually (Y-distance, amount, start-pattern) rather than batch-collecting.

## Don't Hand-Roll

Problems that look simple but have existing patterns:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Font size extraction from PDF | Custom PDF binary parsing | pdfplumber `chars` with `size` attribute | pdfplumber handles PDF internal font metrics, glyph bounding boxes, rotated text; manual parsing breaks with font embedding, CID fonts, Type3 fonts |
| Y-distance threshold calculation | Fixed pixel value (e.g., 5pt, 10pt) | Adaptive threshold (1.5× median line height) | Fixed thresholds break with font size variations; adaptive calculation matches actual document layout |
| Spatial clustering of text blocks | ML clustering (DBSCAN, k-means) | Rule-based proximity + content heuristics | Invoice tables are structured data with predictable layout; deterministic rules (Y-distance + amount absence + start patterns) are faster, more maintainable, and more explainable than ML |
| Article number pattern matching | Single regex for all formats | Multi-pattern hierarchy with validation | Article number formats vary wildly: alphanumeric (ABC123), numeric (12345), dash-separated (123-456), prefixed (XY-789). Use pattern hierarchy with context validation (must have description after) |
| Multi-page table detection | Position-based (top 30% = header) | Header keyword matching + footer keyword matching | Position-based fails when headers vary in size; keyword matching adapts to different header lengths |

**Key insight:** Multi-line detection is fundamentally a **content + spatial hybrid problem**. Pure spatial analysis (just Y-distance and X-alignment) fails with edge cases. Pure content analysis (just regex patterns) fails with layout variations. The solution combines both: spatial proximity for normal cases, content patterns for override cases.

## Common Pitfalls

### Pitfall 1: Fixed Y-Distance Thresholds Breaking with Font Size Variations

**What goes wrong:** Using fixed pixel/point thresholds (e.g., "Y-distance < 5pt = continuation") breaks when font sizes vary across invoices or within tables.

**Why it happens:** 
- 10pt font typically has ~12pt line spacing (1.2× font size)
- 14pt font typically has ~16-18pt line spacing (1.15-1.3× font size)
- Fixed 5pt threshold works for 10pt font but fails for 14pt font (treats separate items as continuations)

**How to avoid:** Calculate adaptive Y-distance threshold based on median line height of actual table:
```python
# Calculate median line height from consecutive rows
line_heights = [rows[i+1].y_min - rows[i].y_max for i in range(len(rows)-1)]
median_height = statistics.median(line_heights)
y_threshold = median_height * 1.5  # WCAG 1.5× spacing guideline
```

**Warning signs:**
- Separate line items being merged on some invoices but not others
- Multi-line detection working perfectly on test PDFs but failing on production
- Complaints that "items are smashed together" or "descriptions cut off mid-sentence"

### Pitfall 2: Indented Sub-Items Treated as Separate Items

**What goes wrong:** Invoices with indented sub-descriptions (bullet points, numbered lists, specifications) are incorrectly treated as separate line items because X-alignment deviates beyond tolerance.

**Why it happens:** Some suppliers format multi-line descriptions aesthetically:
```
PROD123  Main product description
         • Specification 1
         • Specification 2
         • Specification 3
```
The bullet points are intentionally indented (5-10% page width right), causing X-alignment check to fail.

**How to avoid:** 
1. Use amount absence as **primary** signal (indented sub-items never have amounts)
2. Allow X-alignment tolerance with **right-indent allowance** (±2% normal, +5% for right-indent)
3. Check for bullet point characters (`•`, `–`, `*`, `-`, `1.`, `2.`) at line start as continuation signal

```python
_BULLET_PATTERN = re.compile(r'^\s*[•–\*\-]|\d+\.')

def _is_continuation_with_bullet_check(row: Row) -> bool:
    """Enhanced continuation check allowing bullet points."""
    # Primary: no amount = continuation
    if not _contains_amount(row):
        return True
    
    # Secondary: bullet point pattern suggests sub-item
    if _BULLET_PATTERN.match(row.text):
        return True
    
    return False
```

**Warning signs:**
- Line items with bullet point descriptions split into multiple items
- Descriptions ending mid-sentence, with next item being "• Detail text"
- Line item count much higher than expected (each bullet treated as separate item)

### Pitfall 3: Article Numbers at Start of Continuation Lines

**What goes wrong:** Continuation lines that happen to start with numbers matching article number patterns (e.g., "123 days warranty", "500 units included") are incorrectly treated as new line items.

**Why it happens:** Article number regex (`^\d{3,}`) matches any numeric text at line start, including quantities, measurements, or incidental numbers in descriptions.

**How to avoid:** Validate article number pattern with context:
1. **Length check:** Article numbers are typically 5+ digits; 2-3 digit numbers are likely quantities/measurements
2. **Description presence:** Article numbers must be followed by description text (not just number)
3. **Position in sequence:** Article numbers typically appear at consistent X-positions; outliers are suspicious
4. **Amount presence:** Article number rows always have amounts; no amount = likely not article number

```python
def _is_likely_article_number(row: Row, reference_x: float, tolerance: float) -> bool:
    """Validate if numeric start is likely article number vs incidental number."""
    text = row.text.strip()
    
    # Extract leading number
    match = re.match(r'^(\d+)', text)
    if not match:
        return False
    
    number = match.group(1)
    
    # Length validation: article numbers typically 5+ digits
    if len(number) < 5:
        return False  # Likely quantity or measurement
    
    # Context validation: must have description text after number
    remainder = text[len(number):].strip()
    if len(remainder) < 3:
        return False  # No description = not article number
    
    # Position validation: article numbers at consistent X-position
    row_x = row.tokens[0].x if row.tokens else row.x_min
    if abs(row_x - reference_x) > tolerance:
        return False  # X-position doesn't match article number column
    
    # Amount validation: article number rows have amounts
    if not _contains_amount(row):
        return False  # No amount = likely continuation with incidental number
    
    return True
```

**Warning signs:**
- Line items split at phrases like "24 months warranty", "100 pieces", "365 days support"
- Continuation lines with measurements (dimensions, durations) treated as new items
- Article number column shows suspicious entries like "12", "365", "100" (too short)

### Pitfall 4: Footer Proximity Causing False Wraps

**What goes wrong:** Last line item incorrectly absorbs footer rows as continuation lines because footer rows lack amounts and have small Y-distance.

**Why it happens:** Footer rows like "Summa", "Frakt", "Avgift" immediately follow last item with:
- No amount on footer label row (amount appears on separate row or after colon)
- Small Y-distance (normal table row spacing)
- X-aligned with description column (left-aligned text)

**How to avoid:** Apply footer keyword check **before** wrap detection:
```python
def detect_wrapped_rows_with_footer_guard(
    product_row: Row,
    following_rows: List[Row],
    all_rows: List[Row]
) -> List[Row]:
    """Wrap detection with footer proximity guard."""
    y_threshold = _calculate_adaptive_y_threshold(all_rows)
    
    wraps = []
    prev_row = product_row
    
    for next_row in following_rows:
        # FOOTER CHECK FIRST (before any continuation logic)
        if _is_footer_row(next_row):
            break  # Footer row = stop wrap detection
        
        # Start pattern check
        if _matches_start_pattern(next_row):
            break
        
        # Y-distance check
        y_distance = next_row.y_min - prev_row.y_max
        if y_distance > y_threshold:
            break
        
        # Amount absence check
        if _contains_amount(next_row):
            break
        
        wraps.append(next_row)
        prev_row = next_row
    
    return wraps
```

Also: Detect "large Y-distance gap" before footer as table end signal:
```python
def _has_table_end_gap(prev_row: Row, next_row: Row, median_height: float) -> bool:
    """Check if Y-distance suggests table end (section break before footer)."""
    y_distance = next_row.y_min - prev_row.y_max
    
    # Large gap (2× median) suggests table end
    if y_distance > median_height * 2.0:
        return True
    
    return False
```

**Warning signs:**
- Line items with descriptions ending in "Summa", "Totalt", "Frakt"
- Last line item has absurdly long description including summary text
- Excel export shows merged footer rows in last item description

### Pitfall 5: Mixed Wrapped/Non-Wrapped Items in Same Table

**What goes wrong:** Table contains both single-line items (no wraps) and multi-line items (with wraps), causing inconsistent detection where single-line items incorrectly absorb next item's first line.

**Why it happens:** Detection logic may not properly terminate wrap scanning when next row is actually a new item. Example:
```
Item 1: Short description           100.00 kr
Item 2: Long description line 1
        Long description line 2      200.00 kr
Item 3: Short description            300.00 kr
```
If Item 1's wrap detection looks ahead, it might incorrectly treat "Item 2: Long description line 1" as a continuation because it lacks an amount.

**How to avoid:** Use **look-ahead validation** with start-pattern check:
```python
def detect_wrapped_rows_with_lookahead(
    product_row: Row,
    following_rows: List[Row],
    all_rows: List[Row]
) -> List[Row]:
    """Wrap detection with look-ahead for new item detection."""
    y_threshold = _calculate_adaptive_y_threshold(all_rows)
    
    wraps = []
    prev_row = product_row
    
    for i, next_row in enumerate(following_rows):
        # Footer check
        if _is_footer_row(next_row):
            break
        
        # Start pattern check (primary new-item signal)
        if _matches_start_pattern(next_row):
            break  # Definitive new item
        
        # Y-distance check
        y_distance = next_row.y_min - prev_row.y_max
        if y_distance > y_threshold:
            break
        
        # Amount check
        if _contains_amount(next_row):
            break  # Has amount = new item
        
        # LOOK-AHEAD: Check if next row after this one has amount
        # (Indicates current row is first line of multi-line item, not continuation)
        if i + 1 < len(following_rows):
            row_after = following_rows[i + 1]
            
            # If row after has amount AND small Y-distance to current row,
            # current row is likely first line of new multi-line item
            y_distance_next = row_after.y_min - next_row.y_max
            if _contains_amount(row_after) and y_distance_next <= y_threshold:
                break  # Current row is first line of new item
        
        wraps.append(next_row)
        prev_row = next_row
    
    return wraps
```

**Warning signs:**
- First line of multi-line items merged into previous item
- Line item descriptions containing unrelated product names
- Mismatch between line item count and expected count (fewer items extracted)

### Pitfall 6: Multi-Page Tables with Header Only on First Page

**What goes wrong:** Table continues to page 2+, but header row only appears on page 1. Page 2+ has no header, causing table boundary detection to fail (treats entire page as non-table or misses table start).

**Why it happens:** Current implementation (Phase 20) detects table boundaries per-page using header keyword matching. If page lacks header, `_get_table_block_rows()` returns empty or incorrect boundaries.

**How to avoid:** Implement cross-page table continuation detection:
```python
def extract_multi_page_table_rows(pages: List[Page]) -> List[Row]:
    """Extract table rows across multiple pages."""
    all_table_rows = []
    table_active = False
    
    for page_num, page in enumerate(pages):
        rows = page.rows
        
        # Check for header on this page
        header_idx = _find_table_header(rows)
        
        if header_idx is not None:
            # Header found: start/restart table
            table_active = True
            start_idx = header_idx + 1
        elif table_active:
            # No header but table active from previous page: continuation
            start_idx = 0
        else:
            # No header and table not active: skip page
            continue
        
        # Find table end (footer keywords)
        end_idx = _find_table_footer(rows)
        
        if end_idx is not None:
            # Footer found: table ends on this page
            table_rows = rows[start_idx:end_idx]
            all_table_rows.extend(table_rows)
            table_active = False  # Table complete
            break
        else:
            # No footer: table continues to next page
            table_rows = rows[start_idx:]
            all_table_rows.extend(table_rows)
            # table_active remains True
    
    return all_table_rows
```

**Warning signs:**
- Multi-page invoices only extracting items from page 1
- Page 2+ line items missing from output
- Error logs showing "no table header found" on continuation pages

## Code Examples

Verified patterns from existing implementation and research:

### Adaptive Y-Distance Threshold Calculation

```python
# Source: Research-based pattern (WCAG 1.5× line spacing guideline)
import statistics
from typing import List
from ..models.row import Row

def calculate_adaptive_y_threshold(rows: List[Row]) -> float:
    """Calculate Y-distance threshold based on median line height.
    
    Args:
        rows: List of table rows for analysis
    
    Returns:
        Y-distance threshold (1.5× median line height)
    
    Rationale:
        - WCAG 2.1 recommends 1.5× font size for line spacing
        - Median more robust than mean (avoids skew from section breaks)
        - Adapts to font size variations across invoices
    """
    line_heights = []
    
    for i in range(len(rows) - 1):
        current_row = rows[i]
        next_row = rows[i + 1]
        
        # Y-distance between consecutive rows (vertical spacing)
        y_distance = next_row.y_min - current_row.y_max
        
        if y_distance > 0:  # Skip overlapping rows
            line_heights.append(y_distance)
    
    if not line_heights:
        # Fallback: typical invoice font (10-12pt) × 1.5
        return 15.0
    
    median_height = statistics.median(line_heights)
    
    # Threshold: 1.5× median (accounts for slight variations)
    return median_height * 1.5
```

### Enhanced Wrap Detection with All Signals

```python
# Source: Synthesized from research patterns + Phase 20 implementation
from typing import List, Optional
from ..models.row import Row
from ..models.page import Page

def detect_wrapped_rows_enhanced(
    product_row: Row,
    following_rows: List[Row],
    page: Page,
    all_table_rows: List[Row]
) -> List[Row]:
    """Detect wrapped rows using spatial + content hybrid approach.
    
    Args:
        product_row: Primary line item row
        following_rows: Candidate continuation rows
        page: Page reference for width calculation
        all_table_rows: All table rows for adaptive threshold calculation
    
    Returns:
        List of wrapped continuation rows
    
    Algorithm:
        1. Calculate adaptive Y-threshold (1.5× median line height)
        2. For each following row:
           a. Footer check (stop if footer)
           b. Start-pattern check (stop if article#/date/individnr)
           c. Y-distance check (stop if > threshold)
           d. Amount check (stop if has VAT% + amount)
           e. X-alignment check (stop if deviation > tolerance)
        3. Return collected wraps
    """
    if not following_rows:
        return []
    
    # Step 1: Adaptive Y-threshold
    y_threshold = calculate_adaptive_y_threshold(all_table_rows)
    
    # X-tolerance (2% of page width)
    x_tolerance = 0.02 * page.width
    
    # Reference X-position (description column start)
    ref_x = product_row.tokens[0].x if product_row.tokens else product_row.x_min
    
    wraps = []
    prev_row = product_row
    
    for next_row in following_rows:
        # Step 2a: Footer guard
        if _is_footer_row(next_row):
            break
        
        # Step 2b: Start-pattern detection (override spatial proximity)
        if _matches_start_pattern(next_row):
            break
        
        # Step 2c: Y-distance check
        y_distance = next_row.y_min - prev_row.y_max
        if y_distance > y_threshold:
            break
        
        # Step 2d: Amount check (primary continuation signal)
        if _contains_amount(next_row):
            break
        
        # Step 2e: X-alignment check (secondary validation)
        next_x = next_row.tokens[0].x if next_row.tokens else next_row.x_min
        x_deviation = abs(next_x - ref_x)
        
        # Allow slight right-indent (up to 5% page width) for sub-items
        max_right_indent = 0.05 * page.width
        if x_deviation > x_tolerance:
            # Check if acceptable right-indent
            if next_x - ref_x > max_right_indent or next_x - ref_x < 0:
                break  # Too far left or too far right
        
        # Step 2f: Max wraps safety limit (prevent runaway)
        if len(wraps) >= 10:
            break  # Safety: max 10 continuation lines
        
        # Passed all checks: this is a continuation row
        wraps.append(next_row)
        prev_row = next_row
    
    return wraps
```

### Start-Pattern Detection (Swedish Invoices)

```python
# Source: Research-based patterns for Swedish invoice formats
import re
from ..models.row import Row

# Article number patterns (Swedish formats)
_ARTICLE_PATTERNS = [
    re.compile(r'^\s*[A-Z]{2,}\d{3,}'),        # Uppercase prefix: AB123, XYZ456
    re.compile(r'^\s*\d{5,}'),                 # Numeric: 12345, 3838969
    re.compile(r'^\s*\w{3,}-?\d{2,}'),         # Alphanumeric: PROD-123, ABC456
]

# Date patterns (ISO, Swedish, compact)
_DATE_PATTERN = re.compile(
    r'^\s*(?:'
    r'\d{4}-\d{2}-\d{2}|'      # ISO: 2026-01-26
    r'\d{2}\.\d{2}\.\d{4}|'    # Swedish: 26.01.2026
    r'\d{6,8}'                 # Compact: 20260126
    r')'
)

# Swedish personnummer (individnr)
_INDIVIDNR_PATTERN = re.compile(
    r'^\s*\d{6,8}-\d{4}\b'     # YYMMDD-XXXX or YYYYMMDD-XXXX
)

# Account code patterns
_ACCOUNT_CODE_PATTERN = re.compile(
    r'^\s*\d{4,6}\s+'          # 4-6 digits followed by description
)

def matches_start_pattern(row: Row) -> bool:
    """Check if row matches new item start pattern.
    
    Checks for:
    - Article numbers (various Swedish formats)
    - Dates (ISO, Swedish, compact)
    - Individnr (Swedish personal ID)
    - Account codes (accounting invoices)
    
    Returns:
        True if row starts with new-item pattern, False otherwise
    """
    text = row.text.strip()
    
    if not text:
        return False
    
    # Article number patterns (highest priority)
    for pattern in _ARTICLE_PATTERNS:
        if pattern.match(text):
            # Validation: must have description after article number
            # (prevents matching pure numbers like quantities)
            if len(text) > 8:  # Article# + space + description (min 8 chars)
                return True
    
    # Date pattern (service period, delivery date)
    if _DATE_PATTERN.match(text):
        return True
    
    # Individnr pattern (personnel invoices)
    if _INDIVIDNR_PATTERN.match(text):
        return True
    
    # Account code pattern (accounting invoices)
    if _ACCOUNT_CODE_PATTERN.match(text):
        # Validation: must have text after code
        tokens = row.tokens
        if len(tokens) >= 2:
            return True
    
    return False
```

### Multi-Page Table Continuation

```python
# Source: Research-based pattern for cross-page table handling
from typing import List, Tuple
from ..models.page import Page
from ..models.row import Row

def extract_multi_page_table(
    pages: List[Page]
) -> List[Row]:
    """Extract table rows across multiple pages.
    
    Handles:
    - Tables with header only on first page
    - Tables with repeated headers on each page
    - Footer detection to determine table end
    
    Returns:
        Flat list of all table rows across pages
    """
    all_table_rows = []
    table_active = False
    
    for page_num, page in enumerate(pages):
        rows = page.rows
        
        # Check for table header on this page
        header_idx = None
        for idx, row in enumerate(rows[:10]):  # Check first 10 rows
            if _is_table_header_row(row.text.lower()):
                header_idx = idx
                break
        
        if header_idx is not None:
            # Header found: table starts/restarts here
            table_active = True
            start_idx = header_idx + 1
        elif table_active:
            # No header but table is active: continuation from previous page
            start_idx = 0
        else:
            # No header and table not active: skip this page
            continue
        
        # Find table end on this page (footer keywords)
        end_idx = None
        for idx in range(start_idx, len(rows)):
            row = rows[idx]
            if _is_footer_row(row) or _TABLE_END_PATTERN.search(row.text.lower()):
                end_idx = idx
                break
        
        if end_idx is not None:
            # Footer found: table ends on this page
            page_table_rows = rows[start_idx:end_idx]
            all_table_rows.extend(page_table_rows)
            table_active = False
            break  # Table complete
        else:
            # No footer: table continues to next page
            page_table_rows = rows[start_idx:]
            all_table_rows.extend(page_table_rows)
            # table_active remains True for next page
    
    return all_table_rows

def _is_table_header_row(text_lower: str) -> bool:
    """Detect table header row by keywords."""
    if "nettobelopp" not in text_lower:
        return False
    return any(keyword in text_lower for keyword in 
               ("artikelnr", "artikel", "benämning", "beskrivning"))
```

## State of the Art (2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed Y-distance thresholds (5pt, 10pt) | Adaptive threshold (1.5× median line height) | 2024+ | Handles font size variations; more robust across different invoice formats |
| X-alignment as primary filter | Amount absence as primary, X-alignment as secondary | 2025+ | Correctly handles indented sub-items, bullet points; fewer false negatives |
| Pure spatial proximity (Y-distance + X-alignment only) | Spatial + content hybrid (spatial + start patterns + amount detection) | 2025+ | Handles edge cases: tightly-spaced items, article numbers starting new items regardless of spatial proximity |
| Max wrap count limits (e.g., "max 3 wraps") | Natural stopping conditions (footer proximity, amount detection) | 2025+ | No arbitrary limits; adapts to actual description length |
| Per-page table detection | Cross-page table continuation detection | 2025+ | Correctly handles multi-page invoices with header only on first page |
| Template-based multi-line detection (invoice2data) | Deterministic hybrid rules | 2024+ | No per-supplier templates needed; works across invoice formats |

**New tools/patterns to consider:**
- **Neural table structure recognition (ClusterTabNet, TEXUS):** Emerging ML-based table detection and structure recognition. Useful for complex/irregular tables but overkill for structured invoice tables where deterministic rules suffice. Consider for "AI fallback" path when deterministic fails.
- **Document Intelligence Layout API (Azure):** Provides native cross-page table merging and line grouping. Closed-source, API-based (cost + latency). Consider for cloud-based deployment or when deterministic approach needs validation.
- **pdfplumber font metrics:** pdfplumber 0.11.9+ (Jan 2026) provides `size` attribute for characters, enabling font-size-based threshold calculation. Use for adaptive Y-threshold calculation.

**Deprecated/outdated:**
- **Fixed max wrap counts:** Arbitrary limits like "max 3 continuation lines" from early invoice parsers (2020-2022). Modern approach uses natural stopping conditions.
- **Pure regex-based line grouping:** Early invoice2data templates used pure regex to match multi-line patterns (`(?m)^Item.*\n.*\n.*$`). Fragile with layout variations. Modern approach combines spatial + content analysis.
- **Position-based line grouping (top N%, bottom N%):** Early PDF parsers used positional heuristics. Fails with variable layouts. Modern approach uses keyword anchors and spatial proximity.

## Open Questions

Things that couldn't be fully resolved:

1. **What is the optimal Y-distance threshold multiplier?**
   - What we know: WCAG 2.1 recommends 1.5× font size for line spacing; median line height provides robust baseline
   - What's unclear: Whether 1.5× is optimal for all invoice formats, or if threshold should vary by format (tight-spaced vs loose-spaced)
   - Recommendation: Start with 1.5× median; make configurable per supplier profile if needed (`y_threshold_multiplier: 1.5` in YAML)

2. **How to handle deeply nested sub-items (3+ levels of indentation)?**
   - What we know: Some invoices have hierarchical structures (product → service → sub-service → specification)
   - What's unclear: Whether nested items should be flattened into single description or preserved as structured hierarchy
   - Recommendation: Flatten for Phase 21 (consolidate all levels into single description); consider structured hierarchy in future phase if needed for specific use cases

3. **Should article number patterns be configurable per supplier?**
   - What we know: Article number formats vary widely across suppliers (alphanumeric, numeric, prefixed, dash-separated)
   - What's unclear: Whether universal patterns suffice or if per-supplier customization is needed
   - Recommendation: Start with universal patterns (cover 90% of cases); add supplier-specific patterns to profile YAML if needed (`article_number_pattern: "^ACME-\d{4}"`)

4. **How to handle multi-column descriptions (side-by-side text)?**
   - What we know: Some invoices have wide description columns with text wrapping into pseudo-columns
   - What's unclear: How to detect and merge multi-column text within single description field
   - Recommendation: Out of scope for Phase 21; treat multi-column as single-column with X-alignment tolerance. Consider dedicated multi-column detection in future phase if encountered in production.

5. **What is the maximum reasonable wrap count before flagging as anomaly?**
   - What we know: Most items have 1-5 continuation lines; 10+ lines suggests footer proximity or detection error
   - What's unclear: Whether to hard-limit max wraps or log warning for manual review
   - Recommendation: Implement soft limit (10 lines) with warning log; no hard limit (allow arbitrarily long descriptions but flag for review)

## Sources

### Primary (HIGH confidence)
- **pdfplumber documentation** - https://github.com/jsvine/pdfplumber - Character-level positioning (`chars` with `x0`, `y0`, `size`, `height`), version 0.11.9+ (Jan 2026)
- **WCAG 2.1 Text Spacing (SC 1.4.12)** - https://www.w3.org/WAI/WCAG21/Understanding/text-spacing.html - Line height should be at least 1.5× font size for readability
- **Existing implementation** - `src/pipeline/wrap_detection.py` - Current spatial proximity algorithm (X-tolerance ±2%, max 3 wraps, amount-based stop condition)
- **Phase 20 Research** - `.planning/phases/20-tabellsegment-kolumnregler/20-RESEARCH.md` - VAT%-anchored detection, footer filtering, thousand separator handling

### Secondary (MEDIUM confidence)
- **Microsoft Document Intelligence cross-page tables** - https://techcommunity.microsoft.com/blog/azure-ai-services-blog/a-heuristic-method-of-merging-cross-page-tables-based-on-document-intelligence-l/4118126 - Heuristic approach for merging tables across pages (validates cross-page detection approach)
- **Stack Overflow: pdfplumber font size extraction** - https://stackoverflow.com/questions/68097779 - Confirmed `chars` objects include `size` attribute for font height
- **ClusterTabNet paper** - https://arxiv.org/html/2402.07502v2 - Transformer-based spatial clustering for table structure (validates spatial proximity concepts)
- **invoice2data multi-line handling** - https://stackoverflow.com/questions/59827981 - Community patterns for continuation line detection (validates content-based patterns)

### Tertiary (LOW confidence)
- **WebSearch: Line spacing algorithms** - General articles on paragraph detection (2024-2025) - Concepts only, not authoritative
- **WebSearch: Invoice parsing pitfalls** - Blog posts on multi-line item challenges - Anecdotal evidence, not verified with authoritative sources
- **WebSearch: Swedish invoice formats** - Community discussions on artikelnummer patterns - Patterns derived from examples, not from official standard

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pdfplumber capabilities verified with official docs; stdlib usage is standard practice
- Architecture patterns: HIGH - Patterns synthesized from existing implementation (Phase 20), WCAG standards, and research on spatial text analysis
- Pitfalls: MEDIUM-HIGH - Based on existing implementation experience, web research on common issues, and logical extrapolation of edge cases
- State of the Art: MEDIUM - Web research indicates trends (adaptive thresholds, hybrid spatial+content) but not authoritative sources for "current best practice"

**Research date:** 2026-01-26
**Valid until:** ~90 days (April 2026) for algorithm patterns (stable domain); ~180 days (July 2026) for pdfplumber capabilities (mature library)

**Phase 21 context:** This research builds on Phase 20 (table segmentation, VAT%-anchored amounts, footer filtering) and focuses specifically on multi-line item detection within table boundaries. Phase 20 provides table rows; Phase 21 determines which rows belong together as single items.
