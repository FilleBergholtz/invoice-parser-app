"""Test script för att verifiera fixarna för artikelnummer, enheter, företag och datum."""
import pandas as pd
import glob
import os
from pathlib import Path

print("=" * 80)
print("TEST: Verifiering av fixar")
print("=" * 80)

# Hitta senaste Excel-fil (prioritera output_test_fixes om den finns)
output_dirs = [
    'output_test_fixes',  # Prioritera den nya batch-processningen
    'output_test_edge_cases_v2',
    'output_test_edge_cases',
    'output_verification_footer_fix',
    'output_verification'
]

excel_files = []
for output_dir in output_dirs:
    if os.path.exists(output_dir):
        files = glob.glob(f'{output_dir}/invoices_*.xlsx')
        excel_files.extend(files)

if not excel_files:
    print("\nFEL: Ingen Excel-fil hittades. Kör först batch-processning:")
    print("  python -m src.cli.main --input tests/fixtures/pdfs --output output_test")
    exit(1)

latest_file = max(excel_files, key=lambda p: os.path.getmtime(p))
print(f"\nAnalyserar: {latest_file}\n")

df = pd.read_excel(latest_file)

print("=" * 80)
print("1. TEST: Artikelnummer i antal")
print("=" * 80)

# Hitta rader där antal ser ut som artikelnummer (långa nummer)
article_number_in_quantity = []
for idx, row in df.iterrows():
    quantity = row['Antal']
    description = str(row['Beskrivning'])
    
    if pd.notna(quantity):
        try:
            qty_value = float(quantity)
            # Artikelnummer är typiskt 6+ siffror
            if qty_value >= 100000:
                # Kolla om beskrivningen börjar med samma nummer
                desc_start = description.split()[0] if description else ""
                if str(int(qty_value)) in desc_start or desc_start.replace(' ', '') == str(int(qty_value)):
                    article_number_in_quantity.append({
                        'Fakturanummer': row['Fakturanummer'],
                        'Beskrivning': description,
                        'Antal': quantity,
                        'Enhet': row['Enhet']
                    })
        except (ValueError, TypeError):
            pass

print(f"\nHittade {len(article_number_in_quantity)} rader där artikelnummer kan ha hamnat i antal:")
if len(article_number_in_quantity) > 0:
    for item in article_number_in_quantity[:10]:
        print(f"  - Antal: {item['Antal']}, Beskrivning: {item['Beskrivning'][:60]}")
    if len(article_number_in_quantity) > 10:
        print(f"  ... och {len(article_number_in_quantity) - 10} fler")
else:
    print("  OK: Inga artikelnummer i antal-kolumnen!")

print("\n" + "=" * 80)
print("2. TEST: Enheter (DAY, dagar, EA, LTR, Liter, månad, XPA)")
print("=" * 80)

# Kända enheter som ska finnas
expected_units = ['day', 'days', 'dagar', 'ea', 'ltr', 'liter', 'liters', 'månad', 'månader', 'xpa']
expected_units_upper = [u.upper() for u in expected_units]

# Hitta alla unika enheter
all_units = df['Enhet'].dropna().unique()
all_units_lower = [str(u).lower() for u in all_units if pd.notna(u)]

print(f"\nHittade {len(all_units)} unika enheter:")
for unit in sorted(all_units)[:20]:
    print(f"  - {unit}")

# Kolla om förväntade enheter finns
missing_units = []
for expected in expected_units:
    if expected not in all_units_lower:
        missing_units.append(expected)

if missing_units:
    print(f"\nVARNING: Följande enheter saknas: {', '.join(missing_units)}")
    print("  (Detta kan vara OK om de inte finns i testdata)")
else:
    print(f"\nOK: Alla förväntade enheter finns i data (eller finns inte i testdata)")

print("\n" + "=" * 80)
print("3. TEST: Företag (filtrera bort metadata)")
print("=" * 80)

