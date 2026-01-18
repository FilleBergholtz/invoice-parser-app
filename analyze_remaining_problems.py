"""Analysera de återstående problem-raderna för EA, LTR, månad, DAY, XPA enheter."""
import pandas as pd
import re
import glob
import os

print("=" * 80)
print("ANALYS: Återstående problem-rader (edge cases)")
print("=" * 80)

# Hitta senaste Excel-fil
output_dirs = [
    'tests/output_test_unit_fix_v3',
    'tests/output_test_unit_fix_v2',
    'tests/output_test_unit_fix',
]

excel_files = []
for output_dir in output_dirs:
    if os.path.exists(output_dir):
        files = glob.glob(f'{output_dir}/invoices_*.xlsx')
        excel_files.extend(files)

if not excel_files:
    print("\nFEL: Ingen Excel-fil hittades")
    exit(1)

latest_file = max(excel_files, key=lambda p: os.path.getmtime(p))
print(f"\nAnalyserar: {latest_file}\n")

df = pd.read_excel(latest_file)

# Hitta alla rader med problem-enheter
problem_units = ['ea', 'ltr', 'månad', 'day', 'xpa']
problem_rows = df[df['Enhet'].str.lower().isin(problem_units) if 'Enhet' in df.columns else pd.Series([False] * len(df))]

print(f"Hittade {len(problem_rows)} rader med EA, LTR, månad, DAY eller XPA enheter\n")

# Analysera problem
problems = []

for idx, row in problem_rows.iterrows():
    unit = str(row['Enhet']).lower() if pd.notna(row['Enhet']) else ""
    quantity = row['Antal']
    unit_price = row['Á-pris']
    description = str(row['Beskrivning'])
    total_amount = row['Summa']
    discount = row.get('Rabatt', None)
    
    has_problem = False
    problem_reasons = []
    
    # Kolla om quantity ser ut som artikelnummer (6+ siffror)
    if pd.notna(quantity):
        try:
            qty_value = float(quantity)
            if qty_value >= 1000:  # Mycket stort antal är misstänkt
                desc_start = description.split()[0] if description else ""
                if str(int(qty_value)) in desc_start or desc_start.replace(' ', '') == str(int(qty_value)):
                    has_problem = True
                    problem_reasons.append(f"Artikelnummer i antal ({quantity})")
        except:
            pass
    
    # Kolla om unit_price stämmer
    if pd.notna(unit_price) and pd.notna(total_amount) and pd.notna(quantity):
        try:
            up = float(unit_price)
            ta = float(total_amount)
            qty = float(quantity)
            if qty > 0:
                expected_total = up * qty
                
                # Om expected_total är mycket mindre än total_amount, är något fel
                if expected_total < ta * 0.5:
                    has_problem = True
                    problem_reasons.append(f"Á-pris stämmer inte (förväntat total: {expected_total:.2f}, faktiskt: {ta:.2f})")
                elif abs(up - (ta / qty)) > 1.0 and expected_total < ta * 0.9:
                    calculated_price = ta / qty
                    has_problem = True
                    problem_reasons.append(f"Á-pris stämmer inte (beräknat: {calculated_price:.2f}, faktiskt: {up:.2f})")
        except:
            pass
    
    if has_problem:
        problems.append({
            'Fakturanummer': row['Fakturanummer'],
            'Beskrivning': description,
            'Enhet': unit,
            'Antal': quantity,
            'Á-pris': unit_price,
            'Summa': total_amount,
            'Rabatt': discount if pd.notna(discount) else None,
            'Problem': problem_reasons
        })

print(f"Total problem-rader: {len(problems)}\n")

# Kategorisera problem
categories = {
    'artikelnummer_i_antal': [],
    'unit_price_for_liten': [],
    'unit_price_stämmer_inte': [],
    'komplexa_rabatter': [],
    'tusen_separator_problem': []
}

