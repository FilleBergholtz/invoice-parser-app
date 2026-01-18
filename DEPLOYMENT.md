# Deployment Guide: Invoice Parser App

Denna guide beskriver hur man deployar Invoice Parser App i olika miljöer.

---

## 📋 Innehåll

1. [Lokal Deployment](#lokal-deployment)
2. [Docker Deployment](#docker-deployment)
3. [Windows Installer](#windows-installer)
4. [Cloud Deployment](#cloud-deployment)
5. [Production Considerations](#production-considerations)
6. [Troubleshooting](#troubleshooting)

---

## 🖥️ Lokal Deployment

### Förutsättningar

- Python 3.11 eller senare
- pip (Python package manager)
- Git (för att klona projektet)

### Installation

```bash
# 1. Klona eller navigera till projektet
cd invoice-parser-app

# 2. Skapa virtual environment (rekommenderat)
python -m venv venv

# 3. Aktivera virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Installera dependencies
pip install -e .
```

### Kör Streamlit UI

```bash
# Starta Streamlit-appen
python -m streamlit run run_streamlit.py

# Eller med specifik port
python -m streamlit run run_streamlit.py --server.port 8501
```

Appen öppnas automatiskt i webbläsaren på `http://localhost:8501`

**Alternativ:** Använd startfilen:
```bash
streamlit run run_streamlit.py
```

### Kör FastAPI

```bash
# Starta API:et
python run_api.py

# Eller direkt med uvicorn
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

API:et startar på `http://localhost:8000`
- API-dokumentation: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Kör CLI

```bash
# Processa en faktura
python -m src.cli.main process invoice.pdf output/

# Batch-bearbetning
python -m src.cli.main batch input_folder/ output/
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

Detta skapar `dist/EPG_PDF_Extraherare.exe` som kan köras direkt på Windows utan Python.

> **ℹ️ Vad inkluderas i bygget?**
> 
> **Inkluderas:**
> - ✅ All kod från `src/` mappen (applikationskod)
> - ✅ Alla Python-dependencies (pdfplumber, pandas, openpyxl, etc.)
> - ✅ Python runtime (inbyggd i executable)
> 
> **Exkluderas (inkluderas INTE):**
> - ❌ Testfiler (`test_*.py`, `tests/` mappen)
> - ❌ Analysfiler (`analyze_*.py`)
> - ❌ Output-mappar och genererade filer
> - ❌ Development-verktyg (pytest, unittest)
> - ❌ Källkod-filer som inte används av applikationen
> 
> Endast produktionskod inkluderas - testfiler och output-mappar behövs inte i den färdiga produkten.

### Skapa Windows Installer (.exe Setup)

För att skapa en professionell installer med NSIS:

> **⚠️ Viktigt:** NSIS behövs BARA för utvecklare som bygger installer-filen. Slutanvändare behöver INTE ha NSIS installerat - de behöver bara köra den färdiga `EPG_PDF_Extraherare_Setup.exe`-filen.

#### Förutsättningar (för utvecklare)

- Executable måste vara byggd först (se ovan)
- [NSIS (Nullsoft Scriptable Install System)](https://nsis.sourceforge.io/Download) måste vara installerat på utvecklarens dator för att bygga installer-filen

**Notera:** Om NSIS inte är installerat kan du ändå använda den färdiga `.exe`-filen direkt från `dist/` mappen och distribuera den till slutanvändare.

#### Steg

1. **Bygg executable först:**
   ```bash
   python build_windows.py
   ```
   
   > **ℹ️ Automatisk rensning:** Scriptet rensar automatiskt gamla `build/` och `dist/` mappar innan nytt bygge. Du behöver inte manuellt ta bort gamla filer.

2. **Kompilera NSIS installer:**
   
   **Alternativ A: Använd build_installer.py (rekommenderat)**
   ```bash
   python build_installer.py
   ```
   Detta script hittar automatiskt NSIS och bygger installern. Gamla installer-filer rensas automatiskt innan nytt bygge.

   **Alternativ B: Manuellt med makensis**
   ```bash
   cd installer
   makensis installer.nsi
   ```

   Detta skapar `EPG_PDF_Extraherare_Setup.exe` i `installer/`-mappen.

3. **Distribuera installer:**
   - `EPG_PDF_Extraherare_Setup.exe` kan distribueras till slutanvändare
   - **Slutanvändare behöver INTE ha NSIS eller Python installerat** - de behöver bara köra installer-filen
   - Installern installerar appen i `C:\Program Files\EPG PDF Extraherare\`
   - Skapar Start Menu-genvägar
   - Valfritt: Desktop-genväg

#### Installer-funktioner

- ✅ Automatisk installation till Program Files
- ✅ Start Menu-genvägar
- ✅ Desktop-genväg (valfritt)
- ✅ Integrering med Windows Add/Remove Programs
- ✅ Avinstallationsstöd
- ✅ Version-hantering

#### Användning av installerad app

Efter installation kan användaren:

```bash
# Använd direkt från kommandoraden (om PATH är konfigurerad)
EPG_PDF_Extraherare.exe --input fakturor/ --output output/

# Eller navigera till installationsmappen
cd "C:\Program Files\EPG PDF Extraherare"
.\EPG_PDF_Extraherare.exe --input fakturor/ --output output/
```

**Notera:** Default output-mapp används automatiskt om `--output` inte anges:
- `%USERPROFILE%\Documents\EPG PDF Extraherare\output\`

#### Avinstallation

Användare kan avinstallera via:
- **Settings → Apps → EPG PDF Extraherare → Uninstall**
- Eller kör `Uninstall.exe` från installationsmappen

#### För slutanvändare

**Slutanvändare behöver INTE:**
- ❌ Python installerat
- ❌ NSIS installerat
- ❌ Några dependencies eller verktyg

**Slutanvändare behöver BARA:**
- ✅ Windows-operativsystem
- ✅ Installer-filen: `EPG_PDF_Extraherare_Setup.exe`

Installationen är helt fristående och kräver inga extra verktyg eller dependencies.

---

## 🐳 Docker Deployment

### Dockerfile för Streamlit

Skapa `Dockerfile.streamlit`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Installera system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Kopiera projektfiler
COPY pyproject.toml ./
COPY src/ ./src/
COPY run_streamlit.py ./

# Installera Python dependencies
RUN pip install --no-cache-dir -e .

# Exponera port
EXPOSE 8501

# Starta Streamlit
CMD ["streamlit", "run", "run_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Dockerfile för FastAPI

Skapa `Dockerfile.api`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Installera system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Kopiera projektfiler
COPY pyproject.toml ./
COPY src/ ./src/
COPY run_api.py ./

# Installera Python dependencies
RUN pip install --no-cache-dir -e .

# Exponera port
EXPOSE 8000

# Starta FastAPI
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

Skapa `docker-compose.yml`:

```yaml
version: '3.8'

services:
  streamlit:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    ports:
      - "8501:8501"
    volumes:
      - ./data:/app/data
    environment:
      - STREAMLIT_SERVER_PORT=8501
    restart: unless-stopped

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000
    restart: unless-stopped
```

### Bygg och kör med Docker

```bash
# Bygg och starta alla services
docker-compose up -d

# Visa logs
docker-compose logs -f

# Stoppa services
docker-compose down

# Bygg om efter kodändringar
docker-compose up -d --build
```

### Individuella Docker-kommandon

**Streamlit:**
```bash
# Bygg image
docker build -f Dockerfile.streamlit -t invoice-parser-streamlit .

# Kör container
docker run -p 8501:8501 invoice-parser-streamlit
```

**FastAPI:**
```bash
# Bygg image
docker build -f Dockerfile.api -t invoice-parser-api .

# Kör container
docker run -p 8000:8000 invoice-parser-api
```

---

## ☁️ Cloud Deployment

### Streamlit Cloud

Streamlit Cloud är enkelt för Streamlit-appar:

1. **Pusha kod till GitHub**
   ```bash
   git push origin main
   ```

2. **Gå till [streamlit.io/cloud](https://streamlit.io/cloud)**

3. **Koppla GitHub-repo och välj branch**

4. **Konfigurera:**
   - Main file: `run_streamlit.py`
   - Python version: 3.11

5. **Deploy!**

### Heroku

**För Streamlit:**

Skapa `Procfile`:
```
web: streamlit run run_streamlit.py --server.port=$PORT --server.address=0.0.0.0
```

Skapa `runtime.txt`:
```
python-3.11.0
```

Deploy:
```bash
heroku create invoice-parser-app
git push heroku main
```

**För FastAPI:**

Skapa `Procfile`:
```
web: uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
```

Deploy:
```bash
heroku create invoice-parser-api
git push heroku main
```

### Azure App Service

**För Streamlit:**

1. Skapa `startup.sh`:
```bash
#!/bin/bash
streamlit run run_streamlit.py --server.port=8000 --server.address=0.0.0.0
```

2. Använd Azure CLI:
```bash
az webapp create --resource-group myResourceGroup --plan myAppServicePlan --name invoice-parser --runtime "PYTHON:3.11"
az webapp config set --startup-file startup.sh
```

**För FastAPI:**

1. Skapa `startup.sh`:
```bash
#!/bin/bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

2. Deploy:
```bash
az webapp up --name invoice-parser-api --runtime "PYTHON:3.11"
```

### AWS Elastic Beanstalk

**För FastAPI:**

1. Skapa `.ebextensions/python.config`:
```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: src.api.main:app
```

2. Deploy:
```bash
eb init -p python-3.11 invoice-parser
eb create invoice-parser-env
eb deploy
```

### Google Cloud Run

**För FastAPI:**

1. Skapa `Dockerfile` (se ovan)

2. Deploy:
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/invoice-parser-api
gcloud run deploy invoice-parser-api --image gcr.io/PROJECT-ID/invoice-parser-api --platform managed
```

---

## 🔒 Production Considerations

### Säkerhet

1. **API Authentication**
   - Lägg till API keys eller OAuth2
   - Implementera rate limiting
   - Använd HTTPS (TLS/SSL)

2. **Environment Variables**
   - Använd `.env` filer för känslig data
   - Lägg aldrig in secrets i kod
   - Använd secrets management (Azure Key Vault, AWS Secrets Manager)

3. **Input Validation**
   - Validera filstorlekar (max 10MB rekommenderat)
   - Begränsa antal filer per batch
   - Sanitize filnamn

### Performance

1. **Caching**
   - Cache resultat för återkommande fakturor
   - Använd Redis för session storage

2. **Asynkron Bearbetning**
   - Använd background job queue (Celery, RQ)
   - Webhooks för notifikationer när bearbetning är klar

3. **Database**
   - Uppgradera från in-memory till SQLite/PostgreSQL
   - Indexera på invoice_id och status

### Monitoring

1. **Logging**
   - Strukturerad logging (JSON format)
   - Log levels: DEBUG, INFO, WARNING, ERROR
   - Centraliserad loggning (ELK stack, CloudWatch)

2. **Metrics**
   - Bearbetningstid per faktura
   - Success/failure rates
   - API response times

3. **Health Checks**
   - `/health` endpoint för API
   - Monitoring alerts

### Scalability

1. **Horizontal Scaling**
   - Load balancer för API
   - Multiple Streamlit instances (med session state sync)

2. **Resource Limits**
   - CPU och minne per container
   - Timeout för långa requests
   - Queue system för batch-jobb

---

## 🛠️ Environment Configuration

### Environment Variables

Skapa `.env` fil:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Database (för framtida användning)
DATABASE_URL=sqlite:///./invoices.db

# Security
API_KEY=your-secret-api-key-here
ALLOWED_ORIGINS=http://localhost:8501,https://yourdomain.com

# File Upload Limits
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_BATCH=50
```

Läs environment variables i kod:

```python
import os
from dotenv import load_dotenv

load_dotenv()

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
```

---

## 📊 Database Setup (Framtida)

### SQLite (Enkel)

```python
# src/api/storage.py
import sqlite3
from pathlib import Path

DB_PATH = Path("invoices.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id TEXT PRIMARY KEY,
            filename TEXT,
            status TEXT,
            invoice_number TEXT,
            total_amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
```

### PostgreSQL (Production)

```python
# Använd SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

---

## 🔍 Troubleshooting

### Vanliga Problem

**Problem: Streamlit kan inte starta**
```bash
# Lösning: Kontrollera att porten inte är upptagen
netstat -ano | findstr :8501  # Windows
lsof -i :8501  # Linux/Mac

# Använd annan port
streamlit run run_streamlit.py --server.port 8502
```

**Problem: API returnerar 500 errors**
```bash
# Lösning: Kontrollera logs
# Aktivera verbose logging i uvicorn
uvicorn src.api.main:app --log-level debug
```

**Problem: PDF-filer kan inte processas**
```bash
# Lösning: Kontrollera att pdfplumber är installerat
pip install pdfplumber

# Kontrollera PDF-filens integritet
python -c "import pdfplumber; pdf = pdfplumber.open('test.pdf'); print(len(pdf.pages))"
```

**Problem: Memory errors vid stora batch-jobb**
```bash
# Lösning: Processera i mindre batches
# Eller öka container memory limits
```

### Debug Mode

**Streamlit:**
```bash
streamlit run run_streamlit.py --logger.level=debug
```

**FastAPI:**
```bash
uvicorn src.api.main:app --reload --log-level debug
```

---

## 📝 Deployment Checklist

### Före Deployment

- [ ] Alla dependencies är listade i `pyproject.toml`
- [ ] Environment variables är dokumenterade
- [ ] Secrets är konfigurerade (inte i kod)
- [ ] Logging är konfigurerat
- [ ] Health checks är implementerade
- [ ] Error handling är på plats
- [ ] Rate limiting är konfigurerat (för API)
- [ ] HTTPS är aktiverat (för production)

### Efter Deployment

- [ ] Verifiera att appen startar korrekt
- [ ] Testa alla endpoints/funktioner
- [ ] Kontrollera logs för errors
- [ ] Verifiera att monitoring fungerar
- [ ] Testa med riktiga fakturor
- [ ] Dokumentera deployment URL:er

---

## 🚀 Quick Start Commands

### Lokal Development

```bash
# Streamlit
python -m streamlit run run_streamlit.py

# FastAPI
python run_api.py

# CLI (default output används automatiskt om --output inte anges)
python -m src.cli.main --input fakturor/
```

### Docker

```bash
# Alla services
docker-compose up -d

# Endast Streamlit
docker run -p 8501:8501 invoice-parser-streamlit

# Endast API
docker run -p 8000:8000 invoice-parser-api
```

### Production

```bash
# Med gunicorn (för FastAPI)
gunicorn src.api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Med systemd service (Linux)
sudo systemctl start invoice-parser-api
sudo systemctl enable invoice-parser-api
```

---

## 📚 Ytterligare Resurser

- [Streamlit Deployment](https://docs.streamlit.io/deploy)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Python Production Checklist](https://docs.python-guide.org/writing/deployment/)

---

**Senast uppdaterad:** 2026-01-17  
**Version:** 1.0.0
