---
phase: 18
title: Fakturaboundaries for multi-page PDFs
status: passed
---

# Verifiering: Phase 18 – Fakturaboundaries

## Status
passed

## Must-haves
- BOUND-01: Fakturor segmenteras genom att läsa fakturanummer per sida och groupby `invoice_no`.
- BOUND-02: Sidnummer (“Sida 1/2”, “Sida 2/2”) används som hjälp för att samla sidor per faktura.
- BOUND-03: Segmentering ska inte bero på “total found”.

## Evidens
- Fakturanummer per sida används för boundary-beslut och nya grupper vid ändring. `invoice_no` väljs per sida via kandidatlogik och används i beslutsträdet. ```178:239:src/pipeline/invoice_boundary_detection.py
        invoice_candidate = _select_invoice_number_candidate(rows, page, header_segment)
        page_number_info = _parse_page_number(rows)

        if invoice_candidate:
            invoice_no = invoice_candidate["candidate"]
            if current_invoice_no is None:
                current_invoice_no = invoice_no
                reasons.append("invoice_no_detected")
            elif invoice_no != current_invoice_no:
                if current_start <= page_num - 1:
                    boundaries.append((current_start, page_num - 1))
                current_start = page_num
                current_invoice_no = invoice_no
                decision = "new_invoice"
                reasons.append("invoice_no_change")
            else:
                reasons.append("invoice_no_match")
```
- Sidnummer parseras och används när fakturanummer saknas, inklusive sekventiell kontinuitet. ```413:462:src/pipeline/invoice_boundary_detection.py
def _parse_page_number(rows: List[Row]) -> Optional[Dict[str, Any]]:
    """Parse page numbering like 'Sida 1/2', 'Sida 2 av 3', 'Page 1/2', or '1/2'."""
    if not rows:
        return None
    label_re = re.compile(r"\b(?:sida|page)\s*(\d{1,3})\s*(?:/|av)\s*(\d{1,3})\b", re.IGNORECASE)
    fraction_re = re.compile(r"\b(\d{1,3})\s*/\s*(\d{1,3})\b")
    # ...
    return None

def _is_page_number_sequential(prev_info: Dict[str, Any], current_info: Dict[str, Any]) -> bool:
    """Check if page numbering is sequential without jumps."""
    # ...
    return True
```
- Beslutslogiken använder endast fakturanummer och sidnummer; ingen “total found”-logik i boundary-funktionen. ```148:239:src/pipeline/invoice_boundary_detection.py
def _find_invoice_boundaries(
    doc: Document,
    page_segments_map: dict,  # page_number -> (segments, rows)
    verbose: bool = False,
    decision_log: Optional[List[Dict[str, Any]]] = None,
) -> List[Tuple[int, int]]:
    """Find invoice boundaries by analyzing invoice number and page numbering."""
    # ... ingen total-detektion används i beslutsträdet ...
```
- Compare-path logging för boundary-beslut i CLI finns. ```1068:1092:src/cli/main.py
        boundary_decisions = [] if (compare_extraction and verbose) else None
        boundaries = detect_invoice_boundaries(
            doc,
            extraction_path,
            verbose,
            output_dir=output_dir,
            decision_log=boundary_decisions
        )
        if boundary_decisions is not None:
            print("  Boundary decisions (compare-path):")
            for entry in boundary_decisions:
                # ...
                print(f"    - Page {entry.get('page')}: {entry.get('decision')} ({info}; {reasons})")
```
- Tester täcker multi-invoice, sidnummer-fallback, konflikt där fakturanummer vinner och falsk kandidat. ```72:123:tests/test_invoice_boundary_detection.py
def test_two_invoices_two_pages_each():
    # ...
    assert boundaries == [(1, 2), (3, 4)]

def test_missing_invoice_number_uses_page_numbers():
    # ...
    assert boundaries == [(1, 2)]

def test_conflict_invoice_number_wins_over_page_number():
    # ...
    assert boundaries == [(1, 1), (2, 2)]

def test_ordernr_not_used_as_invoice_number():
    # ...
    assert boundaries == [(1, 2)]
```
