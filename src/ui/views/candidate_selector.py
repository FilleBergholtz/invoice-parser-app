"""Candidate selector widget for manual validation."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QScrollArea
)

logger = logging.getLogger(__name__)


class CandidateSelector(QWidget):
    """Widget for selecting total amount candidates with keyboard shortcuts.
    
    Displays list of candidates with confidence scores and supports
    mouse click and keyboard navigation (arrow keys, Enter).
    """
    
    # Signal emitted when candidate is selected
    # Args: (candidate_index: int, amount: float)
    candidate_selected = Signal(int, float)
    
    def __init__(self, parent=None):
        """Initialize candidate selector.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        
        # State
        self.candidates: List[Dict] = []
        self.selected_index: Optional[int] = None
        self.candidate_buttons: List[QPushButton] = []
        
        # UI Setup
        self.setup_ui()
    
    def setup_ui(self):
        """Initialize UI components."""
        self.setStyleSheet("background-color: #f8f8f8;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Title (dark text for contrast)
        title = QLabel("Välj korrekt totalsumma:")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #111; background: transparent;")
        layout.addWidget(title)
        
        # Scroll area for candidate list
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Container for candidate buttons
        self.candidates_widget = QWidget()
        self.candidates_layout = QVBoxLayout(self.candidates_widget)
        self.candidates_layout.setContentsMargins(0, 0, 0, 0)
        self.candidates_layout.setSpacing(5)
        self.candidates_layout.addStretch()  # Push buttons to top
        
        self.scroll_area.setWidget(self.candidates_widget)
        layout.addWidget(self.scroll_area)
        
        # Instructions (dark gray for readability on light and dark backgrounds)
        instructions = QLabel("Använd piltangenter för att navigera\nEnter för att välja")
        instructions.setStyleSheet("color: #333; font-size: 11px; background: transparent;")
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instructions)
        
        # Enable keyboard focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def set_candidates(self, candidates: List[Dict]) -> None:
        """Set candidate list to display.
        
        Args:
            candidates: List of candidate dicts from InvoiceHeader.total_candidates
                Each dict has: amount, score, row_index, keyword_type
        """
        # Clear existing buttons
        for button in self.candidate_buttons:
            self.candidates_layout.removeWidget(button)
            button.deleteLater()
        self.candidate_buttons.clear()
        
        self.candidates = candidates
        self.selected_index = None
        
        if not candidates:
            # Show message if no candidates
            no_candidates = QLabel("Inga kandidater tillgängliga")
            no_candidates.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_candidates.setStyleSheet("color: #555; padding: 20px; background: transparent;")
            self.candidates_layout.insertWidget(0, no_candidates)
            return
        
        # Create button for each candidate
        for idx, candidate in enumerate(candidates):
            amount = candidate.get('amount', 0.0)
            score = candidate.get('score', 0.0)
            row_index = candidate.get('row_index', -1)
            keyword_type = candidate.get('keyword_type', 'unknown')
            
            # Format display text
            amount_str = f"{amount:,.2f}".replace(',', ' ').replace('.', ',')
            score_str = f"{score:.1%}"
            
            # Button text
            button_text = f"SEK {amount_str}\n(confidence: {score_str})"
            
            # Create button
            button = QPushButton(button_text)
            button.setCheckable(True)
            button.setMinimumHeight(60)
            button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px;
                    border: 2px solid #888;
                    border-radius: 4px;
                    background-color: #f5f5f5;
                    color: #1a1a1a;
                }
                QPushButton:hover {
                    border-color: #0078d4;
                    background-color: #e8e8e8;
                    color: #111;
                }
                QPushButton:checked {
                    border-color: #0078d4;
                    background-color: #cce5ff;
                    color: #0d47a1;
                    font-weight: bold;
                }
            """)
            
            # Tooltip with additional info
            tooltip = f"Rad {row_index}, Typ: {keyword_type}"
            button.setToolTip(tooltip)
            
            # Connect click signal
            button.clicked.connect(lambda checked, i=idx: self._on_candidate_clicked(i))
            
            # Store button
            self.candidate_buttons.append(button)
            self.candidates_layout.insertWidget(idx, button)
        
        # Select first candidate by default
        if self.candidate_buttons:
            self.select_candidate(0)
    
    def select_candidate(self, index: int) -> None:
        """Select candidate by index (programmatic).
        
        Args:
            index: Candidate index (0-based)
        """
        if not self.candidate_buttons or index < 0 or index >= len(self.candidate_buttons):
            return
        
        # Deselect previous
        if self.selected_index is not None and self.selected_index < len(self.candidate_buttons):
            self.candidate_buttons[self.selected_index].setChecked(False)
        
        # Select new
        self.selected_index = index
        btn = self.candidate_buttons[index]
        btn.setChecked(True)
        
        # Scroll scroll area so selected button is visible
        self.scroll_area.ensureWidgetVisible(btn)
        
        # Set focus for keyboard navigation
        self.setFocus()
    
    def _on_candidate_clicked(self, index: int) -> None:
        """Handle candidate button click.
        
        Args:
            index: Candidate index
        """
        self.select_candidate(index)
        
        # Emit signal
        if index < len(self.candidates):
            candidate = self.candidates[index]
            amount = candidate.get('amount', 0.0)
            self.candidate_selected.emit(index, amount)
            logger.debug(f"Candidate {index} selected: SEK {amount}")
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard shortcuts.
        
        Args:
            event: Key event
        """
        if not self.candidate_buttons:
            super().keyPressEvent(event)
            return
        
        key = event.key()
        
        if key == Qt.Key.Key_Up:
            # Navigate up
            if self.selected_index is None or self.selected_index <= 0:
                # Wrap to last
                new_index = len(self.candidate_buttons) - 1
            else:
                new_index = self.selected_index - 1
            self.select_candidate(new_index)
            event.accept()
            
        elif key == Qt.Key.Key_Down:
            # Navigate down
            if self.selected_index is None or self.selected_index >= len(self.candidate_buttons) - 1:
                # Wrap to first
                new_index = 0
            else:
                new_index = self.selected_index + 1
            self.select_candidate(new_index)
            event.accept()
            
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            # Select highlighted candidate
            if self.selected_index is not None:
                self._on_candidate_clicked(self.selected_index)
            event.accept()
            
        elif key == Qt.Key.Key_Escape:
            # Cancel selection (optional - just clear highlight)
            if self.selected_index is not None:
                self.candidate_buttons[self.selected_index].setChecked(False)
                self.selected_index = None
            event.accept()
            
        else:
            super().keyPressEvent(event)
    
    def get_selected_candidate(self) -> Optional[Dict]:
        """Get currently selected candidate.
        
        Returns:
            Selected candidate dict, or None if none selected
        """
        if self.selected_index is not None and self.selected_index < len(self.candidates):
            return self.candidates[self.selected_index]
        return None
