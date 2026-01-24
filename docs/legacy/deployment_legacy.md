# Deployment Guide (Legacy)

Detta dokument beskriver deployment-metoder som inte längre är primära mål för projektet (Streamlit, FastAPI, Docker, Cloud). Projektet fokuserar nu på Windows Desktop (Offline-first).

---

## 📋 Innehåll

1. [Lokal Deployment](#lokal-deployment)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Deployment](#cloud-deployment)
4. [Production Considerations](#production-considerations)
5. [Troubleshooting](#troubleshooting)

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
