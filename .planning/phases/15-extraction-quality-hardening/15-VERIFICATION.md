# Phase 15: Extraction quality hardening — Verification

**Skapad:** 2026-01-25

Verifiering av OCR confidence-användning, routing-stabilitet och parser-robusthet enligt 15-CONTEXT.md. Uppdateras när planer (15-01 …) är definierade.

---

## 1. Per-plan checks (from SUMMARY)

| Plan | Check | Resultat |
|------|--------|----------|
| *(planer ej definierade än)* | — | — |

*Fyll i efter /gsd:plan-phase 15.*

---

## 2. Success criteria (15-CONTEXT)

1. **OCR confidence:** Mått används konsekvent i routing och run_summary; trösklar dokumenterade eller konfigurerbara.
2. **Routing:** Inget onödigt flipp mellan metoder vid marginella inputs; vision_reason och method_used konsekventa.
3. **Parser robustness:** Header/total/line-parsers hanterar tom/brusig/konstig text utan krasch; REVIEW eller tomt fält där lämpligt.
4. Befintliga tester och Phase 14-verifiering förblir passerande.

---

## 3. Automatiska tester

Kör relevanta testmoduler efter implementation:

```bash
python -m pytest tests/ -v -k "ocr token text_quality run_summary header total line_parser"
```

*(Anpassa -k efter faktiska testfiler.)*

---

## 4. Manuell verifiering (rekommenderas)

1. **Routing:** Kör engine med PDF:er som ger marginell text_quality/confidence; kontrollera att method_used och vision_reason inte flippar vid små variationer.
2. **Parser robustness:** Testa med PDF:er eller mocks med tom text, enbart specialtecken, eller extremt långa rader; förvänta REVIEW eller tomma fält, ingen krasch.
3. **OCR confidence:** Om trösklar eller logg/UI läggs till, verifiera att värdena stämmer med run_summary och routing.

---

*Skapad 2026-01-25 — Phase 15 extraction quality hardening*
