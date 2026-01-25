"""About dialog with tabs: Om appen and Hjälp."""

from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QLabel, QPushButton,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from .. import resources_rc  # noqa: F401 - register icons
from ...config import get_app_version, get_app_name


def _author_name() -> str:
    """Creator credit. Placeholder when not in pyproject."""
    return "Filip Bergholtz"


class AboutDialog(QDialog):
    """Dialog with tabs 'Om appen' (name, version, description, credit) and 'Hjälp' (usage + troubleshooting)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aboutDialog")
        self.setWindowTitle("Om EPG PDF Extraherare")
        self.setWindowIcon(QIcon(":/icons/app.svg"))
        self.setMinimumSize(420, 380)
        self.setModal(True)

        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.addTab(self._build_om_appen_tab(), "Om appen")
        tabs.addTab(self._build_hjalp_tab(), "Hjälp")
        layout.addWidget(tabs)

        close_btn = QPushButton("Stäng")
        close_btn.setDefault(True)
        close_btn.setAutoDefault(True)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _build_om_appen_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        name = QLabel(get_app_name())
        name.setObjectName("aboutAppName")
        name.setStyleSheet("font-size: 14pt; font-weight: bold; color: #0f172a;")
        layout.addWidget(name)

        version = QLabel(f"Version {get_app_version()}")
        version.setStyleSheet("color: #64748b; font-size: 10pt;")
        layout.addWidget(version)

        desc = QLabel(
            "Appen analyserar PDF-fakturor: öppna PDF → kör analys → granska resultat och varningar "
            "→ välj kandidat vid behov → exportera till Excel."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #334155; margin-top: 8px;")
        layout.addWidget(desc)

        author = QLabel(f"Skapad av: {_author_name()}")
        author.setStyleSheet("color: #64748b; margin-top: 12px; font-size: 10pt;")
        layout.addWidget(author)

        layout.addStretch()
        return tab

    def _build_hjalp_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        steps_label = QLabel("Så här använder du appen:")
        steps_label.setStyleSheet("font-weight: bold; color: #0f172a;")
        layout.addWidget(steps_label)

        steps = [
            "1. Öppna PDF – välj eller dra och släpp en faktura-PDF.",
            "2. Kör analys – klicka Kör för att extrahera data.",
            "3. Granska resultat – kontrollera varningar och föreslagna värden.",
            "4. Välj kandidat vid behov – om flera förslag finns, välj rätt rad.",
            "5. Exportera till Excel – spara till utdatamappen.",
        ]
        for s in steps:
            lbl = QLabel(s)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #334155;")
            layout.addWidget(lbl)

        layout.addSpacing(14)
        trouble_label = QLabel("Felsökning")
        trouble_label.setStyleSheet("font-weight: bold; color: #0f172a;")
        layout.addWidget(trouble_label)

        trouble = [
            "• Saknade resultat: Kontrollera att PDF:en innehåller text (inte bara bilder). Aktivera OCR i inställningarna om sidan skannats.",
            "• Fel eller konstiga värden: Använd \"Välj kandidat\" och spara rätt värde så lär systemet sig.",
            "• Låg konfidens / AI: Aktivera AI-inställningar (verktygsfältet Inställningar eller menyn AI → AI-inställningar) om du vill att osäkra fält förbättras med AI.",
        ]
        for t in trouble:
            lbl = QLabel(t)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #64748b; font-size: 9pt;")
            layout.addWidget(lbl)

        layout.addStretch()
        return tab
