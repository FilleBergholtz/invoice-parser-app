"""Main window for the Invoice Parser UI."""

import sys
import os
from pathlib import Path
from types import SimpleNamespace
import logging
from typing import Optional, Tuple, List, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFileDialog, QTextEdit, 
    QProgressBar, QGroupBox, QLineEdit, QSplitter, QMenuBar, QMenu
)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent

logger = logging.getLogger(__name__)

from ..services.engine_runner import EngineRunner
from .pdf_viewer import PDFViewer
from .candidate_selector import CandidateSelector
from .ai_settings_dialog import AISettingsDialog
from ...learning.correction_collector import save_correction
from ...config import get_learning_db_path

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPG PDF Extraherare")
        self.resize(800, 600)
        self.setAcceptDrops(True)
        
        # State
        self.input_path = None
        self.output_dir = str(Path.home() / "Documents" / "EPG PDF Extraherare" / "output")
        self.runner_thread = None
        self.runner = None
        self.processing_result = None  # Store processing result for validation
        
        # UI Setup
        self.setup_menu_bar()
        self.setup_ui()
    
    def setup_menu_bar(self):
        """Setup menu bar with settings."""
        menubar = self.menuBar()
        
        # Inställningar menu
        settings_menu = menubar.addMenu("Inställningar")
        
        # AI-inställningar action
        ai_settings_action = settings_menu.addAction("AI-inställningar...")
        ai_settings_action.triggered.connect(self.open_ai_settings)
        
    def setup_ui(self):
        """Initialize UI components."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # --- Input Section ---
        input_group = QGroupBox("Input PDF")
        input_layout = QHBoxLayout()
        
        self.input_label = QLineEdit()
        self.input_label.setPlaceholderText("Dra och släpp PDF här eller välj fil...")
        self.input_label.setReadOnly(True)
        
        browse_btn = QPushButton("Välj Fil")
        browse_btn.clicked.connect(self.browse_file)
        
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(browse_btn)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # --- Output Section ---
        output_group = QGroupBox("Output Mapp")
        output_layout = QHBoxLayout()
        
        self.output_label = QLineEdit(self.output_dir)
        self.output_label.setReadOnly(True)
        
        open_output_btn = QPushButton("Öppna Mapp")
        open_output_btn.clicked.connect(self.open_output_dir)
        
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(open_output_btn)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # --- Actions ---
        action_layout = QHBoxLayout()
        self.start_btn = QPushButton("Starta Bearbetning")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        
        action_layout.addWidget(self.start_btn)
        layout.addLayout(action_layout)
        
        # --- Progress & Logs ---
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        # --- Status ---
        self.status_label = QLabel("Redo")
        layout.addWidget(self.status_label)
        
        # --- Validation Section (initially hidden) ---
        self.validation_widget = QWidget()
        validation_layout = QVBoxLayout(self.validation_widget)
        
        validation_label = QLabel("Validering: Välj korrekt totalsumma")
        validation_label.setStyleSheet("font-weight: bold; font-size: 14px")
        validation_layout.addWidget(validation_label)
        
        # Splitter for PDF viewer and candidate selector
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # PDF Viewer
        self.pdf_viewer = PDFViewer()
        splitter.addWidget(self.pdf_viewer)
        
        # Candidate Selector
        self.candidate_selector = CandidateSelector()
        splitter.addWidget(self.candidate_selector)
        
        splitter.setSizes([600, 300])  # PDF viewer larger, candidate selector wider
        validation_layout.addWidget(splitter)
        
        # Action buttons (explicit contrast: dark text on light background)
        action_layout = QHBoxLayout()
        _btn_style = """
            QPushButton {
                background-color: #e0e0e0; color: #111; border: 2px solid #888;
                border-radius: 4px; font-weight: bold; padding: 8px 16px;
            }
            QPushButton:hover { background-color: #d0d0d0; border-color: #0078d4; }
            QPushButton:pressed { background-color: #c0c0c0; }
            QPushButton:disabled { background-color: #ccc; color: #666; border-color: #999; }
        """
        self.confirm_btn = QPushButton("Bekräfta val")
        self.confirm_btn.setMinimumHeight(40)
        self.confirm_btn.setStyleSheet(_btn_style)
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._confirm_correction)
        action_layout.addWidget(self.confirm_btn)
        
        skip_btn = QPushButton("Hoppa över")
        skip_btn.setMinimumHeight(40)
        skip_btn.setStyleSheet(_btn_style)
        skip_btn.clicked.connect(self._skip_validation)
        action_layout.addWidget(skip_btn)
        
        validation_layout.addLayout(action_layout)
        
        # Status message for corrections
        self.correction_status = QLabel("")
        self.correction_status.setStyleSheet("color: green; font-weight: bold")
        self.correction_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        validation_layout.addWidget(self.correction_status)
        
        # Connect signals for bidirectional synchronization
        self.pdf_viewer.candidate_clicked.connect(self._on_pdf_candidate_clicked)
        self.candidate_selector.candidate_selected.connect(self._on_selector_candidate_selected)
        
        # State for selected candidate and correction
        self.selected_candidate_index: Optional[int] = None
        self.selected_candidate_amount: Optional[float] = None
        self.correction_saved: bool = False
        self.current_invoice_header = None  # Will store InvoiceHeader when available
        self._validation_queue: List[dict] = []
        self._validation_queue_index: int = 0
        self._current_validation_invoice_id: Optional[str] = None
        self._current_validation_invoice_number: Optional[str] = None  # Extraherade fakturanummer (prioritet över filnamn)

        self.next_invoice_btn = QPushButton("Nästa faktura")
        self.next_invoice_btn.setMinimumHeight(40)
        self.next_invoice_btn.setStyleSheet(_btn_style)
        self.next_invoice_btn.clicked.connect(self._advance_to_next_validation)
        action_layout.addWidget(self.next_invoice_btn)
        self.next_invoice_btn.setVisible(False)
        
        # Initially hide validation section
        self.validation_widget.setVisible(False)
        layout.addWidget(self.validation_widget)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            self.set_input_file(files[0])

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Välj PDF Faktura", str(Path.home()), "PDF Files (*.pdf)"
        )
        if file_path:
            self.set_input_file(file_path)

    def set_input_file(self, path):
        self.input_path = path
        self.input_label.setText(path)
        self.start_btn.setEnabled(True)
        self.log(f"Vald fil: {path}")

    def open_output_dir(self):
        path = Path(self.output_dir)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))

    def start_processing(self):
        if not self.input_path:
            return
            
        # Disable UI
        self.start_btn.setEnabled(False)
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.log_area.clear()
        self.status_label.setText("Bearbetar...")
        
        # Create Runner
        self.runner_thread = QThread()
        self.runner = EngineRunner(self.input_path, self.output_dir)
        self.runner.moveToThread(self.runner_thread)
        
        # Connect signals
        self.runner.started.connect(lambda: self.log("Startar motor..."))
        self.runner.progress.connect(self.log)
        self.runner.error.connect(self.log_error)
        self.runner.result_ready.connect(self.handle_result)
        self.runner.finished.connect(self.processing_finished)
        
        self.runner_thread.started.connect(self.runner.run)
        
        # Start
        self.runner_thread.start()

    def processing_finished(self, exit_code):
        self.runner_thread.quit()
        self.runner_thread.wait()
        
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.start_btn.setEnabled(True)
        
        if exit_code == 0:
            self.status_label.setText("Klar (OK)")
            self.status_label.setStyleSheet("color: green")
        else:
            self.status_label.setText(f"Klar (Exit Code {exit_code})")
            # Yellow/Red depending on severity logic, usually code 1 is fail/review
            self.status_label.setStyleSheet("color: orange")

    def handle_result(self, summary):
        self.log("-" * 40)
        self.log("RESULTAT:")
        self.log(f"Status: {summary.get('status')}")
        self.log(f"OK: {summary.get('ok_count')}, Review: {summary.get('review_count')}")
        if summary.get('excel_path'):
            self.log(f"Excel: {summary.get('excel_path')}")
        self.log("-" * 40)
        
        # Store result for validation
        self.processing_result = summary
        
        # Check if validation needed (REVIEW status or low confidence)
        # For now, show validation if review_count > 0 or if single file with low confidence
        # In future, we'll check individual invoice confidence from artifacts
        needs_validation = (
            summary.get('review_count', 0) > 0 or
            summary.get('status') == 'REVIEW'
        )
        
        if needs_validation and self.input_path:
            self._show_validation_ui()
    
    def _show_validation_ui(self):
        """Show validation UI with PDF viewer and candidate selector.
        Initializes validation queue from processing_result and shows first item.
        """
        try:
            self._validation_queue = (self.processing_result or {}).get("validation_queue") or []
            self._validation_queue_index = 0
            if self._validation_queue and not (self.processing_result or {}).get("validation"):
                self.processing_result["validation"] = self._validation_queue[0]
            self._refresh_validation_view()
            self._update_next_button_visibility()
        except Exception as e:
            self.log_error(f"Kunde inte ladda PDF för validering: {e}")

    def _refresh_validation_view(self) -> None:
        """Load current processing_result['validation'] into PDF viewer and candidate selector."""
        validation = (self.processing_result or {}).get("validation") or {}
        pdf_path = validation.get("pdf_path") or (self.processing_result or {}).get("input_path") or self.input_path
        pdf_path = str(Path(pdf_path).resolve()) if pdf_path else None
        if not pdf_path or not Path(pdf_path).exists():
            pdf_path = self.input_path
        if not pdf_path or not Path(pdf_path).exists():
            self.log_error("Kunde inte hitta PDF att validera (saknad pdf_path).")
            return
        self.pdf_viewer.load_pdf(pdf_path)
        self.log(f"Validerar PDF: {pdf_path}")
        candidates, traceability = self._load_candidates_from_result()
        if candidates:
            self.candidate_selector.set_candidates(candidates)
            self.pdf_viewer.set_candidates(candidates, traceability)
            page = 1
            if traceability and getattr(traceability, "evidence", None):
                page = traceability.evidence.get("page_number", 1)
            try:
                self.pdf_viewer.set_page(int(page))
            except Exception:
                pass
        else:
            self.log("Inga kandidater hittades - validering kan inte utföras")
        self.validation_widget.setVisible(True)
        self.log("Valideringsläge aktiverat - välj korrekt totalsumma från listan")
        self.candidate_selector.setFocus()

    def _update_next_button_visibility(self) -> None:
        """Show 'Nästa faktura' when there is a next item in the validation queue."""
        visible = (
            len(self._validation_queue) > 1
            and self._validation_queue_index < len(self._validation_queue) - 1
        )
        self.next_invoice_btn.setVisible(visible)

    def _advance_to_next_validation(self) -> None:
        """Switch to next item in validation queue, or close UI if none left."""
        self._validation_queue_index += 1
        if self._validation_queue_index < len(self._validation_queue):
            self.processing_result["validation"] = self._validation_queue[self._validation_queue_index]
            self.selected_candidate_index = None
            self.selected_candidate_amount = None
            self.correction_saved = False
            self.confirm_btn.setEnabled(False)
            self.correction_status.setText("")
            self._refresh_validation_view()
            self._update_next_button_visibility()
        else:
            self._close_validation_ui()

    def _close_validation_ui(self) -> None:
        """Hide validation widget and clear status."""
        self.validation_widget.setVisible(False)
        self.correction_status.setText("")
        self.log("Validering avslutad")

    def _finish_current_validation_and_continue(self) -> None:
        """After skip or confirm: show next validation item or close UI."""
        if self._validation_queue and self._validation_queue_index < len(self._validation_queue) - 1:
            self._advance_to_next_validation()
        else:
            self._close_validation_ui()
    
    def _load_candidates_from_result(self) -> Tuple[List[dict], Any]:
        """Load candidates and traceability from processing result (run_summary.validation).
        
        Returns:
            (candidates, traceability_for_viewer). candidates is list of dicts;
            traceability_for_viewer has .evidence for PDF highlighting, or None.
        """
        candidates: List[dict] = []
        traceability_for_viewer = None
        
        if not self.processing_result:
            return candidates, traceability_for_viewer
        
        validation = self.processing_result.get("validation") or {}
        self._current_validation_invoice_id = validation.get("invoice_id")
        self._current_validation_invoice_number = validation.get("invoice_number")
        raw = validation.get("candidates") or []
        if not raw:
            return candidates, traceability_for_viewer
        
        candidates = [
            {
                "amount": c.get("amount", 0.0),
                "score": c.get("score", 0.0),
                "row_index": c.get("row_index", -1),
                "keyword_type": c.get("keyword_type", "unknown"),
            }
            for c in raw
        ]
        
        tr = validation.get("traceability")
        if isinstance(tr, dict) and "evidence" in tr:
            traceability_for_viewer = SimpleNamespace(evidence=tr["evidence"])
        
        # Minimal InvoiceHeader for correction saving (with total_candidates)
        from ...models.invoice_header import InvoiceHeader
        from ...models.segment import Segment
        from ...models.page import Page
        from ...models.document import Document
        from ...models.row import Row
        from ...models.token import Token
        
        doc = Document(
            filename=Path(self.input_path).name,
            filepath=self.input_path,
            page_count=0,
            pages=[],
            metadata={},
        )
        page = Page(document=doc, page_number=1, width=595.0, height=842.0)
        tok = Token(text="dummy", x=0, y=0, width=10, height=10, page=page)
        row = Row(tokens=[tok], text="dummy", x_min=0, x_max=0, y=0, page=page)
        segment = Segment(
            segment_type="header",
            rows=[row],
            y_min=0,
            y_max=100,
            page=page,
        )
        self.current_invoice_header = InvoiceHeader(
            segment=segment,
            total_amount=None,
            total_confidence=0.0,
            supplier_name=None,
            total_candidates=candidates,
        )
        
        return candidates, traceability_for_viewer
    
    def _on_pdf_candidate_clicked(self, candidate_index: int) -> None:
        """Handle candidate click in PDF viewer.
        
        Args:
            candidate_index: Index of clicked candidate
        """
        # Select in candidate selector
        self.candidate_selector.select_candidate(candidate_index)
        self.selected_candidate_index = candidate_index
        self.candidate_selector.setFocus()
        self.log(f"Kandidat {candidate_index} klickad i PDF")
    
    def _on_selector_candidate_selected(self, candidate_index: int, amount: float) -> None:
        """Handle candidate selection in selector.
        
        Args:
            candidate_index: Index of selected candidate
            amount: Selected amount
        """
        # Highlight in PDF viewer
        self.pdf_viewer.highlight_candidate(candidate_index)
        self.selected_candidate_index = candidate_index
        self.selected_candidate_amount = amount
        
        # Enable confirm button
        self.confirm_btn.setEnabled(True)
        
        # Clear previous status
        self.correction_status.setText("")
        
        self.log(f"Kandidat {candidate_index} vald: SEK {amount:,.2f}")
    
    def _confirm_correction(self) -> None:
        """Confirm and save correction."""
        if self.selected_candidate_index is None or self.selected_candidate_amount is None:
            self.log_error("Ingen kandidat vald - kan inte spara korrigering")
            return
        
        if self.correction_saved:
            self.log("Korrigering redan sparad för denna faktura")
            return
        
        try:
            # Använd extraherade fakturanummer som identifierare när det finns (en PDF kan innehålla flera fakturor med olika nummer)
            n = self._current_validation_invoice_number
            invoice_id = (n if n and str(n).strip() else None) or self._current_validation_invoice_id or (
                Path(self.input_path).stem if self.input_path else "unknown"
            )
            
            # For now, we don't have InvoiceHeader loaded from processing result
            # Create a minimal mock InvoiceHeader for correction saving
            # In future, we'll load actual InvoiceHeader from artifacts/review reports
            from ...models.invoice_header import InvoiceHeader
            from ...models.segment import Segment
            from ...models.page import Page
            from ...models.document import Document
            from ...models.row import Row
            from ...models.token import Token
            
            # Create minimal InvoiceHeader if not available
            if self.current_invoice_header is None:
                # Create minimal structure for correction saving
                # This is a workaround until we have full integration
                doc = Document(
                    filename=Path(self.input_path).name,
                    filepath=self.input_path,
                    page_count=0,
                    pages=[],
                    metadata={},
                )
                page = Page(document=doc, page_number=1, width=595.0, height=842.0)
                tok = Token(text="dummy", x=0, y=0, width=10, height=10, page=page)
                row = Row(tokens=[tok], text="dummy", x_min=0, x_max=0, y=0, page=page)
                segment = Segment(
                    segment_type="header",
                    rows=[row],
                    y_min=0,
                    y_max=100,
                    page=page,
                )
                
                self.current_invoice_header = InvoiceHeader(
                    segment=segment,
                    total_amount=None,  # Will be set from processing result
                    total_confidence=0.0,
                    supplier_name=None
                )
            
            # Get candidate score
            candidate_score = None
            if self.current_invoice_header.total_candidates:
                if self.selected_candidate_index < len(self.current_invoice_header.total_candidates):
                    candidate = self.current_invoice_header.total_candidates[self.selected_candidate_index]
                    candidate_score = candidate.get('score', 0.0)
            
            # Save correction to JSON (and to learning DB so it's used for learning directly)
            correction = save_correction(
                invoice_id=invoice_id,
                invoice_header=self.current_invoice_header,
                selected_amount=self.selected_candidate_amount,
                selected_index=self.selected_candidate_index,
                candidate_score=candidate_score
            )
            
            db_ok = False
            try:
                from ...learning.database import LearningDatabase
                from ...learning.pattern_extractor import extract_patterns_from_corrections
                db_path = get_learning_db_path()
                db = LearningDatabase(db_path)
                db.add_correction(correction)
                patterns = extract_patterns_from_corrections([correction])
                for p in patterns:
                    db.save_pattern(p)
                db_ok = True
            except Exception as db_err:
                logger.warning("Could not persist correction to learning DB: %s", db_err)
            
            self.correction_saved = True
            self.confirm_btn.setEnabled(False)
            msg = f"✓ Korrigering sparad: SEK {self.selected_candidate_amount:,.2f}"
            if db_ok:
                msg += " (fil + inlärningsdatabas)"
            else:
                msg += " (fil; databas otillgänglig)"
            self.correction_status.setText(msg)
            self.log(f"Korrigering sparad för faktura {invoice_id}" + (" – även i inlärningsdatabasen" if db_ok else " – endast i fil"))
            self._finish_current_validation_and_continue()
            return
            
        except Exception as e:
            self.log_error(f"Kunde inte spara korrigering: {e}")
            logger.error(f"Failed to save correction: {e}", exc_info=True)
    
    def _skip_validation(self) -> None:
        """Skip validation without saving correction; show next or close."""
        self.log("Validering hoppades över")
        self._finish_current_validation_and_continue()
    
    def open_ai_settings(self):
        """Open AI settings dialog."""
        dialog = AISettingsDialog(self)
        if dialog.exec():
            # Settings saved, update status
            self.status_label.setText("AI-inställningar uppdaterade")
            logger.info("AI settings updated from UI")

    def log(self, message):
        self.log_area.append(message)
        # Scroll to bottom
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def log_error(self, message):
        self.log_area.append(f"<font color='red'>{message}</font>")
