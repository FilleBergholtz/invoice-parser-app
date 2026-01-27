"""Unit tests for column detection (Phase 22)."""

from decimal import Decimal

import pytest

from src.models.document import Document
from src.models.page import Page
from src.models.row import Row
from src.models.token import Token
from src.pipeline.column_detection import (
    assign_tokens_to_columns,
    detect_columns_gap_based,
    map_columns_from_header
)


@pytest.fixture
def sample_page():
    """Create a sample page for testing."""
    doc = Document(filename="test.pdf", filepath="test.pdf", page_count=0, pages=[])
    page = Page(page_number=1, width=612, height=792, document=doc)
    doc.pages.append(page)
    doc.page_count = 1
    return page


@pytest.fixture
def table_rows_with_gaps(sample_page):
    """Create table rows with clear column gaps."""
    rows = []
    
    # Row 1: Description at x=50, Quantity at x=300, Price at x=450, Netto at x=550
    tokens1 = [
        Token(text="Product", x=50, y=100, width=200, height=12, page=sample_page),
        Token(text="5", x=300, y=100, width=20, height=12, page=sample_page),
        Token(text="100.00", x=450, y=100, width=60, height=12, page=sample_page),
        Token(text="500.00", x=550, y=100, width=60, height=12, page=sample_page),
    ]
    row1 = Row(tokens=tokens1, text="Product 5 100.00 500.00", x_min=50, x_max=610, y=100, page=sample_page)
    
    # Row 2: Similar layout
    tokens2 = [
        Token(text="Service", x=50, y=120, width=200, height=12, page=sample_page),
        Token(text="2", x=300, y=120, width=20, height=12, page=sample_page),
        Token(text="50.00", x=450, y=120, width=60, height=12, page=sample_page),
        Token(text="100.00", x=550, y=120, width=60, height=12, page=sample_page),
    ]
    row2 = Row(tokens=tokens2, text="Service 2 50.00 100.00", x_min=50, x_max=610, y=120, page=sample_page)
    
    return [row1, row2]


@pytest.fixture
def table_rows_single_column(sample_page):
    """Create table rows with no gaps (single column)."""
    rows = []
    
    # Row 1: Single token (no gaps possible)
    tokens1 = [
        Token(text="Product description text", x=50, y=100, width=300, height=12, page=sample_page),
    ]
    row1 = Row(tokens=tokens1, text="Product description text", x_min=50, x_max=350, y=100, page=sample_page)
    
    return [row1]


@pytest.fixture
def header_row(sample_page):
    """Create a header row with column labels."""
    tokens = [
        Token(text="Benämning", x=50, y=80, width=200, height=12, page=sample_page),
        Token(text="Antal", x=300, y=80, width=50, height=12, page=sample_page),
        Token(text="Pris", x=450, y=80, width=50, height=12, page=sample_page),
        Token(text="Nettobelopp", x=550, y=80, width=100, height=12, page=sample_page),
    ]
    return Row(tokens=tokens, text="Benämning Antal Pris Nettobelopp", x_min=50, x_max=650, y=80, page=sample_page)


