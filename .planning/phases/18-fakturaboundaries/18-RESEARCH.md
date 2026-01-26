# Fas 18: Fakturaboundaries for multi-page PDFs

## Mal och krav
- Roadmap: Sidor grupperas korrekt per faktura utan att bero pa totalsumma.
- Krav: BOUND-01, BOUND-02, BOUND-03.
- Fokus: Ny logik i `invoice_boundary_detection.py` samt CLI compare-path.

## Heuristik: gruppering med fakturanummer per sida
1. Extrahera kandidatlista per sida:
   - Fakturanummer-etiketter: "Fakturanr", "Faktura nr", "Invoice No", "Invoice Number".
   - Varden: alfanumeriska sekvenser, 4-20 tecken, tillat bindestreck/slug.
   - Placering: Ovre halvan eller header-zon prioriteras.
2. Matcha sida till aktiv faktura:
   - Om sidan har exakt ett starkt fakturanummer -> ny grupp om det skiljer sig fran aktivt.
   - Om fakturanummer matchar aktivt -> tillhor samma faktura.
   - Om flera kandidater -> valj hogst konfidens (etikett + narhet + position).
3. Stabilisering over flera sidor:
   - Krav pa minst 2 sidor med samma fakturanummer innan grupp delas vid konflikt.
   - Soft-break: Om sidan saknar fakturanummer men matchar header-sjalvklart (leverantor + datum) -> behall aktiv grupp.

## Sida X/Y och sidnumrering
1. Identifiera format:
   - "Sida 1/2", "Sida 2 av 3", "Page 1/2", "1/2".
2. Anvandning:
   - Om "Sida 1/2" hittas -> starta ny grupp om ingen aktiv eller om aktiv faktura har slutats.
   - Om "Sida 2/2" utan fakturanummer -> tillhor samma faktura som foregaende sida.
   - Konsekvenskontroll: Om sidnummer okar sekventiellt utan hopp, bevara grupp.
3. Konfliktlosning:
   - Om sidnummer indikerar ny faktura men fakturanummer matchar aktiv -> fakturanummer vinner.
   - Om sidnummer indikerar fortsättning men nytt fakturanummer hittas -> starta ny grupp och markera risk.

## Risker och fallback
- Saknat fakturanummer:
  - Fallback: gruppera med header-fingerprint (leverantor + datum + valuta).
  - Fallback: anvand sidnumrering och kontinuitet i layout.
- Falska fakturanummer (kundnummer, ordernr):
  - Fallback: prioritering av etikett/position och blacklist av nyckelord.
- OCR-brus:
  - Fallback: normalisera tecken (O/0, I/1) och tolerera 1-2 edit distance.
- Blandade fakturor i samma PDF:
  - Fallback: om fakturanummer skiftar ofta, aktivera "split aggressivt" med kort buffer.

## Testideer
- PDF med 2 fakturor, 2 sidor vardera, tydligt fakturanummer.
- PDF utan fakturanummer men med "Sida 1/2, 2/2" -> korrekt grupp.
- PDF med fakturanummer pa sida 1 men inte pa sida 2 -> fortsatt grupp.
- PDF dar "Sida 1/2" kolliderar med nytt fakturanummer pa sida 2.
- OCR-variation: "Faktura nr: O123" vs "0123" -> samma grupp.
- Falsk kandidat: "Ordernr 12345" och "Fakturanr 6789" -> valj fakturanr.

## Implementationsnoteringar
- Utoka `invoice_boundary_detection.py` med:
  - kandidat-extraktor per sida
  - sidnumrering-parser
  - beslutstrad for gruppgrans
- CLI compare-path:
  - logga boundary-beslut och indikatorer (fakturanr, sida x/y, fallback).
