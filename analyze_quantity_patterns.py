"""Analysera quantity-mönster för att identifiera tusen-separator problem."""
import pandas as pd
import re
import glob
import os

print("=" * 80)
print("ANALYS: Quantity-mönster med tusen-separatorer")
print("=" * 80)

# Hitta senaste Excel-fil
output_dirs = ['output_test_unit_fix_v3']
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

# Hitta problem-rader
problem_units = ['ea', 'ltr', 'månad', 'day', 'xpa']
problem_rows = df[df['Enhet'].str.lower().isin(problem_units) if 'Enhet' in df.columns else pd.Series([False] * len(df))]

problems = []
for idx, row in problem_rows.iterrows():
    unit = str(row['Enhet']).lower() if pd.notna(row['Enhet']) else ""
    quantity = row['Antal']
    unit_price = row['Á-pris']
    description = str(row['Beskrivning'])
    total_amount = row['Summa']
    
    if pd.notna(unit_price) and pd.notna(total_amount) and pd.notna(quantity):
        try:
            up = float(unit_price)
            ta = float(total_amount)
            qty = float(quantity)
            if qty > 0:
                expected_total = up * qty
                if expected_total < ta * 0.5:  # Stort problem
                    problems.append({
                        'Fakturanummer': row['Fakturanummer'],
                        'Beskrivning': description,
                        'Enhet': unit,
                        'Antal': quantity,
                        'Á-pris': unit_price,
                        'Summa': total_amount,
                        'Expected': expected_total,
                        'Ratio': ta / expected_total if expected_total > 0 else 0
                    })
        except:
            pass

print(f"Hittade {len(problems)} problem-rader där expected_total < total_amount * 0.5\n")

# Analysera beskrivningar för att hitta quantity-mönster
print("=" * 80)
print("ANALYS: Quantity med tusen-separatorer")
print("=" * 80)

for item in problems[:15]:
    desc = item['Beskrivning']
    unit = item['Enhet']
    qty = item['Antal']
    up = item['Á-pris']
    ta = item['Summa']
    expected = item['Expected']
    ratio = item['Ratio']
    
    print(f"\nFakturanummer: {item['Fakturanummer']}")
    print(f"Beskrivning: {desc}")
    print(f"Enhet: {unit}, Antal: {qty}, Á-pris: {up}, Summa: {ta}")
    print(f"Expected: {expected:.2f}, Ratio: {ratio:.2f}x")
    
    # Hitta enhetens position
    unit_pos = desc.lower().find(unit)
    if unit_pos > 0:
        before_unit = desc[:unit_pos].strip()
        after_unit = desc[unit_pos + len(unit):].strip()
        
        # Hitta nummer före enheten (kan vara quantity med tusen-separator)
        # Pattern för tusen-separator: "2 108", "1 260", "4 708"
        thousand_sep_pattern = r'\d{1,3}(?:\s+\d{3})+'
        matches = re.findall(thousand_sep_pattern, before_unit)
        
        if matches:
            print(f"  TUSEN-SEPARATOR HITTAD före enhet: {matches}")
            for match in matches:
                cleaned = match.replace(' ', '')
                try:
                    value = int(cleaned)
                    # Kolla om detta skulle ge rätt total
                    if abs(value * float(up) - ta) < 10:  # Tolerans 10 SEK
                        print(f"  ✓ KORREKT QUANTITY: {value} (istället för {qty})")
                        print(f"    Beräknat total: {value * float(up):.2f} (faktiskt: {ta:.2f})")
                except:
                    pass
        
        # Hitta alla nummer före enheten
        all_numbers_before = re.findall(r'\d+(?:\s+\d+)*', before_unit)
        print(f"  Alla nummer före enhet: {all_numbers_before[-5:]}")  # Sista 5
        
        # Hitta nummer efter enheten (unit_price)
        all_numbers_after = re.findall(r'\d+(?:[.,]\d+)?', after_unit)
        print(f"  Alla nummer efter enhet: {all_numbers_after[:3]}")  # Första 3

print("\n" + "=" * 80)
print("SAMMANFATTNING")
print("=" * 80)
print(f"\nTotal problem-rader: {len(problems)}")
print(f"\nProblemet verkar vara att quantity med tusen-separatorer (t.ex. '2 108')")
print(f"extraheras som bara sista delen ('108') istället för hela numret ('2108').")

print("\n" + "=" * 80)
