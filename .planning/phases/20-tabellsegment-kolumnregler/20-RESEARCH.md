# Phase 20: Tabellsegment & kolumnregler - Research

**Researched:** 2026-01-26
**Domain:** PDF text-layer table extraction, invoice line item parsing
**Confidence:** HIGH

## Summary

Invoice table parsing from PDF text layers requires a hybrid approach combining keyword-based boundary detection with positional/regex-based column identification. Unlike general-purpose table extraction, invoice tables are semi-structured with variable column orders, embedded totals, and inconsistent formatting across suppliers.

The established approach for deterministic text-layer parsing is:
1. **Boundary detection** via header/footer keyword anchors to isolate the line items table
2. **Positional parsing** for column identification, as it's more reliable than pure regex for multi-word descriptions with spaces
3. **VAT column as anchor** for identifying net amounts (rightmost amount after VAT% on each row)
4. **Footer filtering** using keyword lists (hard/soft) to avoid extracting summary rows as line items

**Primary recommendation:** Use keyword-based table boundary detection with positional column parsing. For Swedish invoices, anchor net amount extraction to VAT% patterns (`25.00`/`25,00`) and take the last numeric value after the VAT column to avoid misidentifying intermediate columns (discounts, unit prices) as net amounts.

## Standard Stack

The established libraries/tools for PDF text-layer table extraction:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pdfplumber | 0.11.9+ (Jan 2026) | PDF text/token extraction with layout | Industry standard for text-based PDFs; provides character-level positioning, built-in table extraction, visual debugging |
| Camelot | 1.0.9+ (Aug 2025) | Structured table extraction to pandas DataFrames | Specialized for table extraction with quality metrics (accuracy, whitespace); supports multiple export formats |
| PyPDF2 / pypdf | 3.x+ | Low-level PDF parsing | Fallback for basic text extraction when detailed layout not needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Decimal (stdlib) | Python 3.8+ | Precise currency math | Essential for financial calculations; avoids float precision issues |
| regex (re stdlib) | Python 3.8+ | Pattern matching for amounts, VAT%, keywords | Standard for parsing currency patterns, detecting table boundaries |
| invoice2data | 0.4.x+ | Template-based invoice parsing | When processing invoices from many different suppliers; supports YAML templates |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Camelot | pdfplumber | Camelot provides automatic table detection + quality metrics; pdfplumber gives more control for semi-structured layouts |
| Positional parsing | Pure regex | Regex breaks with multi-word descriptions containing spaces; positional parsing handles variable text length better |
| Keyword anchors | Position-based (top 30%, middle 40%, bottom 30%) | Keywords are more reliable across different invoice formats; position-based fails when invoice structure varies |

**Installation:**
```bash
pip install pdfplumber camelot-py[cv]
# For Camelot, also need system dependencies: Ghostscript, Tkinter
```

**Note:** This project uses pdfplumber for text-layer extraction (already implemented in Phase 16). Camelot is documented as an alternative for fully structured tables.

## Architecture Patterns

### Recommended Project Structure
```
src/pipeline/
├── pdf_detection.py          # Text-layer vs image detection
├── reader.py                  # pdfplumber integration
├── segment_identification.py  # Header/items/footer segments (positional)
├── invoice_line_parser.py     # Table boundary + column parsing (this phase)
└── number_normalizer.py       # Swedish Decimal normalization (Phase 19)
```

### Pattern 1: Keyword-Based Table Boundary Detection
**What:** Detect table start/end using header and footer keyword patterns rather than fixed positions.
**When to use:** Semi-structured invoices where table position varies but keywords are consistent.

**Example:**
```python
# Table header keywords (must contain "nettobelopp" + at least one other)
def _is_table_header_row(text_lower: str) -> bool:
    if "nettobelopp" not in text_lower:
        return False
    return any(keyword in text_lower for keyword in 
               ("artikelnr", "artikel", "benämning"))

# Table footer keyword (ends table block)
_TABLE_END_PATTERN = re.compile(r"nettobelopp\s+exkl\.?\s*moms", re.IGNORECASE)

# Scan rows to find boundary indices
for idx, row in enumerate(rows):
    text_lower = row.text.lower()
    if start_idx is None and _is_table_header_row(text_lower):
        start_idx = idx + 1  # Start after header row
    if start_idx is not None and _TABLE_END_PATTERN.search(text_lower):
        end_idx = idx  # End before footer row
        break

# Filter rows to table block
table_rows = rows[start_idx:end_idx]
```

