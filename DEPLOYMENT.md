# Deployment Guide: Invoice Parser App (Windows Desktop)

Denna guide beskriver hur man deployar Invoice Parser App som en fristående Windows Desktop-applikation eller använder CLI-verktyget.

> **Obs:** För dokumentation om tidigare deployment-metoder (Streamlit, API, Docker, Cloud), se `docs/legacy/deployment_legacy.md`.

---

## 📋 Innehåll

1. [Lokal Installation (Utvecklare)](#lokal-installation-utvecklare)
2. [Windows Installer](#windows-installer)
3. [CLI Användning](#cli-användning)
4. [Deployment Checklist](#deployment-checklist)

---

## 🖥️ Lokal Installation (Utvecklare)

### Förutsättningar

- Python 3.11 eller senare
- pip (Python package manager)
- Git

### Installation

```bash
# 1. Klona projektet
cd invoice-parser-app

# 2. Skapa virtual environment
python -m venv venv

# 3. Aktivera virtual environment
venv\Scripts\activate

# 4. Installera dependencies
pip install -e .
```

### Kör CLI

```bash
# Processa en faktura
python -m src.cli.main process invoice.pdf output/
```

---

## 💻 Windows Installer

### Bygg Windows .exe Executable

För att skapa en fristående Windows .exe-fil utan att användaren behöver Python installerat:

```bash
# 1. Installera PyInstaller (om det inte redan är installerat)
pip install pyinstaller

# 2. Bygg executable
python build_windows.py
```

Detta skapar:
- `dist/EPG_PDF_Extraherare.exe` - CLI-version
- `dist/EPG_PDF_Extraherare_GUI.exe` - GUI-version (Kommer i Fas 5)

### Skapa Windows Installer (.exe Setup)

Använd det medföljande scriptet för att skapa en installationsfil:

```bash
python build_installer.py
```

Detta skapar `installer/EPG_PDF_Extraherare_Setup.exe`.

**Vad installern gör:**
- ✅ Installerar appen i `C:\Program Files\EPG PDF Extraherare\`
- ✅ Skapar Start Menu-genvägar
- ✅ Skapar Desktop-genväg (valfritt)
- ✅ Lägger till avinstallationsstöd

**Krav för slutanvändare:**
- Endast Windows (ingen Python krävs)

---

## 🖥️ GUI Användning

Installerad applikation kan köras med grafiskt gränssnitt:

```bash
# Om installerad via setup.exe
& "C:\Program Files\EPG PDF Extraherare\EPG_PDF_Extraherare_GUI.exe"
```

**GUI-funktioner:**
- Drag & drop PDF-filer direkt i fönstret
- Välj input-fil via dialog
- Konfigurera output-mapp
- Visa bearbetningsstatus i realtid
- Automatisk öppning av output-mapp efter bearbetning

## ⚙️ CLI Användning

Installerad applikation kan också köras från kommandoraden.

```bash
# Om installerad via setup.exe
& "C:\Program Files\EPG PDF Extraherare\EPG_PDF_Extraherare.exe" --input fakturor/ --output output/
```

**Argument:**
- `--input`: Sökväg till PDF-fil eller mapp
- `--output`: Mapp där resultat ska sparas (Default: Documents/EPG PDF Extraherare/output)
- `--verbose`: Visa mer detaljerad loggning
- `--fail-fast`: Stanna vid första felet vid batch-körning

---

## 📝 Deployment Checklist

### Före Release

- [ ] Alla dependencies är listade i `pyproject.toml`
- [ ] Versionnumret är uppdaterat
- [ ] Tester passerar (`pytest`)
- [ ] Byggprocessen fungerar (`python build_windows.py`)
- [ ] Installer-skriptet fungerar (`python build_installer.py`)
- [ ] Installerad app startar korrekt på ren Windows-miljö

### Efter Release

- [ ] Verifiera versionsnummer i installerad app
- [ ] Testa avinstallation

---

**Senast uppdaterad:** 2026-01-24
**Version:** 1.0.1

> **Notera:** GUI-versionen använder PySide6 (Qt-baserad desktop applikation). Web-baserade alternativ (Streamlit/FastAPI) är dokumenterade i `docs/legacy/deployment_legacy.md`.
