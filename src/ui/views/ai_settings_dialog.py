"""AI settings dialog for configuring AI provider and API keys."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QFrame, QGroupBox, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt

from ...config import load_ai_config, set_ai_config, clear_ai_config

logger = logging.getLogger(__name__)


def _default_model(provider: str) -> str:
    """Provider-specific default model."""
    if provider == "claude":
        return "claude-3-opus-20240229"
    return "gpt-4-turbo-preview"


class AISettingsDialog(QDialog):
    """Dialog for configuring AI settings."""
    
    def __init__(self, parent=None):
        """Initialize AI settings dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("AI-inställningar")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        # Load current settings from config file (source of truth after save)
        config = load_ai_config()
        self.current_enabled = config.get("enabled", False)
        self.current_provider = (config.get("provider") or "openai").lower()
        self.current_model = config.get("model") or _default_model(self.current_provider)
        self.current_key = config.get("api_key") or ""
        
        # Setup UI
        self.setup_ui()
        
        # Load values into UI
        self.load_settings()
    
    def _status_text(self) -> str:
        """Current AI config status for display."""
        c = load_ai_config()
        key = (c.get("api_key") or "").strip()
        prov = (c.get("provider") or "openai").lower()
        model = c.get("model") or _default_model(prov)
        enabled = c.get("enabled", False)
        prov_disp = "OpenAI" if prov == "openai" else "Claude"
        if not key:
            return f"Ingen AI konfigurerad"
        status = f"Konfigurerad: {prov_disp}, {model}"
        if enabled:
            status += " · Aktiverad"
        else:
            status += " · Inaktiverad"
        return status
    
    def setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)
        self.setStyleSheet("QDialog { background-color: #fafafa; }")
        
        # --- Status (vilken AI som är tillagd) - tydlig ruta med mörk text ---
        status_frame = QFrame()
        status_frame.setStyleSheet(
            "QFrame { background-color: #e8e8e8; border: 1px solid #999; border-radius: 4px; } "
            "QLabel { color: #111; font-weight: bold; font-size: 13px; }"
        )
        status_frame.setMinimumHeight(44)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 6, 10, 6)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_frame)
        
        # --- Aktivera / Inaktivera ---
        self.ai_enabled_checkbox = QCheckBox("Aktivera AI-fallback")
        self.ai_enabled_checkbox.setStyleSheet("QCheckBox { color: #111; font-weight: bold; }")
        self.ai_enabled_checkbox.setToolTip(
            "Kryssa i för att aktivera, avkryssa för att inaktivera. AI används när confidence < 95 %."
        )
        layout.addWidget(self.ai_enabled_checkbox)
        
        # --- Provider Selection ---
        provider_group = QGroupBox("AI-leverantör")
        provider_group.setStyleSheet("QGroupBox { color: #111; font-weight: bold; }")
        provider_layout = QVBoxLayout()
        
        provider_label = QLabel("Välj AI-leverantör:")
        provider_label.setStyleSheet("color: #111;")
        provider_layout.addWidget(provider_label)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Claude"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)
        
        # --- Model Selection ---
        model_group = QGroupBox("Modell")
        model_group.setStyleSheet("QGroupBox { color: #111; font-weight: bold; }")
        model_layout = QVBoxLayout()
        
        model_label = QLabel("Välj modell:")
        model_label.setStyleSheet("color: #111;")
        model_layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)  # Allow custom model names
        model_layout.addWidget(self.model_combo)
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # --- API Key ---
        key_group = QGroupBox("API-nyckel")
        key_group.setStyleSheet("QGroupBox { color: #111; font-weight: bold; }")
        key_layout = QVBoxLayout()
        
        key_label = QLabel("API-nyckel:")
        key_label.setStyleSheet("color: #111;")
        key_layout.addWidget(key_label)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Ange din API-nyckel här...")
        key_layout.addWidget(self.api_key_input)
        
        # Show/Hide button
        show_key_btn = QPushButton("Visa")
        show_key_btn.setCheckable(True)
        show_key_btn.toggled.connect(
            lambda checked: self.api_key_input.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )
        key_layout.addWidget(show_key_btn)
        
        key_group.setLayout(key_layout)
        layout.addWidget(key_group)
        
        # --- Info ---
        info_label = QLabel(
            "AI används innan kandidatlistan visas: om confidence < 95 % anropas AI och ev. "
            "förslag läggs högst upp. AI får hela sidans text (header, items, footer), radsumma "
            "och våra kandidater—så den kan hitta rätt total även när kandidaterna är fel.\n"
            "Spara för att aktivera/inaktivera. Inställningar gäller vid nästa körning."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #333; font-size: 11px;")
        layout.addWidget(info_label)
        
        # --- Buttons ---
        button_layout = QHBoxLayout()
        remove_btn = QPushButton("Ta bort")
        remove_btn.setToolTip("Ta bort konfigurerad AI (provider, modell, nyckel)")
        remove_btn.clicked.connect(self._remove_config)
        button_layout.addWidget(remove_btn)
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Avbryt")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Spara")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _reload_config(self):
        """Reload config from file into current_* and refresh UI."""
        config = load_ai_config()
        self.current_enabled = config.get("enabled", False)
        self.current_provider = (config.get("provider") or "openai").lower()
        self.current_model = config.get("model") or _default_model(self.current_provider)
        self.current_key = config.get("api_key") or ""
    
    def _remove_config(self):
        """Remove AI configuration and refresh dialog."""
        clear_ai_config()
        self._reload_config()
        self.load_settings()
    
    def load_settings(self):
        """Load current settings into UI."""
        self.status_label.setText(self._status_text())
        # AI enabled
        self.ai_enabled_checkbox.setChecked(self.current_enabled)
        
        # Provider
        provider_index = 0 if self.current_provider == "openai" else 1
        self.provider_combo.setCurrentIndex(provider_index)
        self._update_model_options()
        
        # Model
        model_index = self.model_combo.findText(self.current_model)
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)
        else:
            self.model_combo.setCurrentText(self.current_model)
        
        # API key (only show if already set, don't reveal full key)
        if self.current_key:
            masked_key = self.current_key[:8] + "..." if len(self.current_key) > 8 else "***"
            self.api_key_input.setPlaceholderText(f"Nuvarande nyckel: {masked_key}")
        else:
            self.api_key_input.clear()
            self.api_key_input.setPlaceholderText("Ange din API-nyckel här...")
    
    def _on_provider_changed(self, provider_text: str):
        """Handle provider selection change.
        
        Args:
            provider_text: Selected provider name
        """
        self._update_model_options()
    
    def _update_model_options(self):
        """Update model combo box based on selected provider."""
        provider_text = self.provider_combo.currentText()
        self.model_combo.clear()
        
        if provider_text == "OpenAI":
            self.model_combo.addItems([
                "gpt-5-nano",
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-3.5-turbo"
            ])
        elif provider_text == "Claude":
            self.model_combo.addItems([
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307"
            ])
    
    def save_settings(self):
        """Save settings and close dialog."""
        # Get API key
        api_key_input = self.api_key_input.text().strip()
        
        # If AI is enabled, validate API key
        if self.ai_enabled_checkbox.isChecked():
            if not api_key_input and not self.current_key:
                QMessageBox.warning(
                    self,
                    "API-nyckel saknas",
                    "Du måste ange en API-nyckel för att aktivera AI-fallback."
                )
                return
            
            # Use new key if provided, otherwise keep existing
            api_key = api_key_input if api_key_input else self.current_key
        else:
            # AI disabled - keep existing key (don't clear it)
            api_key = api_key_input if api_key_input else self.current_key
        
        # Get provider
        provider_text = self.provider_combo.currentText()
        provider = "openai" if provider_text == "OpenAI" else "claude"
        
        # Get model
        model = self.model_combo.currentText().strip()
        if not model:
            QMessageBox.warning(
                self,
                "Modell saknas",
                "Du måste välja eller ange en modell."
            )
            return
        
        # Get enabled state
        enabled = self.ai_enabled_checkbox.isChecked()
        
        # Save settings
        try:
            # Only pass api_key if it's provided, otherwise None (keeps existing)
            api_key_to_save = api_key if api_key else None
            set_ai_config(
                enabled=enabled,
                provider=provider,
                model=model,
                api_key=api_key_to_save
            )
            
            QMessageBox.information(
                self,
                "Inställningar sparade",
                "AI-inställningarna har sparats och kommer att användas vid nästa körning."
            )
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Failed to save AI settings: {e}")
            QMessageBox.critical(
                self,
                "Fel",
                f"Kunde inte spara inställningar: {e}"
            )