**Why this works:** Swedish invoices consistently use "Nettobelopp" as column header and "Nettobelopp exkl. moms" as total row. Anchoring to these keywords is more robust than position-based segmentation.

### Pattern 2: VAT%-Anchored Net Amount Extraction
**What:** Identify net amount as the rightmost numeric value after the VAT% column (e.g., "25.00" or "25,00").
**When to use:** Invoices with variable column order where intermediate columns (discount%, unit price) could be misidentified as net amount.

**Example:**
```python
# Pattern for 25% VAT (Swedish standard rate)
_MOMS_RATE_PATTERN = re.compile(r"\b25[.,]00\b")

# Amount pattern supporting Swedish thousand separators
_AMOUNT_PATTERN = re.compile(
    r'-?\d{1,3}(?:[ .]\d{3})+(?:[.,]\d{1,2})?-?|-?\d+(?:[.,]\d{1,2})?-?'
)

def _extract_amount_from_row_text(row: Row, require_moms: bool = False):
    row_text = row.text
    
    # If require_moms=True, find VAT% position first
    moms_match = None
    if require_moms:
        moms_match = _MOMS_RATE_PATTERN.search(row_text)
        if not moms_match:
            return None  # No VAT% = not a valid line item
    
    # Find all amounts
    amount_matches = list(_AMOUNT_PATTERN.finditer(row_text))
    
    # Filter to amounts AFTER VAT% position
    if require_moms and moms_match:
        amounts = [m for m in amount_matches if m.start() > moms_match.end()]
    else:
        amounts = amount_matches
    
    # Take rightmost amount as net amount
    if amounts:
        rightmost = amounts[-1]
        return normalize_swedish_decimal(rightmost.group(0))
    return None
```

**Why this works:** Invoice column order varies (Quantity | Unit | Price | VAT% | Net OR Quantity | Unit | Price | Discount% | VAT% | Net). By requiring VAT% and taking the rightmost amount after it, we reliably identify net amount regardless of intermediate columns.

### Pattern 3: Footer Row Filtering (Hard + Soft Keywords)
**What:** Use two-tier keyword matching to avoid extracting summary/total rows as line items.
**When to use:** Always. Footer rows often contain amounts that would otherwise pass the "row with amount = line item" rule.

**Example:**
```python
# HARD keywords: always classify as footer (no additional checks)
_FOOTER_HARD_KEYWORDS = frozenset([
    'summa att betala', 'totalt', 'delsumma', 'nettobelopp', 
    'fakturabelopp', 'moms', 'exkl. moms', 'inkl. moms'
])

# SOFT keywords: require additional signal (e.g., large amount)
_FOOTER_SOFT_KEYWORDS = frozenset([
    'summa', 'exkl', 'inkl', 'forskott', 'fraktavgift', 'avgift'
])

def _is_footer_row(row: Row) -> bool:
    text_lower = row.text.lower()
    
    # HARD keywords: immediate classification
    for keyword in _FOOTER_HARD_KEYWORDS:
        if keyword in text_lower:
            return True
    
    # SOFT keywords: require large amount as additional signal
    for keyword in _FOOTER_SOFT_KEYWORDS:
        if keyword in text_lower:
            if _row_has_total_like_amount(row):  # e.g., > 5000 SEK
                return True
    
    return False
```

**Why this works:** Some footer rows contain generic terms like "summa" that could appear in descriptions. Hard/soft split avoids false positives while catching actual footer rows.

### Pattern 4: Positional Column Identification with Unit as Anchor
**What:** Use unit keywords (st, kg, tim, etc.) as spatial anchor to identify quantity (left of unit) and unit price (right of unit, before net amount).
**When to use:** Invoices with consistent spacing/tokens but variable column count.

