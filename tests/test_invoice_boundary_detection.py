"""Tests for invoice boundary detection."""

from typing import Dict, List, Tuple

from src.models.document import Document
from src.models.page import Page
from src.models.row import Row
from src.models.segment import Segment
from src.models.token import Token
from src.pipeline.invoice_boundary_detection import _find_invoice_boundaries


def _make_rows(page: Page, row_specs: List[Tuple[str, float]]) -> List[Row]:
    rows: List[Row] = []
    for text, y in row_specs:
        token = Token(text=text, x=10.0, y=y, width=200.0, height=12.0, page=page)
        row = Row(
            tokens=[token],
            y=y,
            x_min=token.x,
            x_max=token.x + token.width,
            text=text,
            page=page,
        )
        rows.append(row)
    return rows


def _make_page_segments(doc: Document, page_number: int, row_specs: List[Tuple[str, float]]):
    page = Page(
        page_number=page_number,
        document=doc,
        width=595.0,
        height=842.0,
        tokens=[],
        rendered_image_path=None,
    )
    rows = _make_rows(page, row_specs)
    header_rows = [row for row in rows if row.y < 200]
    segments: List[Segment] = []
    if header_rows:
        segments.append(
            Segment(
                segment_type="header",
                rows=header_rows,
                y_min=min(r.y for r in header_rows),
                y_max=max(r.y for r in header_rows),
                page=page,
            )
        )
    return page, rows, segments


def _build_doc_with_pages(pages_data: List[List[Tuple[str, float]]]) -> Tuple[Document, Dict[int, Tuple[List[Segment], List[Row]]]]:
    doc = Document(
        filename="test.pdf",
        filepath="/path/to/test.pdf",
        page_count=0,
        pages=[],
        metadata={},
    )
    page_segments_map: Dict[int, Tuple[List[Segment], List[Row]]] = {}
    pages: List[Page] = []
    for index, row_specs in enumerate(pages_data, start=1):
        page, rows, segments = _make_page_segments(doc, index, row_specs)
        pages.append(page)
        page_segments_map[index] = (segments, rows)
    doc.pages = pages
    return doc, page_segments_map


def test_two_invoices_two_pages_each():
    doc, page_segments_map = _build_doc_with_pages(
        [
            [("Fakturanr: INV-1001", 60.0)],
            [("Fakturanr: INV-1001", 60.0)],
            [("Fakturanr: INV-2001", 60.0)],
            [("Fakturanr: INV-2001", 60.0)],
        ]
    )

    boundaries = _find_invoice_boundaries(doc, page_segments_map)

    assert boundaries == [(1, 2), (3, 4)]


def test_missing_invoice_number_uses_page_numbers():
    doc, page_segments_map = _build_doc_with_pages(
        [
            [("Fakturanr: INV-1001", 60.0), ("Sida 1/2", 790.0)],
            [("Sida 2/2", 790.0)],
        ]
    )

    boundaries = _find_invoice_boundaries(doc, page_segments_map)

    assert boundaries == [(1, 2)]


def test_conflict_invoice_number_wins_over_page_number():
    doc, page_segments_map = _build_doc_with_pages(
        [
            [("Fakturanr: INV-1001", 60.0), ("Sida 1/2", 790.0)],
            [("Fakturanr: INV-2001", 60.0), ("Sida 2/2", 790.0)],
        ]
    )

    boundaries = _find_invoice_boundaries(doc, page_segments_map)

    assert boundaries == [(1, 1), (2, 2)]


def test_ordernr_not_used_as_invoice_number():
    doc, page_segments_map = _build_doc_with_pages(
        [
            [("Ordernr: 12345", 60.0), ("Sida 1/2", 790.0)],
            [("Ordernr: 12345", 60.0), ("Sida 2/2", 790.0)],
        ]
    )

    boundaries = _find_invoice_boundaries(doc, page_segments_map)

    assert boundaries == [(1, 2)]
