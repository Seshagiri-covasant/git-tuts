"""Check schema descriptions from logs vs Benchmarking.xlsx"""
import pandas as pd
import re

# Sample descriptions from the logs (from terminal selection)
log_descriptions = {
    'OneTimeVendorFlag': 'Indicates if the vendor is a one-time or infrequent vendor.',
    'P2PHRIN305': 'Risky Vendors - Invoice(s) from Vendor(s) from Embargoed Countries',
    'P2PHRIN302': 'Risky Vendors - Vendor name(s) matching with OFAC Sanctions List',
    'P2PHRIN303': 'Risky Vendors - Vendor name(s) matching with Panama Papers - Invoices',
    'P2PHRIN304': 'Risky Vendors - Vendor address matching with Panama Papers - Invoices',
    'P2PFMIN268': 'Document Currency different in PO and Invoice',
    'P2PFMIN271': 'Vendor(s) with only one Invoice, without OTV flag',
    'PostingDate': 'Date posted in accounting ledgers.',
    'SPT_VendorNumber': 'Unique identifier for vendor associated with the invoice.',
    'TotalInvoiceAmountRC': 'Total invoice amount in reporting currency.',
    'VendorCountry': 'Country code where the vendor is registered.',
    'VendorName': 'Name of the vendor billed in the invoice.',
}

print("="*80)
print("COMPARING LOG SCHEMA vs BENCHMARKING.xlsx")
print("="*80)

# Load Benchmarking.xlsx
excel_invoices = pd.read_excel('Benchmarking.xlsx', sheet_name='Invoices Schema')

print(f"\n✅ Loaded Benchmarking.xlsx (Invoices Schema: {len(excel_invoices)} columns)")

print("\n" + "-"*80)
print("COMPARISON RESULTS:")
print("-"*80)

matches = 0
mismatches = []

for col_name, log_desc in log_descriptions.items():
    excel_row = excel_invoices[excel_invoices['Column Name'].str.strip() == col_name]
    
    if excel_row.empty:
        print(f"⚠️  {col_name}: NOT FOUND in Excel")
        continue
    
    excel_desc = excel_row['Description'].iloc[0].strip() if pd.notna(excel_row['Description'].iloc[0]) else ''
    log_desc_clean = log_desc.strip()
    
    if excel_desc == log_desc_clean:
        matches += 1
        print(f"✅ {col_name}: MATCH")
    else:
        mismatches.append((col_name, log_desc_clean, excel_desc))
        print(f"❌ {col_name}: MISMATCH")
        print(f"   Log:    {log_desc_clean}")
        print(f"   Excel:  {excel_desc}")

print("\n" + "="*80)
print(f"SUMMARY: {matches} matches, {len(mismatches)} mismatches out of {len(log_descriptions)} checked")
print("="*80)

if mismatches:
    print("\n🔴 CRITICAL: These columns have different descriptions!")
    print("The LLM is seeing different descriptions than what's in Benchmarking.xlsx")
    print("This will cause incorrect intent picking!")