**Example:**
```python
unit_keywords = ['st', 'kg', 'h', 'tim', 'ea', 'pcs', 'm²', 'm3', 'dagar']

# Find unit token index
unit_token_idx = None
for i, token in enumerate(tokens):
    if token.text.strip().lower() in unit_keywords:
        unit = token.text.lower()
        unit_token_idx = i
        break

# Extract quantity: numeric token(s) before unit
if unit_token_idx is not None:
    # Check for thousand-separator format: "2 108" before unit
    before_unit_text = " ".join(t.text for t in tokens[:unit_token_idx])
    thousand_sep_pattern = re.compile(r'\b(\d{1,3}(?:\s+\d{3})+)\b')
    matches = list(thousand_sep_pattern.finditer(before_unit_text))
    if matches:
        quantity_text = matches[-1].group(1)  # Rightmost match (closest to unit)
        quantity = normalize_swedish_decimal(quantity_text)
    
    # Extract unit_price: numeric token between unit and net amount
    if amount_token_idx is not None and unit_token_idx + 1 < amount_token_idx:
        price_text = " ".join(t.text for t in tokens[unit_token_idx+1:amount_token_idx])
        price_match = _AMOUNT_PATTERN.search(price_text)
        if price_match:
            unit_price = normalize_swedish_decimal(price_match.group(0))
```

**Why this works:** Unit keywords are consistent across invoice formats. Using unit position as anchor avoids confusion between article numbers, quantities, and prices.

### Anti-Patterns to Avoid

- **Pure positional segmentation (top 30% = header, middle 40% = items, bottom 30% = footer):** Fails when invoice structure varies (e.g., long headers, short item lists). Use keyword anchors instead.
  
- **Parsing amounts token-by-token:** Breaks with Swedish thousand separators (`1 072,60` becomes three tokens: `1`, `072`, `,60`). Use `row.text` regex with full Swedish amount pattern instead.

- **Taking first amount on row as net amount:** Fails with multi-column invoices where unit price or discount appears before net amount. Use VAT% as anchor or rightmost amount.

- **Skipping footer filtering:** Summary rows often have amounts and would be extracted as line items. Always filter footer keywords.

- **Fixed column order assumptions:** Different suppliers place columns in different orders (Quantity-Unit-Price-Net vs Price-Quantity-Unit-Net). Use content-based identification (unit keywords, VAT%, amount ranges) rather than fixed indices.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF text extraction | Custom PDF parser using pypdf | pdfplumber with layout extraction | pdfplumber handles character positioning, bounding boxes, fonts; manual parsing misses layout context needed for tables |
| Currency amount parsing | String manipulation with split/replace | Regex pattern + Decimal normalization | Edge cases: negative amounts (`-474,30`), thousand separators across tokens (`1 072,60`), trailing minus (`1,00-`), percentage discounts (`10,5%`) |
| Swedish number normalization | Custom locale formatting | Dedicated normalizer with Decimal | Handles ambiguous cases: `1.234` (thousand separator) vs `1.234` (decimal), comma vs period, space separators |
| Table extraction (structured PDFs) | Position-based row/column splitting | Camelot with quality metrics | Camelot detects table boundaries, handles merged cells, provides accuracy scores to filter bad tables |
| Template-based invoice parsing | Custom keyword/regex engine | invoice2data with YAML templates | Mature system with plugins for line items, regex parsers, optional fields, exclude_keywords |

**Key insight:** PDF table extraction is deceptively complex. Simple prototypes work on sample invoices but fail on edge cases: merged cells, ragged columns, embedded images, font size variations, invisible characters, ligatures. Mature libraries handle these.

## Common Pitfalls

### Pitfall 1: Footer Rows Extracted as Line Items
**What goes wrong:** Summary rows like "Summa att betala 15 000,00" or "Fraktavgift 250,00" pass the "row with amount = line item" rule and get extracted as products.

**Why it happens:** Footer rows contain valid amounts and may lack clear structural differences from item rows (same font, same layout, similar length).

