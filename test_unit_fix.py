"""Test script för att verifiera fixen för EA, LTR, månad, DAY, XPA enheter."""
import pandas as pd
import glob
import os
import re

print("=" * 80)
print("TEST: Verifiering av unit-fix (EA, LTR, månad, DAY, XPA)")
print("=" * 80)

# Hitta senaste Excel-fil
output_dirs = [
    'output_test_quantity_fix_v2',
    'output_test_quantity_fix',
    'output_test_unit_fix_v3',
    'output_test_unit_fix_v2',
    'output_test_unit_fix',
    'output_test_fixes',
    'output_test_edge_cases_v2'
]

excel_files = []
for output_dir in output_dirs:
    if os.path.exists(output_dir):
        files = glob.glob(f'{output_dir}/invoices_*.xlsx')
        excel_files.extend(files)

if not excel_files:
    print("\nVANTAR: Batch-processning pågår fortfarande...")
    print("Kör detta script igen när processningen är klar.")
    exit(0)

latest_file = max(excel_files, key=lambda p: os.path.getmtime(p))
print(f"\nAnalyserar: {latest_file}\n")

df = pd.read_excel(latest_file)

# Hitta alla rader med problem-enheter
problem_units = ['ea', 'ltr', 'månad', 'day', 'xpa']
problem_rows = df[df['Enhet'].str.lower().isin(problem_units) if 'Enhet' in df.columns else pd.Series([False] * len(df))]

print(f"Hittade {len(problem_rows)} rader med EA, LTR, månad, DAY eller XPA enheter\n")

# Analysera problem
correct_count = 0
problem_count = 0
problems = []

for idx, row in problem_rows.iterrows():
    unit = str(row['Enhet']).lower() if pd.notna(row['Enhet']) else ""
    quantity = row['Antal']
    unit_price = row['Á-pris']
    description = str(row['Beskrivning'])
    total_amount = row['Summa']
    
    has_problem = False
    problem_reasons = []
    
    # Kolla om quantity ser ut som artikelnummer (6+ siffror)
    if pd.notna(quantity):
        try:
            qty_value = float(quantity)
            if qty_value >= 1000:  # Mycket stort antal är misstänkt
                # Kolla om beskrivningen innehåller samma nummer (artikelnummer)
                desc_start = description.split()[0] if description else ""
                if str(int(qty_value)) in desc_start or desc_start.replace(' ', '') == str(int(qty_value)):
                    has_problem = True
                    problem_reasons.append(f"Artikelnummer i antal ({quantity})")
        except:
            pass
    
    # Kolla om unit_price stämmer med quantity * unit_price ≈ total_amount
    if pd.notna(unit_price) and pd.notna(total_amount) and pd.notna(quantity):
        try:
            up = float(unit_price)
            ta = float(total_amount)
            qty = float(quantity)
            if qty > 0:
                # Beräkna förväntat total från unit_price
                expected_total = up * qty
                
                # Unit price är korrekt om:
                # 1. expected_total >= total_amount (eftersom total_amount kan vara efter rabatt)
                # 2. Om expected_total är mycket mindre än total_amount, är något fel
                if expected_total < ta * 0.5:  # Om expected_total är mindre än hälften, är något fel
                    has_problem = True
                    problem_reasons.append(f"Á-pris stämmer inte (förväntat total: {expected_total:.2f}, faktiskt: {ta:.2f})")
                elif abs(up - (ta / qty)) > 1.0 and expected_total < ta * 0.9:
                    # Om unit_price inte stämmer OCH det inte verkar vara en rabatt, flagga problem
                    calculated_price = ta / qty
                    has_problem = True
                    problem_reasons.append(f"Á-pris stämmer inte (beräknat: {calculated_price:.2f}, faktiskt: {up:.2f})")
        except:
            pass
    
    if has_problem:
        problem_count += 1
        problems.append({
            'Fakturanummer': row['Fakturanummer'],
            'Beskrivning': description[:70],
            'Enhet': unit,
            'Antal': quantity,
            'Á-pris': unit_price,
            'Summa': total_amount,
            'Problem': problem_reasons
        })
    else:
        correct_count += 1

print("=" * 80)
print("RESULTAT")
print("=" * 80)

print(f"\nTotal rader med EA/LTR/månad/DAY/XPA: {len(problem_rows)}")
print(f"Korrekt-rader: {correct_count} ({correct_count/len(problem_rows)*100:.1f}%)")
print(f"Problem-rader: {problem_count} ({problem_count/len(problem_rows)*100:.1f}%)")

if problems:
    print(f"\nExempel på problem-rader (första 10):")
    for item in problems[:10]:
        print(f"\nFakturanummer: {item['Fakturanummer']}")
        print(f"Beskrivning: {item['Beskrivning']}")
        print(f"Enhet: {item['Enhet']}, Antal: {item['Antal']}, Á-pris: {item['Á-pris']}, Summa: {item['Summa']}")
        print(f"Problem: {', '.join(item['Problem'])}")
    
    if len(problems) > 10:
        print(f"\n... och {len(problems) - 10} fler problem-rader")
else:
    print("\nOK: Inga problem hittade!")

print("\n" + "=" * 80)

# Jämför med gamla resultatet
if 'output_test_fixes' in latest_file:
    print("\nJämförelse med tidigare:")
    print("  Före fix: 1805 problem-rader (89.1%)")
    print(f"  Efter fix: {problem_count} problem-rader ({problem_count/len(problem_rows)*100:.1f}%)")
    improvement = 1805 - problem_count
    if improvement > 0:
        print(f"  Förbättring: {improvement} problem fixade ({improvement/1805*100:.1f}%)")

print("\n" + "=" * 80)
