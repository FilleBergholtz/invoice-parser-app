---
status: testing
phase: 08-ai-integration
source: [08-01-SUMMARY.md, 08-02-SUMMARY.md, 08-03-SUMMARY.md]
started: "2026-01-25T00:00:00Z"
updated: "2026-01-25T00:00:00Z"
---

## Current Test

**Test 3** – Provider-väljning (OpenAI/Claude)

Med AI_PROVIDER=openai resp. claude och motsvarande API-nyckel: rätt provider används. Verifiera via logg eller att båda vägarna fungerar. Svara "pass", "skip" eller beskriv problem.

## Tests

### 1. AI av eller API-nyckel saknas – ingen krasch
expected: |
  När AI är av (AI_ENABLED=false) eller OPENAI_API_KEY/ANTHROPIC_API_KEY saknas: pipeline körs mot en PDF, ger heuristik-resultat (totalsumma från footer-extraktion), ingen krasch eller ohanterat undantag.
result: pass

### 2. AI aktiveras vid låg konfidens (< 0.95)
expected: |
  Med AI aktiverat (API-nyckel satt, AI_ENABLED=true eller default) och en PDF som ger totalsumma-konfidens < 0.95: pipeline använder AI-fallback (synligt i logg t.ex. "AI fallback" / "extract_total_with_ai" eller förbättrat resultat). Ingen krasch.
result: pending

### 3. Provider-väljning (OpenAI/Claude)
expected: |
  Med AI_PROVIDER=openai respektive AI_PROVIDER=claude (och motsvarande API-nyckel): rätt provider används vid AI-anrop. Verifieras via logg eller att båda vägarna fungerar vid låg konfidens.
result: pending

### 4. AI-resultat valideras mot radsumma; konfidens kan höjas
expected: |
  När AI returnerar en totalsumma som matchar summan av radbelopp (±1 SEK): systemet använder AI-resultatet och kan höja konfidensen (boost). Observabelt som korrekt totalsumma i output och eventuellt högre konfidens/OK-status.
result: pending

### 5. Felhantering vid timeout eller API-fel
expected: |
  Vid ogiltig API-nyckel, timeout eller nätverksfel: pipeline kraschar inte; heuristik-resultat används, ev. varning i logg. Batch/CLI avslutas normalt.
result: pending

## Summary

total: 5
passed: 2
issues: 0
pending: 3
skipped: 0

## Gaps

