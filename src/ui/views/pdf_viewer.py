"""Clickable PDF viewer component with candidate detection, highlighting, and viewer toolbar."""

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
from PySide6.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QToolBar,
    QSizePolicy,
)

if TYPE_CHECKING:
    from ...models.traceability import Traceability

logger = logging.getLogger(__name__)


class _PDFGraphicsView(QGraphicsView):
    """Internal graphics view for PDF rendering, zoom, and candidate clicks."""

    candidate_clicked = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        if fitz is None:
            raise ImportError(
                "pymupdf (fitz) is required for PDF viewer. "
                "Install with: pip install pymupdf"
            )
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.pdf_doc = None
        self.current_page = None
        self.current_page_number = 1
        self.candidates: List[Dict] = []
        self.traceability: Optional[Traceability] = None
        self.highlight_rects: List[QGraphicsRectItem] = []
        self.selected_candidate_index: Optional[int] = None
        self.scale_factor = 1.0
        self.page_width = 0.0
        self.page_height = 0.0
        self._zoom_level = 1.0
        self._fit_scale = 1.0
        self._pixmap_item: Optional[QGraphicsPixmapItem] = None

        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    @property
    def page_count(self) -> int:
        return len(self.pdf_doc) if self.pdf_doc else 0

    def load_pdf(self, path: str) -> None:
        pdf_path = Path(path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {path}")
        self.pdf_doc = fitz.open(str(pdf_path))
        if len(self.pdf_doc) == 0:
            raise ValueError("PDF has no pages")
        self.current_page_number = 1
        self._render_page(1)
        logger.info(f"Loaded PDF: {path} ({len(self.pdf_doc)} pages)")

    def _render_page(self, page_number: int) -> None:
        if self.pdf_doc is None or page_number < 1 or page_number > len(self.pdf_doc):
            return
        self.scene.clear()
        self.highlight_rects.clear()
        fitz_page = self.pdf_doc[page_number - 1]
        self.current_page = fitz_page
        rect = fitz_page.rect
        self.page_width = rect.width
        self.page_height = rect.height
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = fitz_page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        qpixmap = QPixmap()
        qpixmap.loadFromData(img_data, "PNG")
        self._pixmap_item = QGraphicsPixmapItem(qpixmap)
        self._scene.addItem(self._pixmap_item)
        self.scale_factor = qpixmap.width() / self.page_width
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._fit_scale = self.transform().m11()
        self._zoom_level = 1.0
        if self.candidates and self.traceability:
            self._update_highlights()
        logger.debug(f"Rendered page {page_number}")

    def set_candidates(
        self,
        candidates: List[Dict],
        traceability: Optional[Traceability] = None,
    ) -> None:
        self.candidates = candidates
        self.traceability = traceability
        self._update_highlights()

    def set_page(self, page_number: int) -> None:
        if self.pdf_doc is None:
            return
        self.current_page_number = max(1, min(page_number, len(self.pdf_doc)))
        self._render_page(self.current_page_number)

    def _update_highlights(self) -> None:
        for r in self.highlight_rects:
            self._scene.removeItem(r)
        self.highlight_rects.clear()
        if not self.traceability or not self.candidates:
            return
        bbox = self.traceability.evidence.get("bbox")
        if not bbox or len(bbox) != 4:
            return
        pdf_x, pdf_y, pdf_width, pdf_height = bbox
        sx, sy = self.scale_factor, self.scale_factor
        hr = QGraphicsRectItem(
            pdf_x * sx, pdf_y * sy, pdf_width * sx, pdf_height * sy
        )
        hr.setBrush(Qt.BrushStyle.NoBrush)
        hr.setPen(
            QPen(Qt.GlobalColor.blue, 3)
            if self.selected_candidate_index is not None
            else QPen(Qt.GlobalColor.yellow, 2)
        )
        self.scene.addItem(hr)
        self.highlight_rects.append(hr)

    def highlight_candidate(self, candidate_index: int) -> None:
        self.selected_candidate_index = candidate_index
        self._update_highlights()

    def zoom_in(self) -> None:
        step = 1.2
        new_zoom = self._zoom_level * step
        if new_zoom <= 4.0:
            self._zoom_level = new_zoom
            self.scale(step, step)

    def zoom_out(self) -> None:
        step = 1.0 / 1.2
        new_zoom = self._zoom_level * step
        if new_zoom >= 0.5:
            self._zoom_level = new_zoom
            self.scale(step, step)

    def fit_to_width(self) -> None:
        item = self._pixmap_item
        if item is None:
            items = [i for i in self._scene.items() if isinstance(i, QGraphicsPixmapItem)]
            item = items[0] if items else None
        if item is not None:
            r = item.boundingRect()
            if r.width() > 0:
                scale = self.viewport().width() / r.width()
                self.resetTransform()
                self.scale(scale, scale)
                self._fit_scale = scale
                self._zoom_level = 1.0
                if self.candidates and self.traceability:
                    self._update_highlights()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        scene_pos = self.mapToScene(event.pos())
        pdf_x = scene_pos.x() / self.scale_factor
        pdf_y = scene_pos.y() / self.scale_factor
        if self.traceability:
            bbox = self.traceability.evidence.get("bbox")
            pn = self.traceability.evidence.get("page_number", 1)
            if pn == self.current_page_number and bbox and len(bbox) == 4:
                x0, y0, w, h = bbox
                tol = 5.0
                if x0 - tol <= pdf_x <= x0 + w + tol and y0 - tol <= pdf_y <= y0 + h + tol:
                    self.candidate_clicked.emit(0)
                    return
        super().mousePressEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            step = 1.1 if delta > 0 else 1.0 / 1.1
            new_zoom = self._zoom_level * step
            if 0.5 <= new_zoom <= 4.0:
                self._zoom_level = new_zoom
                self.scale(step, step)
            event.accept()
            return
        super().wheelEvent(event)

    def closeEvent(self, event) -> None:
        if self.pdf_doc:
            self.pdf_doc.close()
        super().closeEvent(event)


class PDFViewer(QWidget):
    """PDF viewer with toolbar (zoom, fit width, prev/next page, page indicator).

    Wraps _PDFGraphicsView and adds a viewer toolbar. Styled via app theme (setObjectName).
    """

    candidate_clicked = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QToolBar()
        toolbar.setObjectName("pdf_viewer_toolbar")
        toolbar.setContentsMargins(2, 2, 2, 2)

        zoom_in_btn = QPushButton("Zooma in")
        zoom_in_btn.setObjectName("pdf_zoom_in")
        zoom_out_btn = QPushButton("Zooma ut")
        zoom_out_btn.setObjectName("pdf_zoom_out")
        fit_btn = QPushButton("Fit bredd")
        fit_btn.setObjectName("pdf_fit_width")
        prev_btn = QPushButton("Föregående")
        prev_btn.setObjectName("pdf_prev_page")
        next_btn = QPushButton("Nästa")
        next_btn.setObjectName("pdf_next_page")
        self._page_label = QLabel("Sida 1 / 1")
        self._page_label.setObjectName("pdf_page_indicator")
        self._page_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        toolbar.addWidget(zoom_in_btn)
        toolbar.addWidget(zoom_out_btn)
        toolbar.addWidget(fit_btn)
        toolbar.addSeparator()
        toolbar.addWidget(prev_btn)
        toolbar.addWidget(next_btn)
        toolbar.addWidget(self._page_label)

        self._view = _PDFGraphicsView(self)
        layout.addWidget(toolbar)
        layout.addWidget(self._view)

        zoom_in_btn.clicked.connect(self._view.zoom_in)
        zoom_out_btn.clicked.connect(self._view.zoom_out)
        fit_btn.clicked.connect(self._view.fit_to_width)
        prev_btn.clicked.connect(self._on_prev_page)
        next_btn.clicked.connect(self._on_next_page)
        self._view.candidate_clicked.connect(self.candidate_clicked.emit)

    def _on_prev_page(self) -> None:
        if self._view.page_count == 0:
            return
        p = max(1, self._view.current_page_number - 1)
        self._view.set_page(p)
        self._update_page_label()

    def _on_next_page(self) -> None:
        if self._view.page_count == 0:
            return
        p = min(self._view.page_count, self._view.current_page_number + 1)
        self._view.set_page(p)
        self._update_page_label()

    def _update_page_label(self) -> None:
        n = self._view.current_page_number
        total = self._view.page_count
        self._page_label.setText(f"Sida {n} / {total}" if total else "Sida 1 / 1")

    def load_pdf(self, path: str) -> None:
        self._view.load_pdf(path)
        self._update_page_label()

    def set_candidates(
        self,
        candidates: List[Dict],
        traceability: Optional[Traceability] = None,
    ) -> None:
        self._view.set_candidates(candidates, traceability)

    def set_page(self, page_number: int) -> None:
        self._view.set_page(page_number)
        self._update_page_label()

    def highlight_candidate(self, candidate_index: int) -> None:
        self._view.highlight_candidate(candidate_index)

    def closeEvent(self, event) -> None:
        if getattr(self._view, "pdf_doc", None) is not None:
            self._view.pdf_doc.close()
            self._view.pdf_doc = None
        super().closeEvent(event)