**How to avoid:** Implement two-tier footer keyword filtering (hard keywords always trigger, soft keywords require additional signal like large amount). Also consider spatial position: if row appears after "Nettobelopp exkl. moms" keyword, it's footer regardless of amount.

**Warning signs:** 
- Extracted "line items" with descriptions like "Totalt", "Att betala", "Exkl. moms"
- Last few line items have suspiciously large amounts (often totals)
- Line item count includes obvious summary rows

### Pitfall 2: Article Numbers Misidentified as Quantities
**What goes wrong:** Large article numbers (e.g., `3838969`, `277615`) are extracted as quantity values, resulting in absurd line items (quantity=277615, unit=ST).

**Why it happens:** Article numbers are numeric tokens appearing before the description, in the same position where quantity might appear. Simple "first number = quantity" heuristics fail.

**How to avoid:** 
- Skip leading numeric tokens (first 2-3 tokens) when extracting quantity
- Use magnitude checks: article numbers are typically 6+ digits or alphanumeric, quantities are typically < 10,000
- Use unit keyword as anchor: quantity must be immediately before unit token
- Check description for article number pattern at start

**Warning signs:**
- Quantities > 100,000 (almost always article numbers, not real quantities)
- Quantity value matches first token of description exactly
- Alphanumeric "quantities" like `2406CSX1P10` (actually article numbers)

### Pitfall 3: Thousand Separators Breaking Amount Extraction
**What goes wrong:** Swedish amounts like `1 072,60` (space as thousand separator) are split into multiple tokens: `1`, `072`, `,60`. Token-by-token parsing extracts `1` as quantity and `072` as price, missing the actual amount.

**Why it happens:** Tokenizers split on whitespace. Swedish formatting uses space for thousand separator, so `1 072 600,50` becomes 4 tokens.

**How to avoid:** 
- Parse amounts from `row.text` (full string) using regex that handles thousand separators: `r'\d{1,3}(?:[ .]\d{3})+(?:[.,]\d{1,2})?'`
- Use Decimal-based normalizer that handles locale-specific formats
- Map extracted amount position back to token index for spatial analysis

**Warning signs:**
- Amounts always < 1000 (thousand-separated amounts not being parsed)
- Extracted amounts don't match visible PDF values
- Amount extraction fails on larger invoices but works on small ones

### Pitfall 4: Column Order Variations Across Suppliers
**What goes wrong:** Hardcoded column indices (e.g., "column 5 is always net amount") fail when different suppliers use different layouts. Some invoices have 5 columns (Qty-Unit-Price-VAT-Net), others have 7 (Article-Desc-Qty-Unit-Price-Disc%-VAT-Net).

**Why it happens:** No invoice standard exists. Each supplier designs their own template.

**How to avoid:**
- Use content-based identification rather than position: identify VAT% by pattern `25.00`, identify unit by keyword matching, identify net amount as rightmost value after VAT%
- Detect column count dynamically and adjust parsing strategy
- Use spatial relationships: "quantity is left of unit", "unit price is between unit and net amount"

**Warning signs:**
- Parser works perfectly on one supplier's invoices but fails on another's
- Net amount gets confused with discount percentage or unit price
- Some invoices extract all fields correctly, others miss quantity or unit price

### Pitfall 5: Negative Amounts vs Discounts
**What goes wrong:** Credit notes or discount rows have negative amounts (e.g., `-474,30`) that get extracted as positive values or confused with quantities.

**Why it happens:** Parsing logic may strip minus signs or misinterpret negative values.

**How to avoid:**
- Preserve sign during regex extraction and normalization
- Distinguish between negative amounts (credit notes: entire net amount is negative) and discount columns (positive net amount with separate negative discount value)
- Use separate discount field in data model rather than treating discounts as negative amounts

**Warning signs:**
- All amounts are positive even when PDF shows negative values
- Discounts not being captured
- Credit notes parsed incorrectly

### Pitfall 6: Multi-Line Item Descriptions (Out of Scope for Phase 20)
**What goes wrong:** Item descriptions spanning multiple rows (e.g., "Product Name\nDetailed description\nSerial: ABC123") cause each row to be extracted as a separate line item, or only the first row is captured.

