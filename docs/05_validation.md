# Valideringsregler

## Översikt

Detta dokument definierar valideringsregler för kvalitetskontroll i invoice-parser pipeline. Validering sker i steg 11 (Reconciliation → Validation) och bestämmer status (OK/Warning/Review).

## Status-värden

### OK
**Definition**: Alla summor stämmer, alla obligatoriska fält extraherade korrekt.

**Kriterier**:
- Subtotal-avvikelse: ≤ 0.01 (tolerans för avrundning)
- Total-avvikelse: ≤ 0.01
- Fakturanummer: extraherat
- Fakturadatum: extraherat
- Minst en produktrad: extraherad
- Alla produktrader har total_amount

**Meddelanden**: Inga meddelanden eller endast info-meddelanden.

---

### Warning
**Definition**: Små avvikelser eller vissa fält saknas, men data är användbar.

**Kriterier**:
- Subtotal-avvikelse: 0.01 < avvikelse ≤ 1.00 SEK
- Total-avvikelse: 0.01 < avvikelse ≤ 1.00 SEK
- Vissa valfria fält saknas (t.ex. leverantörsadress, kundnamn)
- Enstaka produktrader saknar kvantitet eller enhetspris (men har total_amount)
- Moms-sats saknas men kan beräknas

**Meddelanden**: Varningar listas i `warnings`.

---

### Review
**Definition**: Större avvikelser eller kritiska fält saknas, data kräver manuell granskning.

**Kriterier**:
- Subtotal-avvikelse: > 1.00 SEK
- Total-avvikelse: > 1.00 SEK
- Fakturanummer: saknas
- Fakturadatum: saknas
- Inga produktrader extraherade
- Produktrader saknar total_amount
- Stora avvikelser i summor (> 10% av total)

**Meddelanden**: Fel listas i `errors`, kritiska fel flaggas.

---

## Valideringsregler

### Regel 1: Summa-validering

**Beskrivning**: Jämför beräknade summor med extraherade summor från footer.

**Regler**:
- Beräkna subtotal: `sum(invoice_line.total_amount for invoice_line in invoice_lines)`
- Beräkna total: `subtotal + tax` (om tax finns) eller `subtotal` (om ingen tax)
- Jämför med extraherad subtotal/total från footer
- Avvikelse: `|calculated - extracted|`

**Status-bestämning**:
- Avvikelse ≤ 0.01 → OK (avrundningsfel)
- 0.01 < avvikelse ≤ 1.00 → Warning
- Avvikelse > 1.00 → Review

**Implementation**:
```python
def validate_sums(reconciliation: Reconciliation) -> List[str]:
    errors = []
    warnings = []
    
    if reconciliation.subtotal_difference > 1.00:
        errors.append(f"Stor subtotal-avvikelse: {reconciliation.subtotal_difference:.2f} SEK")
    elif reconciliation.subtotal_difference > 0.01:
        warnings.append(f"Liten subtotal-avvikelse: {reconciliation.subtotal_difference:.2f} SEK")
    
    # Similar for total_difference
    return errors, warnings
```

---

### Regel 2: Obligatoriska fält

**Beskrivning**: Validera att obligatoriska fält är extraherade.

**Obligatoriska fält**:
- `invoice_number`: Fakturanummer (kritiskt)
- `invoice_date`: Fakturadatum (kritiskt)
- Minst en `InvoiceLine` med `total_amount` (kritiskt)

**Status-bestämning**:
- Alla obligatoriska fält finns → OK (om summor också stämmer)
- Fakturanummer eller datum saknas → Review
- Inga produktrader → Review

**Implementation**:
```python
def validate_required_fields(specification: InvoiceSpecification, 
                              invoice_lines: List[InvoiceLine]) -> List[str]:
    errors = []
    
    if not specification.invoice_number:
        errors.append("Fakturanummer saknas (obligatoriskt)")
    
    if not specification.invoice_date:
        errors.append("Fakturadatum saknas (obligatoriskt)")
    
    if not invoice_lines:
        errors.append("Inga produktrader extraherade (kritiskt)")
    
    return errors
```

---

### Regel 3: Produktrad-validering

**Beskrivning**: Validera att produktrader är kompletta.

**Regler**:
- Varje `InvoiceLine` måste ha `total_amount`
- `description` bör finnas (men kan vara tom om wrapped text inte kopplades)
- `quantity` och `unit_price` är valfria men bör finnas

**Status-bestämning**:
- Alla rader har total_amount och description → OK (om summor stämmer)
- Några rader saknar total_amount → Review
- Några rader saknar quantity/unit_price → Warning (men OK om total_amount finns)

**Implementation**:
```python
def validate_invoice_lines(invoice_lines: List[InvoiceLine]) -> List[str]:
    errors = []
    warnings = []
    
    for line in invoice_lines:
        if not line.total_amount:
            errors.append(f"Produktrad {line.line_number} saknar total_amount")
        
        if not line.description or line.description.strip() == "":
            warnings.append(f"Produktrad {line.line_number} saknar beskrivning")
        
        if not line.quantity and not line.unit_price:
            # OK om total_amount finns
            pass
        elif line.quantity and line.unit_price:
            # Validera att quantity * unit_price ≈ total_amount
            expected = line.quantity * line.unit_price
            if abs(expected - line.total_amount) > 0.01:
                warnings.append(
                    f"Produktrad {line.line_number}: "
                    f"quantity * unit_price ({expected:.2f}) ≠ total_amount ({line.total_amount:.2f})"
                )
    
    return errors, warnings
```

