"""Analysera problem med EA, LTR, månad, DAY, XPA enheter."""
import pandas as pd
import re

df = pd.read_excel('output_test_fixes/invoices_2026-01-17_21-42-15.xlsx')

print("=" * 80)
print("ANALYS: Problem med EA, LTR, månad, DAY, XPA enheter")
print("=" * 80)

# Hitta alla rader med dessa enheter
problem_units = ['ea', 'ltr', 'månad', 'day', 'xpa']
problem_rows = df[df['Enhet'].str.lower().isin(problem_units) if 'Enhet' in df.columns else pd.Series([False] * len(df))]

print(f"\nHittade {len(problem_rows)} rader med EA, LTR, månad, DAY eller XPA enheter\n")

# Analysera problem
correct_rows = []
problem_rows_list = []

for idx, row in problem_rows.iterrows():
    unit = str(row['Enhet']).lower() if pd.notna(row['Enhet']) else ""
    quantity = row['Antal']
    unit_price = row['Á-pris']
    description = str(row['Beskrivning'])
    total_amount = row['Summa']
    
    # Kolla om quantity ser ut som artikelnummer (6+ siffror)
    has_article_number_in_qty = False
    if pd.notna(quantity):
        try:
            qty_value = float(quantity)
            if qty_value >= 100000 or len(str(int(qty_value))) >= 6:
                # Kolla om beskrivningen börjar med samma nummer
                desc_start = description.split()[0] if description else ""
                if str(int(qty_value)) in desc_start or desc_start.replace(' ', '') == str(int(qty_value)):
                    has_article_number_in_qty = True
        except:
            pass
    
    # Kolla om unit_price är rimligt (inte för stort, inte för litet)
    unit_price_ok = True
    if pd.notna(unit_price) and pd.notna(total_amount) and pd.notna(quantity):
        try:
            up = float(unit_price)
            ta = float(total_amount)
            qty = float(quantity)
            if qty > 0:
                calculated_price = ta / qty
                # Unit price ska vara ungefär total_amount / quantity
                if abs(up - calculated_price) > 0.01:
                    unit_price_ok = False
        except:
            pass
    
    # Kolla om quantity är rimligt (inte för stort)
    quantity_ok = True
    if pd.notna(quantity):
        try:
            qty_value = float(quantity)
            if qty_value >= 1000:  # Mycket stort antal är misstänkt
                quantity_ok = False
        except:
            pass
    
    if has_article_number_in_qty or not unit_price_ok or not quantity_ok:
        problem_rows_list.append({
            'Fakturanummer': row['Fakturanummer'],
            'Beskrivning': description[:60],
            'Enhet': unit,
            'Antal': quantity,
            'Á-pris': unit_price,
            'Summa': total_amount,
            'Problem': []
        })
        if has_article_number_in_qty:
            problem_rows_list[-1]['Problem'].append('Artikelnummer i antal')
        if not unit_price_ok:
            problem_rows_list[-1]['Problem'].append('Á-pris stämmer inte')
        if not quantity_ok:
            problem_rows_list[-1]['Problem'].append('Antal för stort')
    else:
        correct_rows.append({
            'Fakturanummer': row['Fakturanummer'],
            'Beskrivning': description[:60],
            'Enhet': unit,
            'Antal': quantity,
            'Á-pris': unit_price,
            'Summa': total_amount
        })

print(f"Problem-rader: {len(problem_rows_list)}")
print(f"Korrekt-rader: {len(correct_rows)}\n")

if problem_rows_list:
    print("=" * 80)
    print("PROBLEM-RADER:")
    print("=" * 80)
    for item in problem_rows_list[:20]:
        print(f"\nFakturanummer: {item['Fakturanummer']}")
        print(f"Beskrivning: {item['Beskrivning']}")
        print(f"Enhet: {item['Enhet']}")
        print(f"Antal: {item['Antal']}")
        print(f"Á-pris: {item['Á-pris']}")
        print(f"Summa: {item['Summa']}")
        print(f"Problem: {', '.join(item['Problem'])}")
    
    if len(problem_rows_list) > 20:
        print(f"\n... och {len(problem_rows_list) - 20} fler problem-rader")

if correct_rows:
    print("\n" + "=" * 80)
    print("KORREKT-RADER (för jämförelse):")
    print("=" * 80)
    for item in correct_rows[:5]:
        print(f"\nFakturanummer: {item['Fakturanummer']}")
        print(f"Beskrivning: {item['Beskrivning']}")
        print(f"Enhet: {item['Enhet']}")
        print(f"Antal: {item['Antal']}")
        print(f"Á-pris: {item['Á-pris']}")
        print(f"Summa: {item['Summa']}")

print("\n" + "=" * 80)
print("SAMMANFATTNING")
print("=" * 80)
print(f"\nTotal rader med EA/LTR/månad/DAY/XPA: {len(problem_rows)}")
print(f"Problem-rader: {len(problem_rows_list)} ({len(problem_rows_list)/len(problem_rows)*100:.1f}%)")
print(f"Korrekt-rader: {len(correct_rows)} ({len(correct_rows)/len(problem_rows)*100:.1f}%)")

print("\n" + "=" * 80)