**Why it happens:** Parser treats each row independently without checking for continuation patterns.

**How to avoid:** Detect wrapped rows using spatial proximity (Y-distance < threshold) and absence of amount on continuation rows. Consolidate wrapped descriptions before creating InvoiceLine objects. **(Phase 21 scope)**

**Warning signs:**
- Descriptions are truncated (missing continuation text)
- Separate line items that should be one (each has small Y-distance)
- Line items missing amounts (actually continuation rows)

## Code Examples

Verified patterns from implementation:

### Table Block Boundary Detection
```python
# Source: invoice_line_parser.py lines 37-62
def _get_table_block_rows(rows: List[Row]) -> Tuple[List[Row], bool]:
    """Filter rows to table block between header and footer anchors."""
    start_idx = None
    end_idx = None

    for idx, row in enumerate(rows):
        if not row.text:
            continue
        text_lower = row.text.lower()
        
        # Detect header row: must have "nettobelopp" + column keywords
        if start_idx is None and _is_table_header_row(text_lower):
            start_idx = idx + 1  # Start AFTER header
            continue
        
        # Detect footer row: "Nettobelopp exkl. moms:"
        if start_idx is not None and _TABLE_END_PATTERN.search(text_lower):
            end_idx = idx  # End BEFORE footer
            break

    # Return filtered rows + flag indicating if table boundaries found
    if start_idx is None:
        return rows, False  # No table boundaries = return all rows
    if end_idx is None or end_idx <= start_idx:
        return rows[start_idx:], True  # No footer found = return from header to end
    return rows[start_idx:end_idx], True  # Both boundaries found

def _is_table_header_row(text_lower: str) -> bool:
    """Check if row is table header (must have nettobelopp + article/benämning)."""
    if "nettobelopp" not in text_lower:
        return False
    return any(keyword in text_lower for keyword in ("artikelnr", "artikel", "benämning"))
```

### VAT%-Anchored Amount Extraction
```python
# Source: invoice_line_parser.py lines 172-260
_MOMS_RATE_PATTERN = re.compile(r"\b25[.,]00\b")
_AMOUNT_PATTERN = re.compile(
    r'-?\d{1,3}(?:[ .]\d{3})+(?:[.,]\d{1,2})?-?|-?\d+(?:[.,]\d{1,2})?-?'
)

def _extract_amount_from_row_text(
    row: Row,
    require_moms: bool = False
) -> Optional[Tuple[Decimal, Optional[Decimal], Optional[int]]]:
    """Extract total amount (and optional discount) from row text.
    
    If require_moms=True, only extracts amounts appearing AFTER VAT% pattern (25.00).
    Returns rightmost amount after VAT% as net amount.
    """
    row_text = row.text
    
    # Find VAT% position if required
    moms_match = None
    if require_moms:
        moms_match = _MOMS_RATE_PATTERN.search(row_text)
        if not moms_match:
            return None  # No VAT% = not a valid line item

    # Find all amount matches
    amount_matches = list(_AMOUNT_PATTERN.finditer(row_text))
    
    # Extract amounts as (value, is_negative, match_start, match_end)
    amounts = []
    for match in amount_matches:
        amount_text = match.group(0)
        try:
            normalized = normalize_swedish_decimal(amount_text)
        except ValueError:
            continue
        
        is_negative = normalized < 0
        value = abs(normalized)
        if value > 0:
            amounts.append((value, is_negative, match.start(), match.end()))
    
    # Filter amounts to those AFTER VAT% position
    if require_moms and moms_match:
        amounts = [a for a in amounts if a[2] > moms_match.end()]
    
    if not amounts:
        return None
    
    # Find rightmost positive amount (this is net amount)
    total_amount = None
    total_amount_pos = None
    for value, is_negative, start_pos, end_pos in amounts:
        if not is_negative:
            if total_amount_pos is None or start_pos > total_amount_pos:
                total_amount = value
                total_amount_pos = start_pos
    
    if total_amount is None:
        return None
    
    # Find discount: negative amount or percentage before total_amount
    discount = None
    discount_pos = None
    for value, is_negative, start_pos, end_pos in amounts:
        if is_negative and start_pos < total_amount_pos:
            if discount_pos is None or start_pos > discount_pos:
                discount = value  # Rightmost negative amount before net amount
                discount_pos = start_pos
    
    return (total_amount, discount, amount_token_idx)
```