# Hitta företag som ser ut som metadata
metadata_patterns = [
    r'sida\s+\d+/\d+',  # "sida 2/2"
    r'nr:\s*\d+',  # "Nr: xxxxxx"
    r'\d{2}-\d{2}-\d{2}',  # Dates like "25-03-11"
    r'\d{4}-\d{2}-\d{2}',  # Dates like "2024-08-22"
    r'\d+\s+\d+\s+\(\d+\)',  # "001002687 1(1)"
    r'\d{5}\s*[A-ZÅÄÖ]+',  # Postcodes like "11798STOCKHOLM"
    r'\d+\s+\d+[.,]\d{2}\s+sek',  # Amounts like "7 517,00 SEK"
    r'betaling', r'betalningsreferens', r'lagerplats'
]

import re
metadata_in_company = []
for idx, row in df.iterrows():
    company = str(row['Företag'])
    if company and company != 'TBD' and company != 'nan':
        company_lower = company.lower()
        # Kolla om företaget matchar metadata-mönster
        for pattern in metadata_patterns:
            if re.search(pattern, company, re.IGNORECASE):
                metadata_in_company.append({
                    'Fakturanummer': row['Fakturanummer'],
                    'Företag': company
                })
                break

print(f"\nHittade {len(metadata_in_company)} rader där företag ser ut som metadata:")
if len(metadata_in_company) > 0:
    for item in metadata_in_company[:10]:
        print(f"  - Fakturanummer: {item['Fakturanummer']}, Företag: {item['Företag']}")
    if len(metadata_in_company) > 10:
        print(f"  ... och {len(metadata_in_company) - 10} fler")
else:
    print("  OK: Inga metadata i företag-kolumnen!")

print("\n" + "=" * 80)
print("4. TEST: Datum (TBD)")
print("=" * 80)

# Hitta fakturor med TBD på datum
tbd_dates = df[df['Fakturadatum'] == 'TBD']
unique_invoices_tbd = tbd_dates['Fakturanummer'].unique()

print(f"\nHittade {len(unique_invoices_tbd)} fakturor med TBD på datum:")
if len(unique_invoices_tbd) > 0:
    for fakturanummer in unique_invoices_tbd[:10]:
        invoice_rows = df[df['Fakturanummer'] == fakturanummer]
        print(f"  - Fakturanummer: {fakturanummer} ({len(invoice_rows)} rader)")
    if len(unique_invoices_tbd) > 10:
        print(f"  ... och {len(unique_invoices_tbd) - 10} fler fakturor")
else:
    print("  OK: Inga TBD-datum!")

# Statistik
total_invoices = df['Fakturanummer'].nunique()
tbd_percentage = (len(unique_invoices_tbd) / total_invoices * 100) if total_invoices > 0 else 0
print(f"\nStatistik:")
print(f"  Total fakturor: {total_invoices}")
print(f"  Fakturor med TBD: {len(unique_invoices_tbd)} ({tbd_percentage:.1f}%)")

print("\n" + "=" * 80)
print("SAMMANFATTNING")
print("=" * 80)

print(f"\n1. Artikelnummer i antal: {len(article_number_in_quantity)} problem")
print(f"2. Enheter: {len(missing_units)} saknade (kan vara OK)")
print(f"3. Metadata i företag: {len(metadata_in_company)} problem")
print(f"4. TBD på datum: {len(unique_invoices_tbd)} fakturor ({tbd_percentage:.1f}%)")

if len(article_number_in_quantity) == 0 and len(metadata_in_company) == 0:
    print("\nOK: Alla fixar verifierade - inga problem hittade!")
elif len(article_number_in_quantity) == 0 and len(metadata_in_company) < 10:
    print("\nOK: Några mindre problem kvar, men fixarna fungerar i stort")
else:
    print("\nVARNING: Vissa problem kvar - fixarna behover forbattras")

print("\n" + "=" * 80)
