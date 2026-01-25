"""Clickable PDF viewer component with candidate detection and highlighting."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

try:
    import fitz  # pymupdf
except ImportError:
    fitz = None

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPen, QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsRectItem

if TYPE_CHECKING:
    from ...models.traceability import Traceability

logger = logging.getLogger(__name__)


class PDFViewer(QGraphicsView):
    """Clickable PDF viewer with candidate detection and highlighting.
    
    Renders PDF pages using PyMuPDF and supports click detection on
    candidate bounding boxes. Highlights selected candidates visually.
    """
    
    # Signal emitted when candidate is clicked
    candidate_clicked = Signal(int)  # candidate index
    
    def __init__(self, parent=None):
        """Initialize PDF viewer.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        if fitz is None:
            raise ImportError(
                "pymupdf (fitz) is required for PDF viewer. "
                "Install with: pip install pymupdf"
            )
        
        # Scene for rendering
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # PDF document
        self.pdf_doc = None
        self.current_page = None
        self.current_page_number = 1
        
        # Candidates and traceability
        self.candidates: List[Dict] = []
        self.traceability: Optional[Traceability] = None
        
        # Highlighting rectangles
        self.highlight_rects: List[QGraphicsRectItem] = []
        self.selected_candidate_index: Optional[int] = None
        
        # Coordinate mapping
        self.scale_factor = 1.0
        self.page_width = 0.0
        self.page_height = 0.0
        
        # User zoom (relative to fit-to-view); clamped 0.5–4
        self._zoom_level = 1.0
        self._fit_scale = 1.0
        
        # Setup view
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    
    def load_pdf(self, path: str) -> None:
        """Load PDF file and render first page.
        
        Args:
            path: Path to PDF file
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            Exception: If PDF loading fails
        """
        pdf_path = Path(path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        
        try:
            # Open PDF
            self.pdf_doc = fitz.open(str(pdf_path))
            
            if len(self.pdf_doc) == 0:
                raise ValueError("PDF has no pages")
            
            # Render first page
            self.current_page_number = 1
            self._render_page(1)
            
            logger.info(f"Loaded PDF: {path} ({len(self.pdf_doc)} pages)")
            
        except Exception as e:
            logger.error(f"Failed to load PDF {path}: {e}")
            raise
    
    def _render_page(self, page_number: int) -> None:
        """Render PDF page to scene.
        
        Args:
            page_number: Page number (1-indexed)
        """
        if self.pdf_doc is None:
            return
        
        if page_number < 1 or page_number > len(self.pdf_doc):
            logger.warning(f"Invalid page number: {page_number}")
            return
        
        # Clear scene
        self.scene.clear()
        self.highlight_rects.clear()
        
        # Get page (fitz uses 0-indexed)
        fitz_page = self.pdf_doc[page_number - 1]
        self.current_page = fitz_page
        
        # Get page dimensions
        rect = fitz_page.rect
        self.page_width = rect.width
        self.page_height = rect.height
        
        # Render page to pixmap
        # Use reasonable zoom for display (2x for better quality)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = fitz_page.get_pixmap(matrix=mat)
        
        # Convert to QPixmap
        img_data = pix.tobytes("png")
        qpixmap = QPixmap()
        qpixmap.loadFromData(img_data, "PNG")
        
        # Add to scene
        pixmap_item = QGraphicsPixmapItem(qpixmap)
        self.scene.addItem(pixmap_item)
        
        # Calculate scale factor (pixmap size vs page size)
        self.scale_factor = qpixmap.width() / self.page_width
        
        # Fit to view
        self.fitInView(pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._fit_scale = self.transform().m11()
        self._zoom_level = 1.0
        
        # Re-apply highlighting if candidates set
        if self.candidates and self.traceability:
            self._update_highlights()
        
        logger.debug(f"Rendered page {page_number}")
    
    def set_candidates(
        self,
        candidates: List[Dict],
        traceability: Optional[Traceability] = None
    ) -> None:
        """Set candidate list and traceability for highlighting.
        
        Args:
            candidates: List of candidate dicts from InvoiceHeader.total_candidates
                Each dict has: amount, score, row_index, keyword_type
            traceability: Optional Traceability object with bbox information for main candidate
        """
        self.candidates = candidates
        self.traceability = traceability
        
        # Update highlights
        self._update_highlights()
    
    def set_page(self, page_number: int) -> None:
        """Switch to different PDF page.
        
        Args:
            page_number: Page number (1-indexed)
        """
        if self.pdf_doc is None:
            return
        
        self.current_page_number = page_number
        self._render_page(page_number)
    
    def _update_highlights(self) -> None:
        """Update candidate highlighting rectangles."""
        # Clear existing highlights
        for rect in self.highlight_rects:
            self.scene.removeItem(rect)
        self.highlight_rects.clear()
        
        if not self.traceability or not self.candidates:
            return
        
        # Get bbox from traceability evidence
        bbox = self.traceability.evidence.get("bbox")
        if not bbox or len(bbox) != 4:
            return
        
        # Bbox is [x, y, width, height] in PDF coordinates
        pdf_x, pdf_y, pdf_width, pdf_height = bbox
        
        # Convert to pixmap coordinates (account for scale factor)
        pixmap_x = pdf_x * self.scale_factor
        pixmap_y = pdf_y * self.scale_factor
        pixmap_width = pdf_width * self.scale_factor
        pixmap_height = pdf_height * self.scale_factor
        
        # Create highlight rectangle for main candidate (from traceability)
        # This is the currently selected/displayed candidate
        highlight_rect = QGraphicsRectItem(
            pixmap_x, pixmap_y, pixmap_width, pixmap_height
        )
        highlight_rect.setBrush(Qt.BrushStyle.NoBrush)
        # Color and width via QPen (setPen takes a single QPen)
        if self.selected_candidate_index is not None:
            highlight_rect.setPen(QPen(Qt.GlobalColor.blue, 3))
        else:
            highlight_rect.setPen(QPen(Qt.GlobalColor.yellow, 2))
        
        self.scene.addItem(highlight_rect)
        self.highlight_rects.append(highlight_rect)
    
    def highlight_candidate(self, candidate_index: int) -> None:
        """Highlight selected candidate in PDF.
        
        Args:
            candidate_index: Index of candidate to highlight (0-based)
        """
        self.selected_candidate_index = candidate_index
        self._update_highlights()
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse click events for candidate detection.
        
        Args:
            event: Mouse event
        """
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        
        # Get click position in scene coordinates
        scene_pos = self.mapToScene(event.pos())
        
        # Convert to PDF page coordinates
        # Account for viewport transformation
        view_transform = self.transform()
        pdf_x = scene_pos.x() / self.scale_factor
        pdf_y = scene_pos.y() / self.scale_factor
        
        # Check if click is within main candidate's bounding box (from traceability)
        if self.traceability:
            bbox = self.traceability.evidence.get("bbox")
            page_number = self.traceability.evidence.get("page_number", 1)
            
            # Only check if click is on the same page as the candidate
            if page_number == self.current_page_number and bbox and len(bbox) == 4:
                pdf_x_min, pdf_y_min, pdf_width, pdf_height = bbox
                pdf_x_max = pdf_x_min + pdf_width
                pdf_y_max = pdf_y_min + pdf_height
                
                # Check if click is within bbox (with small tolerance for easier clicking)
                tolerance = 5.0  # 5 points tolerance
                if (pdf_x_min - tolerance <= pdf_x <= pdf_x_max + tolerance and
                    pdf_y_min - tolerance <= pdf_y <= pdf_y_max + tolerance):
                    # Click is on the main candidate (from traceability)
                    # Emit signal with index 0 (main candidate)
                    self.candidate_clicked.emit(0)
                    logger.debug(f"Clicked on candidate (main) at PDF coords ({pdf_x:.1f}, {pdf_y:.1f})")
                    return
        
        # If no candidate clicked, pass event to parent
        super().mousePressEvent(event)
    
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom with Ctrl+scroll. Clamp 0.5x–4x relative to fit-to-view."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            step = 1.1 if delta > 0 else 1.0 / 1.1
            new_zoom = self._zoom_level * step
            lo, hi = 0.5, 4.0
            if lo <= new_zoom <= hi:
                self._zoom_level = new_zoom
                self.scale(step, step)
            event.accept()
            return
        super().wheelEvent(event)
    
    def closeEvent(self, event) -> None:
        """Clean up when viewer is closed.
        
        Args:
            event: Close event
        """
        if self.pdf_doc:
            self.pdf_doc.close()
        super().closeEvent(event)