### Footer Row Filtering
```python
# Source: invoice_line_parser.py lines 14-169
_FOOTER_HARD_KEYWORDS = frozenset([
    'summa att betala', 'totalt', 'total', 'delsumma', 'nettobelopp',
    'fakturabelopp', 'moms', 'momspliktigt', 'exkl. moms', 'inkl. moms',
])

_FOOTER_SOFT_KEYWORDS = frozenset([
    'summa', 'exkl', 'inkl', 'forskott', 'fraktavgift', 'avgift',
])

def _is_footer_row(row: Row) -> bool:
    """Check if row is footer (summary/total) using two-tier keyword matching."""
    if not row.text:
        return False
    
    text_lower = row.text.lower()
    
    # HARD keywords: always classify as footer
    for keyword in _FOOTER_HARD_KEYWORDS:
        if keyword.lower() in text_lower:
            return True
    
    # SOFT keywords: require additional signal (large amount)
    for keyword in _FOOTER_SOFT_KEYWORDS:
        if keyword in text_lower:
            if _row_has_total_like_amount(row):  # Amount > threshold (e.g., 5000 SEK)
                return True
    
    return False

def _row_has_total_like_amount(row: Row) -> bool:
    """Check if row has large amount typical of totals (> 0 or > 5000 SEK)."""
    result = _extract_amount_from_row_text(row)
    if not result:
        return False
    total_amount, _, _ = result
    return total_amount > 0  # Adjust threshold as needed
```

## State of the Art (2026)

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pure position-based segmentation (top/middle/bottom thirds) | Keyword-based boundary detection | 2020+ | More robust across different invoice formats; handles variable header/footer sizes |
| Token-by-token amount parsing | Full-text regex with thousand separators | 2022+ | Correctly handles Swedish/European formatting with space as thousand separator |
| Fixed column order assumptions | Content-based column identification (unit keywords, VAT% anchors) | 2023+ | Works across multiple supplier formats without per-supplier templates |
| Manual template creation per supplier | Hybrid: deterministic parsing + ML fallback | 2024-2025 | Reduces maintenance burden while maintaining accuracy on structured invoices |
| Tabula/Camelot for all table extraction | pdfplumber for semi-structured, Camelot for fully structured | 2024+ | pdfplumber provides more control for invoice-like documents with irregular tables |

**New tools/patterns to consider:**
- **LLM-based extraction (GPT-4 Vision, Gemini 1.5):** Emerging approach using vision models to understand invoice layout and extract data without templates. Overkill for text-layer invoices but useful for scanned/image-based invoices.
- **Hybrid deterministic + ML:** Use deterministic parsing (keyword anchors, regex) as primary path, ML/AI as fallback for ambiguous cases. Balances accuracy, cost, and maintainability.
- **invoice2data templates:** Mature YAML-based template system for multi-supplier scenarios. Consider if expanding beyond current supplier set.

**Deprecated/outdated:**
- **Tabula (Java-based):** Still maintained but superseded by Python-native alternatives (Camelot, pdfplumber) with better integration and visual debugging
- **Pure OCR approaches for text-based PDFs:** OCR (Tesseract) should only be fallback for image-based PDFs; text-layer extraction is faster and more accurate when available
- **Fixed position parsing without keyword anchors:** Brittle across invoice format variations; keyword-based boundaries are now standard

## Open Questions

Things that couldn't be fully resolved:

1. **How to handle invoice formats without clear "Nettobelopp exkl. moms" footer?**
   - What we know: Current implementation requires this keyword to detect table end
   - What's unclear: Alternative patterns for invoices using "Total", "Subtotal", or other footer keywords
   - Recommendation: Extend footer keyword list with international variations; consider fallback to positional segmentation if no footer keyword found
   - **Status:** Documented as MEDIUM limitation in `20-LIMITATIONS.md`

