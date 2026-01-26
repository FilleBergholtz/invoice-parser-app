# Fas 19: Svensk talnormalisering

## Mal och krav
- Roadmap: Alla belopp parsas konsekvent som Decimal med svensk notation.
- Krav: NUM-01, NUM-02, NUM-03, NUM-04.
- Fokus: En gemensam normaliseringsfunktion som ateranvands i alla parsare.

## Normaliseringsregler (svensk notation)
1. Trimma och acceptera endast taltecken, mellanslag och separatorer.
2. Ta bort mellanslag som tusentalsseparator (t.ex. "1 234 567,89").
3. Ta bort punkt som tusentalsseparator endast nar punkten foljs av exakt tre siffror
   och antingen slut pa strangen eller nasta separator/icke-siffra.
4. Byt kommatecken till punkt for Decimal (t.ex. "12,50" -> "12.50").
5. Returnera alltid `Decimal` eller kasta kontrollerat fel om formatet inte ar giltigt.

## Regex- och parse-approach (undvik falsk punktborttagning)
- Grundprincip: punkter far bara tas bort nar de representerar tusental, aldrig om de
  ar decimalpunkt i t.ex. "12.5" eller "12.50".
- Rekommenderad strategi:
  1. Rensa whitespace: `s = s.replace(" ", "")`
  2. Ta bort tusentals-punkt med regex som krav pa tre siffror efter:
     - Regex: `r"\.(?=\d{3}(\D|$))"`
     - Forklaring: matchar punkt endast om den foljs av exakt tre siffror och sedan
       slut eller icke-siffra. Detta bevarar "12.5" och "12.50".
  3. Byt `,` -> `.` och parsea `Decimal`.
- Alternativt: validera formatet fore normalisering med hel regex:
  - `r"^[+-]?\d{1,3}([ .]\d{3})*(,\d+)?$|^[+-]?\d+(,\d+)?$"`
  - Anvand for att snabbt avvisa fel som "12.34.567" eller "1,23,45".

## Forslag: delad utility och call sites
- Ny gemensam funktion i `src/utils/number_normalizer.py` eller
  `src/analysis/number_normalizer.py` (om utils saknas i projektet).
- Exponera som `normalize_swedish_decimal(text: str) -> Decimal`.
- Troliga call sites (inventera vid implementation):
  - `src/pipeline/invoice_line_parser.py` (radbelopp, moms%, antal, pris)
  - `src/pipeline/validation.py` (summeringar och validering)
  - `src/pipeline/header_extractor.py` (totalsummor/att betala)
  - `src/export/` (om export parsar om siffror)
  - `src/analysis/` (analys scripts som tolkar tal)
- Sikta pa centralisering: all valutaparssning ska ga via funktionen (NUM-01).

## Risker
- Felaktig borttagning av decimalpunkt vid engelskt format ("12.50") om regex ar for bred.
- OCR-brus kan ge blandade separatorer ("1.234,5" vs "1,234.5").
- Text med valutasymbol eller bokstaver runt talet ("SEK 1 234,50") kan krava trimning.
- Negativa belopp med minustecken i olika positioner ("-1 234,00", "1 234,00-").

## Testideer
- "1 234 567,89" -> Decimal("1234567.89")
- "12.345,67" -> Decimal("12345.67")
- "12.50" -> behall decimalpunkt (ej tusental)
- "12.5" -> behall decimalpunkt
- "1.234" -> tolka som tusental, blir "1234"
- "1,234" -> svensk decimal (1.234) om inget annat indikerar tusental
- "SEK 1 234,50" -> korrekt parse efter trimning
- "-1 234,00" och "1 234,00-" -> negativt belopp
