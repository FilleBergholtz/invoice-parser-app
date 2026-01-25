"""AI settings dialog: grouped Provider, Model, Thresholds, Limits; help text; Test connection stub."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ...config import clear_ai_config, load_ai_config, set_ai_config

logger = logging.getLogger(__name__)


def _default_model(provider: str) -> str:
    if provider == "claude":
        return "claude-3-opus-20240229"
    return "gpt-4-turbo-preview"


def _help_label(text: str) -> QLabel:
    """Create a muted help label (theme: QLabel[class=\"muted\"])."""
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setProperty("class", "muted")
    return lbl


class AISettingsDialog(QDialog):
    """AI settings dialog with grouped sections, help text, and Test connection stub."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aiSettingsDialog")
        self.setWindowTitle("AI-inställningar")
        self.setMinimumWidth(520)
        self.setModal(True)

        config = load_ai_config()
        self.current_enabled = config.get("enabled", False)
        self.current_provider = (config.get("provider") or "openai").lower()
        self.current_model = config.get("model") or _default_model(self.current_provider)
        self.current_key = config.get("api_key") or ""

        self.setup_ui()
        self.load_settings()

    def _status_text(self) -> str:
        c = load_ai_config()
        key = (c.get("api_key") or "").strip()
        prov = (c.get("provider") or "openai").lower()
        model = c.get("model") or _default_model(prov)
        enabled = c.get("enabled", False)
        prov_disp = "OpenAI" if prov == "openai" else "Claude"
        if not key:
            return "Ingen AI konfigurerad"
        status = f"Konfigurerad: {prov_disp}, {model}"
        status += " · Aktiverad" if enabled else " · Inaktiverad"
        return status

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # --- Status ---
        status_frame = QFrame()
        status_frame.setObjectName("ai_settings_status")
        status_frame.setMinimumHeight(44)
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 6, 10, 6)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_frame)

        # --- Provider ---
        provider_group = QGroupBox("Provider")
        provider_group.setObjectName("ai_group_provider")
        provider_layout = QVBoxLayout()

        self.ai_enabled_checkbox = QCheckBox("Aktivera AI-fallback")
        self.ai_enabled_checkbox.setToolTip(
            "Kryssa i för att aktivera. AI används när totalsumma-konfidens under 95 %."
        )
        provider_layout.addWidget(self.ai_enabled_checkbox)

        provider_layout.addWidget(QLabel("Välj AI-leverantör:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Claude"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        provider_layout.addWidget(_help_label(
            "Välj vilken AI-leverantör som ska användas för totalsumma-extraktion vid låg konfidens."
        ))

        provider_layout.addWidget(QLabel("API-nyckel:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Ange din API-nyckel här...")
        provider_layout.addWidget(self.api_key_input)
        show_key_btn = QPushButton("Visa")
        show_key_btn.setCheckable(True)
        show_key_btn.toggled.connect(
            lambda checked: self.api_key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
            )
        )
        provider_layout.addWidget(show_key_btn)
        provider_layout.addWidget(_help_label(
            "API-nyckeln används endast för anrop till vald leverantör. Lagras lokalt."
        ))

        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)

        # --- Model ---
        model_group = QGroupBox("Modell")
        model_group.setObjectName("ai_group_model")
        model_layout = QVBoxLayout()
        model_layout.addWidget(QLabel("Modell:"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(_help_label(
            "Modellnamn enligt leverantörens API (t.ex. gpt-4o, claude-3-5-sonnet)."
        ))
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # --- Thresholds ---
        thresholds_group = QGroupBox("Tröskelvärden")
        thresholds_group.setObjectName("ai_group_thresholds")
        thresholds_layout = QVBoxLayout()
        thresholds_layout.addWidget(_help_label(
            "AI anropas när totalsumma-konfidens är under detta värde (0–1). "
            "Gränsvärdet styrs i motorn vid körning (för närvarande 95 %)."
        ))
        thresholds_group.setLayout(thresholds_layout)
        layout.addWidget(thresholds_group)

        # --- Limits ---
        limits_group = QGroupBox("Gränser")
        limits_group.setObjectName("ai_group_limits")
        limits_layout = QVBoxLayout()
        limits_layout.addWidget(_help_label(
            "Timeout och max tokens styr hur långa AI-svar som tillåts. "
            "Konfigureras i motor/konfiguration; stöd i denna dialog planeras."
        ))
        limits_group.setLayout(limits_layout)
        layout.addWidget(limits_group)

        # --- Info ---
        info_label = QLabel(
            "AI används innan kandidatlistan visas: om konfidens under 95 % anropas AI och ev. "
            "förslag läggs högst upp. Spara för att aktivera/inaktivera. Gäller vid nästa körning."
        )
        info_label.setWordWrap(True)
        info_label.setProperty("class", "muted")
        layout.addWidget(info_label)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        remove_btn = QPushButton("Ta bort")
        remove_btn.setToolTip("Ta bort konfigurerad AI (provider, modell, nyckel)")
        remove_btn.clicked.connect(self._remove_config)
        button_layout.addWidget(remove_btn)

        test_btn = QPushButton("Testa anslutning")
        test_btn.setToolTip("Kontrollera att API-nyckel är angiven och att nätåtkomst finns.")
        test_btn.clicked.connect(self._on_test_connection)
        button_layout.addWidget(test_btn)

        button_layout.addStretch()
        cancel_btn = QPushButton("Avbryt")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Spara")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        layout.addLayout(button_layout)

    def _on_test_connection(self) -> None:
        """Stub: validate that API key is present and show short message (12-05)."""
        key = (self.api_key_input.text() or "").strip() or self.current_key
        if not key:
            QMessageBox.information(
                self,
                "Testa anslutning",
                "Ange API-nyckel först. Faktisk anslutningstest sker från motorn vid körning.",
            )
            return
        if len(key) < 10:
            QMessageBox.information(
                self,
                "Testa anslutning",
                "API-nyckeln verkar för kort. Kontrollera att du klistrat in hela nyckeln.\n\n"
                "Faktisk anslutningstest kräver engine/config-anrop och görs vid körning.",
            )
            return
        QMessageBox.information(
            self,
            "Testa anslutning",
            "API-nyckel angiven. Kontrollera att du har nätåtkomst till vald leverantör.\n\n"
            "Faktisk anslutningstest görs från motorn vid körning.",
        )

    def _reload_config(self) -> None:
        config = load_ai_config()
        self.current_enabled = config.get("enabled", False)
        self.current_provider = (config.get("provider") or "openai").lower()
        self.current_model = config.get("model") or _default_model(self.current_provider)
        self.current_key = config.get("api_key") or ""

    def _remove_config(self) -> None:
        clear_ai_config()
        self._reload_config()
        self.load_settings()

    def load_settings(self) -> None:
        self.status_label.setText(self._status_text())
        self.ai_enabled_checkbox.setChecked(self.current_enabled)

        provider_index = 0 if self.current_provider == "openai" else 1
        self.provider_combo.setCurrentIndex(provider_index)
        self._update_model_options()

        model_index = self.model_combo.findText(self.current_model)
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)
        else:
            self.model_combo.setCurrentText(self.current_model)

        if self.current_key:
            masked = self.current_key[:8] + "..." if len(self.current_key) > 8 else "***"
            self.api_key_input.setPlaceholderText(f"Nuvarande nyckel: {masked}")
        else:
            self.api_key_input.clear()
            self.api_key_input.setPlaceholderText("Ange din API-nyckel här...")

    def _on_provider_changed(self, provider_text: str) -> None:
        self._update_model_options()

    def _update_model_options(self) -> None:
        provider_text = self.provider_combo.currentText()
        self.model_combo.clear()
        if provider_text == "OpenAI":
            self.model_combo.addItems([
                "gpt-5-nano", "gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"
            ])
        elif provider_text == "Claude":
            self.model_combo.addItems([
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ])

    def save_settings(self) -> None:
        api_key_input = self.api_key_input.text().strip()
        if self.ai_enabled_checkbox.isChecked():
            if not api_key_input and not self.current_key:
                QMessageBox.warning(
                    self,
                    "API-nyckel saknas",
                    "Du måste ange en API-nyckel för att aktivera AI-fallback.",
                )
                return
            api_key = api_key_input if api_key_input else self.current_key
        else:
            api_key = api_key_input if api_key_input else self.current_key

        provider_text = self.provider_combo.currentText()
        provider = "openai" if provider_text == "OpenAI" else "claude"
        model = self.model_combo.currentText().strip()
        if not model:
            QMessageBox.warning(
                self, "Modell saknas", "Du måste välja eller ange en modell."
            )
            return

        enabled = self.ai_enabled_checkbox.isChecked()
        try:
            api_key_to_save = api_key if api_key else None
            set_ai_config(
                enabled=enabled,
                provider=provider,
                model=model,
                api_key=api_key_to_save,
            )
            QMessageBox.information(
                self,
                "Inställningar sparade",
                "AI-inställningarna har sparats och används vid nästa körning.",
            )
            self.accept()
        except Exception as e:
            logger.error("Failed to save AI settings: %s", e)
            QMessageBox.critical(
                self, "Fel", f"Kunde inte spara inställningar: {e}"
            )
