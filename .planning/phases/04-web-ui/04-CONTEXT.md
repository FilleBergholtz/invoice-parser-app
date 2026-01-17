# Phase 4: Web UI - Context

**Datum:** 2026-01-17  
**Status:** Planning

---

## Mål

Skapa ett webbaserat användargränssnitt för Invoice Parser App som möjliggör:
- Uppladdning och batch-bearbetning av fakturor via webbläsare
- Visuell granskning av extraherade data
- Review workflow med klickbara PDF-länkar för verifiering
- Statusöversikt och filtrering (OK/PARTIAL/REVIEW)
- Nedladdning av Excel-filer och review-rapporter

---

## Bakgrund

**Nuvarande situation:**
- Systemet har endast CLI (Command Line Interface)
- Batch-bearbetning fungerar väl via kommandorad
- Excel-export och review-rapporter genereras lokalt
- Ingen visuell feedback eller interaktiv granskning

**Behov:**
- Användare vill kunna ladda upp fakturor via webbläsare
- Användare behöver visuell feedback under bearbetning
- Review workflow kräver klickbara länkar till PDF:er för verifiering
- Statusöversikt behövs för att snabbt identifiera problematiska fakturor

---

## Teknisk kontext

**Befintlig stack:**
- Python 3.11+ backend
- CLI interface i `src/cli/main.py`
- Pipeline är modulär och kan användas som bibliotek
- Excel-export och review-rapporter redan implementerade

**Rekommendationer för Web UI:**
- **Backend:** FastAPI eller Flask för REST API
- **Frontend:** React eller Vue.js för interaktiv UI
- **Alternativ:** Streamlit för snabb prototyp (Python-only, enklare men mindre flexibel)

**Överväganden:**
- Streamlit: Snabbast att implementera, Python-only, bra för prototyp
- FastAPI + React: Mer flexibel, bättre för produktion, kräver mer setup
- Flask + Jinja2: Enklare än React, men mindre interaktiv

---

## Krav från REQUIREMENTS.md

**UI-01:** Review workflow med klickbara PDF-länkar (öppnar PDF på specifik sida/bbox för verifiering)  
**UI-02:** Web UI för fakturabearbetning och granskning  
**UI-03:** API för extern systemintegration

---

## Success Criteria

1. Användare kan ladda upp PDF-fakturor via webbläsare
2. Systemet visar bearbetningsstatus i realtid
3. Användare kan se lista över bearbetade fakturor med status (OK/PARTIAL/REVIEW)
4. Användare kan filtrera och sortera fakturor efter status
5. Användare kan klicka på fakturor för att se detaljerad information
6. Review workflow: Klickbara länkar öppnar PDF på rätt sida/position
7. Användare kan ladda ner Excel-filer och review-rapporter
8. API tillgängligt för extern systemintegration

---

## Arkitekturöverväganden

**Alternativ 1: Streamlit (Rekommenderat för MVP)**
- Fördelar: Snabb implementation, Python-only, inbyggd filuppladdning, enkel deployment
- Nackdelar: Mindre flexibel, begränsad anpassning, kan bli långsam vid stora volymer

**Alternativ 2: FastAPI + React**
- Fördelar: Mycket flexibel, bra prestanda, professionell stack, bättre för produktion
- Nackdelar: Mer komplex setup, kräver frontend-utveckling, mer dependencies

**Alternativ 3: Flask + Jinja2 Templates**
- Fördelar: Enklare än React, Python-only backend, server-side rendering
- Nackdelar: Mindre interaktiv, begränsad användarupplevelse

---

## Beslut som behöver tas

1. **Vilket UI-ramverk?** (Streamlit vs FastAPI+React vs Flask)
2. **Hur hanteras filuppladdning?** (Temporär lagring, validering, storleksbegränsningar)
3. **Hur hanteras PDF-visning?** (PDF.js i webbläsare, server-side rendering, extern viewer)
4. **Hur hanteras asynkron bearbetning?** (Background jobs, WebSockets, polling)
5. **Hur hanteras autentisering?** (Ingen för MVP, eller enkel auth?)
6. **Hur deployas?** (Lokal server, Docker, cloud?)

---

## Nästa steg

1. Diskutera och besluta om UI-ramverk
2. Skapa plan för Phase 4 med specifika plans
3. Implementera MVP med valt ramverk
4. Testa med riktiga fakturor
5. Iterera baserat på feedback

---

*Context sammanställd: 2026-01-17*
