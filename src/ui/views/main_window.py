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
    QProgressBar, QGroupBox, QLineEdit, QSplitter, QMenuBar, QMenu,
    QToolBar, QStatusBar, QStackedWidget, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QAction, QKeySequence, QIcon

logger = logging.getLogger(__name__)

from .. import resources_rc  # noqa: F401 - register icons for QIcon(":/...")
from ..services.engine_runner import EngineRunner
from .pdf_viewer import PDFViewer
from .candidate_selector import CandidateSelector
from .ai_settings_dialog import AISettingsDialog
from .about_dialog import AboutDialog
from ...learning.correction_collector import save_correction, CorrectionCollector
from ...config import get_learning_db_path, get_default_output_dir
from ...export.excel_export import apply_corrections_to_excel

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPG PDF Extraherare")
        self.resize(800, 600)
        self.setAcceptDrops(True)
        self.setWindowIcon(QIcon(":/icons/app.svg"))
        
        # State
        self.input_path = None
        self.output_dir = str(get_default_output_dir())
        self.runner_thread = None
        self.runner = None
        self.processing_result = None
        self._last_run_summary: Optional[str] = None
        self._run_error_details: List[str] = []

        # UI Setup
        self.setup_menu_bar()
        self.setup_ui()
    
    def setup_menu_bar(self):
        """Setup menu bar with settings and help."""
        menubar = self.menuBar()
        
        # AI menu (same dialog as toolbar Inställningar; avoid duplicate "Settings" label)
        ai_menu = menubar.addMenu("AI")
        ai_settings_action = ai_menu.addAction("AI-inställningar...")
        ai_settings_action.triggered.connect(self.open_ai_settings)
        
        # Hjälp menu
        help_menu = menubar.addMenu("Hjälp")
        about_action = help_menu.addAction("Om EPG PDF Extraherare...")
        about_action.setIcon(QIcon(":/icons/about.svg"))
        about_action.triggered.connect(self.open_about)
        
    def setup_ui(self):
        """Initialize UI: toolbar, stacked empty/content, splitter, status bar."""
        # --- Toolbar: Öppna (Ctrl+O), Kör (Ctrl+R), Export (Ctrl+E), Inställningar ---
        toolbar = QToolBar()
        toolbar.setObjectName("main_toolbar")
        self.addToolBar(toolbar)

        self.open_action = QAction("Öppna PDF", self)
        self.open_action.setIcon(QIcon(":/icons/open.svg"))
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.browse_file)
        toolbar.addAction(self.open_action)

        self.run_action = QAction("Kör", self)
        self.run_action.setIcon(QIcon(":/icons/run.svg"))
        self.run_action.setShortcut(QKeySequence("Ctrl+R"))
        self.run_action.triggered.connect(self.start_processing)
        self.run_action.setEnabled(False)
        toolbar.addAction(self.run_action)

        self.export_action = QAction("Export", self)
        self.export_action.setIcon(QIcon(":/icons/export.svg"))
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.triggered.connect(self.open_output_dir)
        toolbar.addAction(self.export_action)

        settings_act = QAction("Inställningar", self)
        settings_act.setIcon(QIcon(":/icons/settings.svg"))
        settings_act.triggered.connect(self.open_ai_settings)
        toolbar.addAction(settings_act)

        # --- Central: stacked empty state | content (splitter) ---
        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        # Empty state: no PDF
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_layout.addStretch()
        empty_label = QLabel("Öppna en PDF för att börja")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet("font-size: 16px; color: #64748b;")
        empty_layout.addWidget(empty_label)
        open_cta = QPushButton("Öppna")
        open_cta.setMinimumHeight(44)
        open_cta.clicked.connect(self.browse_file)
        empty_layout.addWidget(open_cta, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch()
        self.stacked.addWidget(empty_widget)

        # Content: horizontal splitter (PDF left | results right)
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.pdf_viewer = PDFViewer()
        self.content_splitter.addWidget(self.pdf_viewer)

        results_panel = QWidget()
        results_layout = QVBoxLayout(results_panel)

        # Input / Output rows
        input_row = QHBoxLayout()
        self.input_label = QLineEdit()
        self.input_label.setPlaceholderText("Dra och släpp PDF eller välj fil...")
        self.input_label.setReadOnly(True)
        browse_btn = QPushButton("Välj fil")
        browse_btn.clicked.connect(self.browse_file)
        input_row.addWidget(self.input_label)
        input_row.addWidget(browse_btn)
        results_layout.addLayout(input_row)

        output_row = QHBoxLayout()
        self.output_label = QLineEdit(self.output_dir)
        self.output_label.setReadOnly(True)
        open_output_btn = QPushButton("Öppna mapp")
        open_output_btn.clicked.connect(self.open_output_dir)
        output_row.addWidget(self.output_label)
        output_row.addWidget(open_output_btn)
        results_layout.addLayout(output_row)

        self.progress_bar = QProgressBar()
        results_layout.addWidget(self.progress_bar)

        # Expandable log (12-03): collapsed by default
        log_header = QHBoxLayout()
        self.log_toggle_btn = QPushButton("Visa logg")
        self.log_toggle_btn.setCheckable(True)
        self.log_toggle_btn.setChecked(False)
        self.log_toggle_btn.clicked.connect(self._toggle_log_visibility)
        log_header.addWidget(self.log_toggle_btn)
        log_header.addStretch()
        results_layout.addLayout(log_header)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(80)
        self.log_area.setVisible(False)
        results_layout.addWidget(self.log_area)

        # Validation section (hidden until needed)
        self.validation_section = QWidget()
        val_layout = QVBoxLayout(self.validation_section)
        validation_label = QLabel("Validering: Välj korrekt totalsumma")
        validation_label.setStyleSheet("font-weight: bold; font-size: 14px")
        val_layout.addWidget(validation_label)
        self.candidate_selector = CandidateSelector()
        val_layout.addWidget(self.candidate_selector)
        val_btn_layout = QHBoxLayout()
        self.confirm_btn = QPushButton("Bekräfta val")
        self.confirm_btn.setMinimumHeight(40)
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._confirm_correction)
        val_btn_layout.addWidget(self.confirm_btn)
        skip_btn = QPushButton("Hoppa över")
        skip_btn.setMinimumHeight(40)
        skip_btn.clicked.connect(self._skip_validation)
        val_btn_layout.addWidget(skip_btn)
        self.next_invoice_btn = QPushButton("Nästa faktura")
        self.next_invoice_btn.setMinimumHeight(40)
        self.next_invoice_btn.clicked.connect(self._advance_to_next_validation)
        self.next_invoice_btn.setVisible(False)
        val_btn_layout.addWidget(self.next_invoice_btn)
        val_layout.addLayout(val_btn_layout)
        self.correction_status = QLabel("")
        self.correction_status.setStyleSheet("color: green; font-weight: bold")
        self.correction_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_layout.addWidget(self.correction_status)
        self.validation_section.setVisible(False)
        results_layout.addWidget(self.validation_section)

        self.pdf_viewer.candidate_clicked.connect(self._on_pdf_candidate_clicked)
        self.pdf_viewer.run_requested.connect(self.start_processing)
        self.candidate_selector.candidate_selected.connect(self._on_selector_candidate_selected)

        self.selected_candidate_index: Optional[int] = None
        self.selected_candidate_amount: Optional[float] = None
        self.correction_saved: bool = False
        self.current_invoice_header = None
        self._validation_queue: List[dict] = []
        self._validation_queue_index: int = 0
        self._current_validation_invoice_id: Optional[str] = None
        self._current_validation_invoice_number: Optional[str] = None

        self.content_splitter.addWidget(results_panel)
        self.content_splitter.setSizes([500, 400])
        self.stacked.addWidget(self.content_splitter)

        self.stacked.setCurrentIndex(0)

        # --- Status bar: engine state + last run summary ---
        self._update_status_bar("Idle", None)

    def _update_status_bar(self, state: str, summary: Optional[str] = None) -> None:
        """Set status bar text from engine state and optional last-run summary."""
        parts = [state]
        if summary:
            parts.append(summary)
        self.statusBar().showMessage("  |  ".join(parts))

    def _toggle_log_visibility(self) -> None:
        """Toggle expandable log panel (12-03)."""
        vis = self.log_toggle_btn.isChecked()
        self.log_area.setVisible(vis)
        self.log_toggle_btn.setText("Dölj logg" if vis else "Visa logg")

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
        self.run_action.setEnabled(True)
        self.stacked.setCurrentIndex(1)
        try:
            self.pdf_viewer.load_pdf(path)
        except Exception as e:
            logger.warning("Could not load PDF into viewer: %s", e)
        self.log(f"Vald fil: {path}")

    def open_output_dir(self):
        path = Path(self.output_dir)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(path))

    def start_processing(self) -> None:
        if not self.input_path:
            return

        self._run_error_details = []
        self.run_action.setEnabled(False)
        self.open_action.setEnabled(False)
        self.export_action.setEnabled(False)
        self.pdf_viewer.set_run_button_enabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.log_area.clear()
        self._update_status_bar("Running", None)

        self.runner_thread = QThread()
        self.runner = EngineRunner(self.input_path, self.output_dir)
        self.runner.moveToThread(self.runner_thread)

        self.runner.started.connect(lambda: self.log("Startar motor..."))
        self.runner.logLine.connect(self.log)
        # progress är samma som logLine för bakåtkompatibilitet – anslut inte båda till log (ger dubbel utskrift)
        self.runner.stateChanged.connect(self._on_engine_state_changed)
        self.runner.error.connect(self._on_engine_error)
        self.runner.result_ready.connect(self.handle_result)
        self.runner.finished.connect(self.processing_finished)

        self.runner_thread.started.connect(self.runner.run)
        self.runner_thread.start()

    def _on_engine_state_changed(self, state: str) -> None:
        """React to engine state (12-03)."""
        self._update_status_bar(state, self._last_run_summary if state != "Running" else None)

    def processing_finished(self, success: bool, paths: Any) -> None:
        if self.runner_thread:
            self.runner_thread.quit()
            self.runner_thread.wait()

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.run_action.setEnabled(True)
        self.open_action.setEnabled(True)
        self.export_action.setEnabled(True)
        self.pdf_viewer.set_run_button_enabled(True)

        if success:
            self._update_status_bar("Success", self._last_run_summary)
        else:
            self._update_status_bar("Error", self._last_run_summary)
            self._show_run_error_dialog()

    def _show_run_error_dialog(self) -> None:
        """Show user-friendly error dialog with expandable details (12-03)."""
        short = (
            "Körningen misslyckades. Kontrollera att motorn är installerad och att PDF-filen är giltig."
        )
        details = "\n".join(self._run_error_details) if self._run_error_details else short
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Körfel")
        box.setText(short)
        box.setDetailedText(details)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.exec()

    def handle_result(self, summary):
        self.log("-" * 40)
        self.log("RESULTAT:")
        self.log(f"Status: {summary.get('status')}")
        self.log(f"OK: {summary.get('ok_count')}, Review: {summary.get('review_count')}")
        if summary.get('excel_path'):
            self.log(f"Excel: {summary.get('excel_path')}")
        self.log("-" * 40)

        ok = summary.get("ok_count", 0)
        review = summary.get("review_count", 0)
        total = ok + review
        if total == 0:
            self._last_run_summary = "ingen fil"
        else:
            parts = [f"{total} fil{'er' if total != 1 else ''}"]
            if ok:
                parts.append(f"{ok} OK")
            if review:
                parts.append(f"{review} review")
            self._last_run_summary = ", ".join(parts)
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
            pr = self.processing_result or {}
            self.processing_result = pr
            self._validation_queue = pr.get("validation_queue") or []
            self._validation_queue_index = 0
            if self._validation_queue and not pr.get("validation"):
                pr["validation"] = self._validation_queue[0]
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
        self.validation_section.setVisible(True)
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
            if self.processing_result is not None:
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
        """Hide validation section and clear status."""
        self.validation_section.setVisible(False)
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
        
        base_path = self.input_path or ""
        doc = Document(
            filename=Path(base_path).name if base_path else "unknown.pdf",
            filepath=base_path,
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
        supplier_name = validation.get("supplier_name") or None
        self.current_invoice_header = InvoiceHeader(
            segment=segment,
            total_amount=None,
            total_confidence=0.0,
            supplier_name=supplier_name,
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
                base_path = self.input_path or ""
                doc = Document(
                    filename=Path(base_path).name if base_path else "unknown.pdf",
                    filepath=base_path,
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
            # Uppdatera Excel med validerade värden
            try:
                all_corrections = CorrectionCollector().get_corrections()
                if all_corrections:
                    pr = self.processing_result or {}
                    excel_path = pr.get("excel_path")
                    if excel_path and Path(excel_path).exists():
                        if apply_corrections_to_excel(excel_path, all_corrections):
                            msg += " – Excel uppdaterad"
                            self.log("Excel uppdaterad med validerade värden")
                    # Uppdatera även per-faktura Excel i review-mappen om den finns
                    review_excel = Path(self.output_dir) / "review" / str(invoice_id) / f"{invoice_id}.xlsx"
                    if review_excel.exists() and apply_corrections_to_excel(review_excel, all_corrections):
                        self.log(f"Review-Excel uppdaterad: {review_excel.name}")
            except Exception as excel_err:
                logger.warning("Kunde inte uppdatera Excel med korrigeringar: %s", excel_err)
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
            self._update_status_bar("Idle", "AI-inställningar uppdaterade")
            logger.info("AI settings updated from UI")

    def open_about(self):
        """Open About dialog (Om appen + Hjälp)."""
        dialog = AboutDialog(self)
        dialog.exec()

    def log(self, message):
        self.log_area.append(message)
        # Scroll to bottom
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def log_error(self, message):
        self.log_area.append(f"<font color='red'>{message}</font>")

    def _on_engine_error(self, message: str) -> None:
        self.log_error(message)
        self._run_error_details.append(message)
        self._update_status_bar("Error", message)