for item in problems:
    desc = item['Beskrivning']
    qty = item['Antal']
    up = item['Á-pris']
    ta = item['Summa']
    
    # Kategorisera
    if 'Artikelnummer i antal' in ' '.join(item['Problem']):
        categories['artikelnummer_i_antal'].append(item)
    elif pd.notna(up) and float(up) < 10 and ta > 1000:
        # Unit price är för liten jämfört med total
        categories['unit_price_for_liten'].append(item)
    elif 'Á-pris stämmer inte' in ' '.join(item['Problem']):
        if pd.notna(item['Rabatt']):
            categories['komplexa_rabatter'].append(item)
        else:
            categories['unit_price_stämmer_inte'].append(item)
    
    # Kolla om det kan vara tusen-separator problem
    if pd.notna(up) and float(up) < 100 and ta > 1000:
        # Kolla om beskrivningen innehåller stora nummer
        large_numbers = re.findall(r'\d{1,3}(?:\s+\d{3})+(?:[.,]\d{2})?', desc)
        if large_numbers:
            categories['tusen_separator_problem'].append(item)

print("=" * 80)
print("KATEGORISERING AV PROBLEM")
print("=" * 80)

for category, items in categories.items():
    if items:
        print(f"\n{category}: {len(items)} rader")
        print("-" * 80)
        for item in items[:3]:  # Visa första 3
            print(f"\nFakturanummer: {item['Fakturanummer']}")
            print(f"Beskrivning: {item['Beskrivning'][:80]}")
            print(f"Enhet: {item['Enhet']}, Antal: {item['Antal']}, Á-pris: {item['Á-pris']}, Summa: {item['Summa']}")
            if item['Rabatt']:
                print(f"Rabatt: {item['Rabatt']}")
            print(f"Problem: {', '.join(item['Problem'])}")
        if len(items) > 3:
            print(f"\n... och {len(items) - 3} fler")

# Detaljerad analys av specifika problem
print("\n" + "=" * 80)
print("DETALJERAD ANALYS")
print("=" * 80)

# Analysera beskrivningar för att hitta mönster
print("\n1. Analys av beskrivningar med problem:")
print("-" * 80)
for item in problems[:10]:
    desc = item['Beskrivning']
    # Hitta alla nummer i beskrivningen
    numbers = re.findall(r'\d+', desc)
    print(f"\nFakturanummer: {item['Fakturanummer']}")
    print(f"Beskrivning: {desc}")
    print(f"Nummer i beskrivning: {numbers}")
    print(f"Antal: {item['Antal']}, Á-pris: {item['Á-pris']}, Summa: {item['Summa']}")
    
    # Försök identifiera vad som kan vara quantity, unit_price
    # Titta efter mönster: ... quantity unit unit_price ...
    unit_pos = None
    if item['Enhet']:
        unit_lower = item['Enhet'].lower()
        desc_lower = desc.lower()
        if unit_lower in desc_lower:
            unit_pos = desc_lower.find(unit_lower)
            print(f"  Enhet '{unit_lower}' hittades på position {unit_pos}")
            
            # Hitta nummer före och efter enheten
            before_unit = desc[:unit_pos]
            after_unit = desc[unit_pos + len(unit_lower):]
            
            numbers_before = re.findall(r'\d+(?:[.,]\d+)?', before_unit)
            numbers_after = re.findall(r'\d+(?:[.,]\d+)?', after_unit)
            
            print(f"  Nummer före enhet: {numbers_before[-3:] if numbers_before else []}")  # Sista 3
            print(f"  Nummer efter enhet: {numbers_after[:3] if numbers_after else []}")  # Första 3

print("\n" + "=" * 80)
print("SAMMANFATTNING")
print("=" * 80)
print(f"\nTotal problem-rader: {len(problems)}")
print(f"\nKategorier:")
for category, items in categories.items():
    if items:
        print(f"  - {category}: {len(items)} rader ({len(items)/len(problems)*100:.1f}%)")

print("\n" + "=" * 80)
