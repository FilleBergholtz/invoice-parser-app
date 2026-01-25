"""AI settings dialog: two-pane (provider list + detail form), edit/save, masked API key, Advanced collapsible (12-06)."""

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
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ...config import clear_ai_config, load_ai_config, set_ai_config

logger = logging.getLogger(__name__)

PROVIDER_IDS = ["openai", "claude"]
PROVIDER_LABELS = {"openai": "OpenAI", "claude": "Claude"}


def _default_model(provider: str) -> str:
    if provider == "claude":
        return "claude-3-opus-20240229"
    return "gpt-4-turbo-preview"


def _help_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setProperty("class", "muted")
    return lbl


class AISettingsDialog(QDialog):
    """Two-pane AI settings: left = provider list, right = detail form; Edit/Save/Cancel, masked API key, Advanced collapsible."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aiSettingsDialog")
        self.setWindowTitle("AI-inställningar")
        self.setMinimumSize(600, 440)
        self.setModal(True)

        self._reload_config()
        self.setup_ui()
        self._sync_from_config()

    def _reload_config(self) -> None:
        config = load_ai_config()
        self.current_enabled = config.get("enabled", False)
        self.current_provider = (config.get("provider") or "openai").lower()
        self.current_model = config.get("model") or _default_model(self.current_provider)
        self.current_key = config.get("api_key") or ""
        self._pending_key: Optional[str] = None  # new key typed in "Replace" flow

    def _status_text(self) -> str:
        c = load_ai_config()
        key = (c.get("api_key") or "").strip()
        prov = (c.get("provider") or "openai").lower()
        model = c.get("model") or _default_model(prov)
        enabled = c.get("enabled", False)
        prov_disp = PROVIDER_LABELS.get(prov, prov)
        if not key:
            return "Ingen AI konfigurerad"
        status = f"Konfigurerad: {prov_disp}, {model}"
        status += " · Aktiverad" if enabled else " · Inaktiverad"
        return status

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        # --- Status line ---
        status_frame = QFrame()
        status_frame.setObjectName("ai_settings_status")
        status_frame.setMinimumHeight(36)
        sl = QVBoxLayout(status_frame)
        sl.setContentsMargins(8, 4, 8, 4)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        sl.addWidget(self.status_label)
        main_layout.addWidget(status_frame)

        # --- Two-pane: list | form ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: provider list
        self.provider_list = QListWidget()
        self.provider_list.setObjectName("ai_provider_list")
        self.provider_list.setMaximumWidth(160)
        for pid in PROVIDER_IDS:
            item = QListWidgetItem(PROVIDER_LABELS[pid])
            item.setData(Qt.ItemDataRole.UserRole, pid)
            self.provider_list.addItem(item)
        self.provider_list.currentRowChanged.connect(self._on_provider_selected)
        splitter.addWidget(self.provider_list)

        # Right: detail form in scroll
        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(8, 0, 0, 0)

        self.ai_enabled_checkbox = QCheckBox("Aktivera AI-fallback")
        self.ai_enabled_checkbox.setToolTip(
            "Kryssa i för att aktivera. AI används när totalsumma-konfidens under 95 %."
        )
        form_layout.addWidget(self.ai_enabled_checkbox)

        form_layout.addWidget(QLabel("Modell:"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        form_layout.addWidget(self.model_combo)
        form_layout.addWidget(_help_label(
            "Modellnamn enligt leverantörens API (t.ex. gpt-4o, claude-3-5-sonnet)."
        ))

        form_layout.addWidget(QLabel("API-nyckel:"))
        key_row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Ange API-nyckel...")
        key_row.addWidget(self.api_key_input)
        self.replace_key_btn = QPushButton("Ersätt")
        self.replace_key_btn.setToolTip("Klicka för att ange eller byta API-nyckel")
        self.replace_key_btn.clicked.connect(self._on_replace_key)
        key_row.addWidget(self.replace_key_btn)
        self.show_key_btn = QPushButton("Visa")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.toggled.connect(
            lambda c: self.api_key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if c else QLineEdit.EchoMode.Password
            )
        )
        key_row.addWidget(self.show_key_btn)
        form_layout.addLayout(key_row)
        form_layout.addWidget(_help_label(
            "API-nyckeln lagras lokalt och används endast för vald leverantör."
        ))

        # Advanced (collapsible)
        self.advanced_btn = QPushButton("Avancerat ▾")
        self.advanced_btn.setCheckable(True)
        self.advanced_btn.setChecked(False)
        self.advanced_btn.clicked.connect(self._toggle_advanced)
        form_layout.addWidget(self.advanced_btn)

        self.advanced_widget = QFrame()
        self.advanced_widget.setVisible(False)
        adv_layout = QVBoxLayout(self.advanced_widget)
        thresholds_group = QGroupBox("Tröskelvärden")
        thresholds_group.setObjectName("ai_group_thresholds")
        tl = QVBoxLayout()
        tl.addWidget(_help_label(
            "AI anropas när totalsumma-konfidens är under 95 %. Gränsvärdet styrs i motorn."
        ))
        thresholds_group.setLayout(tl)
        adv_layout.addWidget(thresholds_group)
        limits_group = QGroupBox("Gränser")
        limits_group.setObjectName("ai_group_limits")
        ll = QVBoxLayout()
        ll.addWidget(_help_label(
            "Timeout och max tokens konfigureras i motor/konfiguration; stöd här planeras."
        ))
        limits_group.setLayout(ll)
        adv_layout.addWidget(limits_group)
        form_layout.addWidget(self.advanced_widget)

        scroll = QScrollArea()
        scroll.setWidget(form_container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        splitter.addWidget(scroll)
        splitter.setSizes([140, 400])

        main_layout.addWidget(splitter)

        # --- Buttons ---
        btn_layout = QHBoxLayout()
        remove_btn = QPushButton("Ta bort")
        remove_btn.setToolTip("Ta bort konfigurerad AI (provider, modell, nyckel)")
        remove_btn.clicked.connect(self._remove_config)
        btn_layout.addWidget(remove_btn)
        test_btn = QPushButton("Testa anslutning")
        test_btn.setToolTip("Kontrollera att API-nyckel är angiven.")
        test_btn.clicked.connect(self._on_test_connection)
        btn_layout.addWidget(test_btn)
        btn_layout.addStretch()
        cancel_btn = QPushButton("Avbryt")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("Spara")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    def _toggle_advanced(self) -> None:
        vis = self.advanced_btn.isChecked()
        self.advanced_widget.setVisible(vis)
        self.advanced_btn.setText("Avancerat ▾" if not vis else "Avancerat ▴")

    def _on_replace_key(self) -> None:
        self.api_key_input.clear()
        self.api_key_input.setPlaceholderText("Ange din API-nyckel här...")
        self.api_key_input.setFocus()
        self._pending_key = None

    def _on_provider_selected(self, row: int) -> None:
        if row < 0:
            return
        item = self.provider_list.item(row)
        if not item:
            return
        pid = item.data(Qt.ItemDataRole.UserRole) or "openai"
        self._update_model_options(pid)
        self._refresh_form_for_provider(pid)

    def _update_model_options(self, provider_id: str) -> None:
        self.model_combo.clear()
        if provider_id == "openai":
            self.model_combo.addItems([
                "gpt-5-nano", "gpt-4-turbo-preview", "gpt-4", "gpt-3.5-turbo"
            ])
        else:
            self.model_combo.addItems([
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ])

    def _refresh_form_for_provider(self, provider_id: str) -> None:
        """Populate form from current config when this provider is selected."""
        self._update_model_options(provider_id)
        if provider_id == self.current_provider:
            self.ai_enabled_checkbox.setChecked(self.current_enabled)
            model = self.current_model or _default_model(provider_id)
            idx = self.model_combo.findText(model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
            else:
                self.model_combo.setCurrentText(model)
            if self.current_key:
                self.api_key_input.clear()
                self.api_key_input.setPlaceholderText("•••••••• (klicka Ersätt för att ändra)")
            else:
                self.api_key_input.clear()
                self.api_key_input.setPlaceholderText("Ange din API-nyckel här...")
        else:
            self.ai_enabled_checkbox.setChecked(False)
            self.model_combo.setCurrentIndex(0)
            self.api_key_input.clear()
            self.api_key_input.setPlaceholderText("Ange din API-nyckel här...")

    def _sync_from_config(self) -> None:
        self.status_label.setText(self._status_text())
        row = PROVIDER_IDS.index(self.current_provider) if self.current_provider in PROVIDER_IDS else 0
        self.provider_list.setCurrentRow(row)
        self._refresh_form_for_provider(self.current_provider)

    def _on_test_connection(self) -> None:
        key = (self.api_key_input.text() or "").strip() or self._effective_key()
        if not key:
            QMessageBox.information(
                self, "Testa anslutning",
                "Ange API-nyckel först (klicka Ersätt och fyll i). Faktisk anslutningstest sker från motorn vid körning.",
            )
            return
        if len(key) < 10:
            QMessageBox.information(
                self, "Testa anslutning",
                "API-nyckeln verkar för kort. Kontrollera att du klistrat in hela nyckeln.",
            )
            return
        QMessageBox.information(
            self, "Testa anslutning",
            "API-nyckel angiven. Kontrollera att du har nätåtkomst till vald leverantör. Faktisk test görs vid körning.",
        )

    def _effective_key(self) -> str:
        t = (self.api_key_input.text() or "").strip()
        if t:
            return t
        row = self.provider_list.currentRow()
        if row >= 0 and self.provider_list.item(row).data(Qt.ItemDataRole.UserRole) == self.current_provider:
            return self.current_key or ""
        return ""

    def _remove_config(self) -> None:
        clear_ai_config()
        self._reload_config()
        self._sync_from_config()

    def save_settings(self) -> None:
        row = self.provider_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Välj leverantör", "Välj en leverantör i listan.")
            return
        provider_id = self.provider_list.item(row).data(Qt.ItemDataRole.UserRole) or "openai"
        model = self.model_combo.currentText().strip()
        if not model:
            QMessageBox.warning(self, "Modell saknas", "Du måste välja eller ange en modell.")
            return

        enabled = self.ai_enabled_checkbox.isChecked()
        api_key_val = (self.api_key_input.text() or "").strip()
        if enabled and not api_key_val and not (provider_id == self.current_provider and self.current_key):
            QMessageBox.warning(
                self, "API-nyckel saknas",
                "Du måste ange en API-nyckel för att aktivera AI-fallback.",
            )
            return
        api_key_to_save = api_key_val if api_key_val else (self.current_key if provider_id == self.current_provider else None)

        try:
            set_ai_config(
                enabled=enabled,
                provider=provider_id,
                model=model,
                api_key=api_key_to_save,
            )
            QMessageBox.information(
                self, "Inställningar sparade",
                "AI-inställningarna har sparats och används vid nästa körning.",
            )
            self.accept()
        except Exception as e:
            logger.error("Failed to save AI settings: %s", e)
            QMessageBox.critical(self, "Fel", f"Kunde inte spara inställningar: {e}")