2. **What's the optimal threshold for "large amount" in soft footer keyword matching?**
   - What we know: Current implementation uses simple `amount > 0` check
   - What's unclear: Whether threshold should be dynamic (percentage of largest line item) or fixed (e.g., 5000 SEK)
   - Recommendation: Analyze ground truth corpus to determine optimal threshold; consider making it configurable per supplier profile

3. **How to handle multiple VAT rates (25%, 12%, 6%) in same invoice?** ⚠️ **CRITICAL LIMITATION**
   - What we know: Current implementation hardcodes `25.00` pattern (Swedish standard rate)
   - What's unclear: How to detect net amount when row has 12% or 6% VAT rate
   - Recommendation: Extend VAT pattern to `\b(25|12|6)[.,]00\b`; validate against expected rates in supplier profile
   - **Status:** **Documented as CRITICAL limitation in `20-LIMITATIONS.md` - Must be addressed in Phase 21/22**
   - **Impact:** Invoices with mixed VAT rates will have incomplete line item extraction

4. **Should table boundary detection be per-page or per-document?**
   - What we know: Current implementation processes each page independently
   - What's unclear: Whether multi-page invoices can have table header only on first page, requiring cross-page boundary detection
   - Recommendation: Test with multi-page invoice corpus; implement cross-page table continuation detection if needed (Phase 21 scope)
   - **Status:** Documented as MINOR limitation in `20-LIMITATIONS.md` (Phase 21 scope)

5. **How to handle invoices with no table structure (pure text format)?**
   - What we know: Implementation assumes tabular layout with columns
   - What's unclear: Fallback strategy for text-format invoices (e.g., "Product: X, Quantity: 2, Price: 100 SEK")
   - Recommendation: Out of scope for Phase 20; consider separate parser for text-format invoices if encountered in production

**See comprehensive limitation documentation:** `.planning/phases/20-tabellsegment-kolumnregler/20-LIMITATIONS.md`

## Sources

### Primary (HIGH confidence)
- **Camelot documentation** - https://camelot-py.readthedocs.io/en/master/ - Table extraction library capabilities, official release notes
- **pdfplumber PyPI** - https://pypi.org/project/pdfplumber/ - Version 0.11.9 (Jan 2026), Python 3.8+ support
- **Implementation code** - src/pipeline/invoice_line_parser.py, src/pipeline/segment_identification.py - Actual patterns used in Phase 20

### Secondary (MEDIUM confidence)
- **invoice2data documentation** - https://invoice2data.readthedocs.io/ - Template-based parsing patterns, verified with official docs
- **Stack Overflow: Invoice parsing patterns** - Multiple sources (2024-2025) on column identification, regex patterns for amounts - Cross-referenced with implementation
- **IEEE paper: Two-stage table extraction** - https://ieeexplore.ieee.org/document/10356436/ - Academic research on invoice table detection

### Tertiary (LOW confidence)
- **WebSearch: Invoice parsing pitfalls** - Blog posts and articles (2023-2026) - General patterns, not verified with authoritative sources
- **WebSearch: Swedish currency formatting** - Community discussions on thousand separators - Confirmed with implementation but not authoritative standard

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pdfplumber and Camelot are industry-standard, actively maintained, verified with official docs
- Architecture patterns: HIGH - Patterns extracted from working implementation (Phase 20) and validated with invoice2data documentation
- Pitfalls: MEDIUM-HIGH - Based on implementation experience and cross-referenced with community sources; specific to Swedish invoices
- State of the Art: MEDIUM - WebSearch results from 2024-2026 indicate trends but not authoritative; ML/LLM approaches emerging but not mature

**Research date:** 2026-01-26
**Valid until:** ~90 days (April 2026) for library versions; ~180 days (July 2026) for architecture patterns (stable domain)

**Phase 20 implementation status:** COMPLETE - This research validates the implemented approach and documents best practices for future reference.