---

### Regel 4: Aritmetisk validering

**Beskrivning**: Validera att aritmetik stämmer (kvantitet × enhetspris = total).

**Regler**:
- Om både `quantity` och `unit_price` finns: `quantity * unit_price` ≈ `total_amount`
- Tolerans: 0.01 SEK (för avrundning)

**Status-bestämning**:
- Aritmetik stämmer för alla rader → OK (om summor också stämmer)
- Några rader har aritmetiska fel → Warning (om avvikelsen är liten)
- Många rader har aritmetiska fel → Review

---

### Regel 5: Datum-validering

**Beskrivning**: Validera att datum är giltigt och rimligt.

**Regler**:
- Datum måste vara i format som kan parsas (YYYY-MM-DD, DD/MM/YYYY, etc.)
- Datum bör inte vara i framtiden
- Datum bör inte vara mer än 10 år tillbaka (configurable)

**Status-bestämning**:
- Giltigt datum → OK
- Ogiltigt datum-format → Review
- Datum i framtiden eller för gammalt → Warning (men tillåt)

**Implementation**:
```python
def validate_date(invoice_date: datetime.date) -> List[str]:
    warnings = []
    
    today = datetime.date.today()
    
    if invoice_date > today:
        warnings.append(f"Fakturadatum är i framtiden: {invoice_date}")
    
    if invoice_date < today - datetime.timedelta(days=3650):  # 10 år
        warnings.append(f"Fakturadatum är mycket gammalt: {invoice_date}")
    
    return warnings
```

---

### Regel 6: Belopp-validering

**Beskrivning**: Validera att belopp är rimliga (positiva, inte för stora).

**Regler**:
- `total_amount` måste vara positivt (> 0)
- `total_amount` bör vara rimligt (t.ex. < 1 000 000 SEK, configurable)
- Subtotal och total bör vara positiva

**Status-bestämning**:
- Alla belopp är rimliga → OK
- Negativa belopp → Review
- Mycket stora belopp → Warning (men tillåt)

---

### Regel 7: Moms-validering

**Beskrivning**: Validera att moms-stats är korrekt (om moms finns).

**Regler**:
- Om moms extraheras: `tax / subtotal` = moms-sats (t.ex. 0.25 för 25%)
- Vanliga moms-satser: 0% (noll), 0.06 (6%), 0.12 (12%), 0.25 (25%)
- Om moms beräknas men inte matchar standard-sats → Warning

**Status-bestämning**:
- Moms-sats matchar standard → OK
- Moms-sats är icke-standard → Warning
- Stora avvikelser i moms-beräkning → Review

---

## Validation-objekt

### Status-bestämning (prioriterad ordning)

1. **Review**: Om något kritisk fel finns (saknade obligatoriska fält, stora avvikelser)
2. **Warning**: Om varningar finns men inga kritiska fel
3. **OK**: Om inga fel eller varningar finns

### Meddelanden

**Structure**:
```python
Validation:
    - status: str  # "OK", "Warning", eller "Review"
    - messages: List[str]  # Alla meddelanden (fel, varningar, info)
    - errors: List[str]  # Endast fel (kritiska)
    - warnings: List[str]  # Endast varningar
    - missing_fields: List[str]  # Saknade fält
```

**Meddelande-format**:
- Fel: `"Kritisk: [beskrivning]"`
- Varningar: `"Varning: [beskrivning]"`
- Info: `"Info: [beskrivning]"`

---

## Implementation-anvisningar

1. **Prioritering**: Kontrollera kritiska fel först (obligatoriska fält)
2. **Summa-validering**: Kör alltid summa-validering för att identifiera avvikelser
3. **Meddelanden**: Generera tydliga meddelanden som förklarar problemet
4. **Status**: Sätt status baserat på allvarligaste problemet (Review > Warning > OK)

## Exempel

### Exempel 1: OK-validering

```
Input:
  - invoice_number: "INV-2024-001"
  - invoice_date: 2024-01-15
  - invoice_lines: [3 rader med total_amount]
  - reconciliation: subtotal_difference = 0.005 SEK

Validering:
  - Obligatoriska fält: ✓
  - Summa-avvikelse: ≤ 0.01 → OK
  - Produktrader: alla har total_amount → OK

Status: OK
```

### Exempel 2: Warning-validering

```
Input:
  - invoice_number: "INV-2024-001"
  - invoice_date: 2024-01-15
  - invoice_lines: [3 rader, en saknar quantity]
  - reconciliation: subtotal_difference = 0.50 SEK

Validering:
  - Obligatoriska fält: ✓
  - Summa-avvikelse: 0.50 SEK → Warning
  - Produktrader: en saknar quantity → Warning

Status: Warning
Messages: [
  "Varning: Liten subtotal-avvikelse: 0.50 SEK",
  "Varning: Produktrad 2 saknar kvantitet"
]
```

### Exempel 3: Review-validering

```
Input:
  - invoice_number: None (saknas)
  - invoice_date: 2024-01-15
  - invoice_lines: [3 rader]
  - reconciliation: subtotal_difference = 50.00 SEK

Validering:
  - Obligatoriska fält: ✗ (invoice_number saknas)
  - Summa-avvikelse: 50.00 SEK → Review

Status: Review
Errors: [
  "Kritisk: Fakturanummer saknas (obligatoriskt)",
  "Kritisk: Stor subtotal-avvikelse: 50.00 SEK"
]
```
