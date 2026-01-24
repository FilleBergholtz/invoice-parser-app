"""Main window for the Invoice Parser UI."""

import sys
import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QFileDialog, QTextEdit, 
    QProgressBar, QGroupBox, QLineEdit, QSplitter
)
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from ..services.engine_runner import EngineRunner
from .pdf_viewer import PDFViewer
from .candidate_selector import CandidateSelector

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
        self.setup_ui()
        
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
        
        # Connect signals for bidirectional synchronization
        self.pdf_viewer.candidate_clicked.connect(self._on_pdf_candidate_clicked)
        self.candidate_selector.candidate_selected.connect(self._on_selector_candidate_selected)
        
        # State for selected candidate
        self.selected_candidate_index: Optional[int] = None
        
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
        """Show validation UI with PDF viewer and candidate selector."""
        try:
            # Load PDF
            self.pdf_viewer.load_pdf(self.input_path)
            
            # Load candidates from processing result
            # For now, we'll try to load from artifacts or use mock data
            # In future, we'll have better integration with processing results
            candidates = self._load_candidates_from_result()
            
            if candidates:
                # Set candidates in selector
                self.candidate_selector.set_candidates(candidates)
                
                # Set candidates in PDF viewer (for highlighting)
                # We need traceability for PDF highlighting - for now, use first candidate's traceability
                # This will be enhanced when we have full InvoiceHeader data
                traceability = None  # TODO: Load from processing result
                self.pdf_viewer.set_candidates(candidates, traceability)
            else:
                self.log("Inga kandidater hittades - validering kan inte utföras")
            
            # Show validation section
            self.validation_widget.setVisible(True)
            self.log("Valideringsläge aktiverat - välj korrekt totalsumma från listan")
            
            # Set focus to candidate selector for keyboard navigation
            self.candidate_selector.setFocus()
            
        except Exception as e:
            self.log_error(f"Kunde inte ladda PDF för validering: {e}")
    
    def _load_candidates_from_result(self) -> list:
        """Load candidates from processing result.
        
        Returns:
            List of candidate dicts, or empty list if not available
        """
        # TODO: Load from actual processing result (artifacts, review reports, etc.)
        # For now, return empty list - this will be enhanced when we have
        # better integration with processing pipeline
        
        # In a real scenario, we would:
        # 1. Load InvoiceHeader from artifacts or review package
        # 2. Extract total_candidates from InvoiceHeader
        # 3. Extract total_traceability for PDF highlighting
        
        return []
    
    def _on_pdf_candidate_clicked(self, candidate_index: int) -> None:
        """Handle candidate click in PDF viewer.
        
        Args:
            candidate_index: Index of clicked candidate
        """
        # Select in candidate selector
        self.candidate_selector.select_candidate(candidate_index)
        self.selected_candidate_index = candidate_index
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
        self.log(f"Kandidat {candidate_index} vald: SEK {amount:,.2f}")

    def log(self, message):
        self.log_area.append(message)
        # Scroll to bottom
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def log_error(self, message):
        self.log_area.append(f"<font color='red'>{message}</font>")