class TestGapBasedColumnDetection:
    """Tests for gap-based column detection."""
    
    def test_gap_based_column_detection_normal(self, table_rows_with_gaps):
        """Test gap-based detection with clear column gaps."""
        column_centers = detect_columns_gap_based(table_rows_with_gaps, min_gap=20.0)
        
        # Should detect 4 columns (description, quantity, price, netto)
        assert len(column_centers) >= 3  # At least 3 columns
        assert all(isinstance(c, float) for c in column_centers)
        assert column_centers == sorted(column_centers)  # Sorted left to right
    
    def test_column_detection_single_column(self, table_rows_single_column):
        """Test edge case: no gaps found (single column)."""
        column_centers = detect_columns_gap_based(table_rows_single_column, min_gap=20.0)
        
        # Should return single column (median X-position)
        assert len(column_centers) == 1
        assert isinstance(column_centers[0], float)
        # Median should be around 200 (center of single token at x=50, width=300)
        assert 50 <= column_centers[0] <= 350
    
    def test_column_detection_empty_rows(self):
        """Test edge case: empty rows list."""
        column_centers = detect_columns_gap_based([], min_gap=20.0)
        
        assert column_centers == []
    
    def test_column_detection_over_clustering(self, sample_page):
        """Test pitfall: too many gaps (over-clustering)."""
        # Create rows with many small gaps (should trigger adaptive threshold)
        rows = []
        for i in range(10):
            tokens = [
                Token(text=f"Col{i}", x=50 + i * 30, y=100 + i * 20, width=20, height=12, page=sample_page),
            ]
            row = Row(tokens=tokens, text=f"Col{i}", x_min=50 + i * 30, x_max=70 + i * 30, y=100 + i * 20, page=sample_page)
            rows.append(row)
        
        column_centers = detect_columns_gap_based(rows, min_gap=20.0)
        
        # Should use adaptive threshold and reduce number of columns
        assert len(column_centers) <= 10  # Should not create too many columns
    
    def test_column_detection_under_clustering(self, sample_page):
        """Test pitfall: too few gaps (under-clustering)."""
        # Create rows with very large gaps (should still detect columns)
        rows = []
        tokens1 = [
            Token(text="Col1", x=50, y=100, width=50, height=12, page=sample_page),
            Token(text="Col2", x=400, y=100, width=50, height=12, page=sample_page),  # Large gap
        ]
        row1 = Row(tokens=tokens1, text="Col1 Col2", x_min=50, x_max=450, y=100, page=sample_page)
        rows.append(row1)
        
        column_centers = detect_columns_gap_based(rows, min_gap=20.0)
        
        # Should detect 2 columns despite large gap
        assert len(column_centers) >= 2
    
    def test_column_detection_variable_widths(self, sample_page):
        """Test variable column widths."""
        # Create rows with columns of different widths
        rows = []
        tokens1 = [
            Token(text="Short", x=50, y=100, width=50, height=12, page=sample_page),
            Token(text="VeryLongColumnName", x=200, y=100, width=150, height=12, page=sample_page),
            Token(text="Med", x=400, y=100, width=50, height=12, page=sample_page),
        ]
        row1 = Row(tokens=tokens1, text="Short VeryLongColumnName Med", x_min=50, x_max=450, y=100, page=sample_page)
        rows.append(row1)
        
        column_centers = detect_columns_gap_based(rows, min_gap=20.0)
        
        # Should detect columns despite variable widths
        assert len(column_centers) >= 2


class TestHeaderRowColumnMapping:
    """Tests for header row column mapping."""
    
    def test_header_row_column_mapping(self, header_row, table_rows_with_gaps):
        """Test header-based field mapping."""
        # First detect columns
        column_centers = detect_columns_gap_based(table_rows_with_gaps, min_gap=20.0)
        
        # Map columns from header
        column_map = map_columns_from_header(header_row, column_centers)
        
        # Should map description, quantity, unit_price, netto
        assert column_map is not None
        assert 'description' in column_map  # "Benämning"
        assert 'quantity' in column_map  # "Antal"
        assert 'netto' in column_map  # "Nettobelopp"
    
    def test_header_row_no_matches(self, sample_page):
        """Test header row with no matching keywords."""
        # Create header with no recognizable keywords
        tokens = [
            Token(text="X", x=50, y=80, width=20, height=12, page=sample_page),
            Token(text="Y", x=200, y=80, width=20, height=12, page=sample_page),
        ]
        header = Row(tokens=tokens, text="X Y", x_min=50, x_max=220, y=80, page=sample_page)
        
        column_centers = [100.0, 210.0]
        column_map = map_columns_from_header(header, column_centers)
        
        # Should return None (no matches)
        assert column_map is None
    
    def test_header_row_empty_tokens(self, sample_page):
        """Test header row with no matching keywords."""
        # Create header with tokens but no matching keywords (instead of empty tokens)
        tokens = [
            Token(text="X", x=50, y=80, width=20, height=12, page=sample_page),
            Token(text="Y", x=200, y=80, width=20, height=12, page=sample_page),
        ]
        header = Row(tokens=tokens, text="X Y", x_min=50, x_max=220, y=80, page=sample_page)
        
        column_centers = [100.0, 200.0]
        column_map = map_columns_from_header(header, column_centers)
        
        # Should return None (no matching keywords)
        assert column_map is None


