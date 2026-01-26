# Phase 17 — AI-policy (fallback only)

## Målbild (AI-01, AI-02)
AI används endast som sista fallback när deterministiska regler saknas eller faller utanför förväntade mönster. EDI-liknande fakturor med text-layer ska i normalfallet aldrig gå via AI, utan lösas deterministiskt med tydlig validering och REVIEW vid osäkerhet.

## Var i pipeline AI-gating ska ligga
Målet är att styra beslutet centralt och tidigt nog för att stoppa onödiga AI-anrop, men sent nog för att deterministiska regler faktiskt hinner köras.

1. **Primär gate: efter deterministisk extraktion + validering**
   - Efter att text-layer/OCR tokens har extraherats och regelbaserade parsers kört (header + lines).
   - Om kritiska fält kan extraheras deterministiskt och validering passerar → **ingen AI**.
   - Om validering faller: kör deterministisk fallback (t.ex. andra parser‑läge) innan AI.

2. **Central policyfunktion i routing**
   - Samla beslut i en policyfunktion som tar in:
     - `extraction_source`, `text_quality`, `ocr_quality`, `critical_fields_conf`, `validation_results`
     - “EDI-likhet” (heuristikpoäng)
   - Denna funktion avgör om AI överhuvudtaget är tillåten för fakturan.

3. **Compare‑path / batch‑flöde**
   - När compare‑path väljer bästa textkälla: kör AI-gating **efter** valet (pdfplumber/OCR).
   - AI‑gating ska se samma beslutsgrund som normal‑path för att undvika två olika regelset.

## Heuristiker för att detektera EDI‑liknande text‑layer
Syftet är att klassificera fakturor där deterministisk parsing bör vara huvudväg.

### Förslag på signaler (samlad poäng/regel)
1. **Text-layer finns och är stabil**
   - Per sida: `use_text_layer == true` enligt text‑layer routing.
   - Hög `text_quality` och många tokens/ord per sida.

2. **Strukturerade ankare i text**
   - Förekomst av typiska rubriker: “Faktura”, “Fakturanr”, “Org.nr”, “Nettobelopp exkl. moms”, “Moms”, “Att betala”.
   - Sidindikatorer: “Sida x/y”, “Page x/y”.

3. **Tabell‑lik struktur**
   - Regelbunden förekomst av rader med flera numeriska kolumner.
   - Upprepade “kolumn‑ankare” (t.ex. Artikel/Benämning/Antal/Pris/Moms/Belopp).
   - Liknande x‑positioner för belopp per rad (tecken på kolumnlayout).

4. **Låg OCR‑beroende**
   - Inga sidor kräver OCR i routing (eller endast undantagsvis).
   - OCR‑confidence behöver inte användas om text‑layer är tillräcklig.

### Enkel beslutspolicy (exempel)
- **EDI‑lik** om:
  - alla sidor har `use_text_layer == true`, **och**
  - minst 2 ankare från rubriklistan matchar, **och**
  - tabellmönster hittas (t.ex. minst N rader med moms% + belopp).

## Hur AI undviks när deterministiska regler finns
1. **Tvinga deterministisk väg som default**
   - AI tillåts inte så länge kritiska fält (fakturanr + totalsumma) kan extraheras av regler och validering passerar.

2. **Regel‑först, AI‑sist**
   - Kör först standardparser → validering.
   - Vid mismatch: kör deterministisk fallback (alternativa regex/kolumn‑läge).
   - Endast om reglerna *inte* hittar fält eller mönstren saknas → AI.

3. **Konfigurerbar policy**
   - En tydlig `ai_policy` i config: t.ex. `allow_ai_for_edi=false`, `force_review_on_edi_fail=true`.
   - Möjlighet att tillfälligt slå på AI för EDI i debugläge, men default = av.

4. **Förklarade beslut**
   - Spara `reason_flags` i resultatet (t.ex. `["edi_like", "validation_passed"]` eller `["no_patterns", "ai_allowed"]`).
   - Viktigt för spårbarhet och att kunna justera heuristiker.

## Risker
- **Falsk EDI‑klassning** → AI blockeras för fakturor som egentligen behöver AI.
- **Falsk icke‑EDI** → AI används onödigt på fakturor som borde gå deterministiskt.
- **För hårda ankare** → EDI‑fakturor utan vissa rubriker flaggas fel.
- **Ofullständig validering** → AI triggas trots att deterministiska regler egentligen räcker.
- **Policy‑spridning** → flera olika policybeslut i olika kodvägar (normal/compare) ger inkonsistens.

## Testidéer
1. **Enhetstester (policy)**
   - EDI‑lik text‑layer + validering OK → AI ej tillåten.
   - EDI‑lik + validering fail + deterministisk fallback lyckas → AI ej tillåten.
   - EDI‑lik + inga mönster hittas → AI tillåten endast om policy säger så.

2. **Integrationstester (pipeline)**
   - Mixed‑PDF med stark text‑layer → AI ska inte användas, endast deterministisk.
   - OCR‑tung faktura utan text‑layer → AI tillåten efter regler + validering faller.
   - Verifiera att compare‑path och normal‑path ger samma AI‑beslut.

3. **Regression**
   - Kör befintliga testsviter för parsing och validation.
   - Kontrollera att inga AI‑anrop sker i EDI‑korpus när heuristiken uppfylls.