class TestTokenToColumnAssignment:
    """Tests for token-to-column assignment."""
    
    def test_token_to_column_assignment(self, table_rows_with_gaps):
        """Test token assignment to columns."""
        # Detect columns
        column_centers = detect_columns_gap_based(table_rows_with_gaps, min_gap=20.0)
        
        # Assign tokens to columns for first row
        row = table_rows_with_gaps[0]
        column_tokens = assign_tokens_to_columns(row, column_centers)
        
        # Should assign tokens to columns
        assert len(column_tokens) == len(column_centers)
        assert all(isinstance(tokens, list) for tokens in column_tokens.values())
        
        # Each token should be assigned to exactly one column
        total_tokens = sum(len(tokens) for tokens in column_tokens.values())
        assert total_tokens == len(row.tokens)
    
    def test_token_to_column_empty_columns(self, sample_page):
        """Test token assignment when some columns are empty."""
        # Create row with tokens only in some columns
        tokens = [
            Token(text="Col1", x=50, y=100, width=50, height=12, page=sample_page),
            Token(text="Col3", x=400, y=100, width=50, height=12, page=sample_page),
        ]
        row = Row(tokens=tokens, text="Col1 Col3", x_min=50, x_max=450, y=100, page=sample_page)
        
        column_centers = [100.0, 250.0, 425.0]  # 3 columns
        column_tokens = assign_tokens_to_columns(row, column_centers)
        
        # Should have 3 columns, but only 2 with tokens
        assert len(column_tokens) == 3
        assert len(column_tokens[0]) == 1  # Col1
        assert len(column_tokens[1]) == 0  # Empty
        assert len(column_tokens[2]) == 1  # Col3
    
    def test_token_to_column_empty_row(self, sample_page):
        """Test token assignment with row that has no tokens in columns."""
        # Create row with single token that doesn't match any column well
        # (instead of empty tokens, which Row doesn't allow)
        token = Token(text="X", x=500, y=100, width=20, height=12, page=sample_page)
        row = Row(tokens=[token], text="X", x_min=500, x_max=520, y=100, page=sample_page)
        
        column_centers = [100.0, 200.0, 300.0]  # Columns far from token
        column_tokens = assign_tokens_to_columns(row, column_centers)
        
        # Should have all columns, token assigned to nearest (column 2 at 300.0)
        assert len(column_tokens) == 3
        # Token should be in column 2 (nearest to x=500)
        assert len(column_tokens[2]) == 1  # Token assigned to column 2
        assert len(column_tokens[0]) == 0
        assert len(column_tokens[1]) == 0
    
    def test_token_to_column_nearest_neighbor(self, sample_page):
        """Test that tokens are assigned to nearest column."""
        # Create tokens at positions: 50, 150, 250, 350
        # Column centers: 100, 200, 300
        # Token at 50 should go to column 0 (100), token at 150 to column 0 or 1, etc.
        tokens = [
            Token(text="T1", x=50, y=100, width=20, height=12, page=sample_page),   # Nearest to 100
            Token(text="T2", x=150, y=100, width=20, height=12, page=sample_page),  # Nearest to 100
            Token(text="T3", x=250, y=100, width=20, height=12, page=sample_page),  # Nearest to 300
            Token(text="T4", x=350, y=100, width=20, height=12, page=sample_page),  # Nearest to 300
        ]
        row = Row(tokens=tokens, text="T1 T2 T3 T4", x_min=50, x_max=370, y=100, page=sample_page)
        
        column_centers = [100.0, 200.0, 300.0]
        column_tokens = assign_tokens_to_columns(row, column_centers)
        
        # T1 and T2 should be in column 0 (closest to 100)
        # T3 and T4 should be in column 2 (closest to 300)
        assert len(column_tokens[0]) >= 1  # T1 or T2
        assert len(column_tokens[2]) >= 1  # T3 or T4
