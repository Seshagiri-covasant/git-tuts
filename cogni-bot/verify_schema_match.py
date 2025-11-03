"""Verify if the schema being used by LLM matches Benchmarking.xlsx"""
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def load_semantic_schema_from_db(chatbot_id: str):
    """Load semantic schema from database"""
    try:
        from app.repositories.chatbot_db_util import ChatbotDbUtil
        
        db = ChatbotDbUtil()
        semantic_schema_json = db.get_semantic_schema(chatbot_id)
        
        if not semantic_schema_json:
            print(f"❌ No semantic schema found for chatbot {chatbot_id}")
            return None
        
        import json
        return json.loads(semantic_schema_json)
    except Exception as e:
        print(f"❌ Error loading semantic schema: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_schema_with_benchmark(db_schema, benchmark_file='Benchmarking.xlsx'):
    """Compare database schema with Benchmarking.xlsx"""
    
    if not db_schema:
        print("❌ No database schema to compare")
        return
    
    # Load Benchmarking.xlsx
    try:
        excel_invoices = pd.read_excel(benchmark_file, sheet_name='Invoices Schema')
        excel_payments = pd.read_excel(benchmark_file, sheet_name='Payments Schema')
        print("✅ Loaded Benchmarking.xlsx")
    except Exception as e:
        print(f"❌ Error loading Benchmarking.xlsx: {e}")
        return
    
    # Extract schema from database
    db_tables = db_schema.get('tables', {})
    
    print("\n" + "="*80)
    print("SCHEMA COMPARISON: Database Schema vs Benchmarking.xlsx")
    print("="*80)
    
    # Compare Invoices table
    if 'Invoices' in db_tables:
        print("\n📊 INVOICES TABLE COMPARISON")
        print("-" * 80)
        compare_table(db_tables['Invoices'], excel_invoices, 'Invoices')
    else:
        print("\n⚠️  Invoices table not found in database schema")
    
    # Compare Payments table
    if 'Payments' in db_tables:
        print("\n📊 PAYMENTS TABLE COMPARISON")
        print("-" * 80)
        compare_table(db_tables['Payments'], excel_payments, 'Payments')
    else:
        print("\n⚠️  Payments table not found in database schema")

def compare_table(db_table, excel_df, table_name):
    """Compare a single table"""
    
    db_columns = db_table.get('columns', {})
    excel_cols = set(excel_df['Column Name'].str.strip())
    
    print(f"\nColumn Count:")
    print(f"  Database: {len(db_columns)} columns")
    print(f"  Excel: {len(excel_cols)} columns")
    
    # Get common columns
    db_col_names = set(db_columns.keys())
    common = db_col_names & excel_cols
    
    print(f"\nCommon columns: {len(common)}")
    print(f"Only in Database: {len(db_col_names - excel_cols)}")
    print(f"Only in Excel: {len(excel_cols - db_col_names)}")
    
    # Compare descriptions
    matches = 0
    mismatches = []
    missing_desc_db = []
    missing_desc_excel = []
    
    for col_name in sorted(common):
        db_col = db_columns.get(col_name, {})
        db_desc = db_col.get('description', '') or '' if isinstance(db_col, dict) else ''
        
        excel_row = excel_df[excel_df['Column Name'].str.strip() == col_name]
        excel_desc = excel_row['Description'].iloc[0].strip() if not excel_row.empty and pd.notna(excel_row['Description'].iloc[0]) else ''
        
        if not db_desc and not excel_desc:
            continue  # Both empty, skip
        elif not db_desc:
            missing_desc_db.append(col_name)
        elif not excel_desc:
            missing_desc_excel.append(col_name)
        elif db_desc.strip() == excel_desc.strip():
            matches += 1
        else:
            mismatches.append({
                'column': col_name,
                'db': db_desc,
                'excel': excel_desc
            })
    
    print(f"\n📝 DESCRIPTION COMPARISON:")
    print(f"  ✅ Matches: {matches}/{len(common)} ({matches/len(common)*100:.1f}% if all had descriptions)")
    print(f"  ❌ Mismatches: {len(mismatches)}")
    print(f"  ⚠️  Missing in Database: {len(missing_desc_db)}")
    print(f"  ⚠️  Missing in Excel: {len(missing_desc_excel)}")
    
    if mismatches:
        print(f"\n❌ DESCRIPTION MISMATCHES (showing first 10):")
        for i, mismatch in enumerate(mismatches[:10], 1):
            print(f"\n{i}. {mismatch['column']}:")
            print(f"   Database: {mismatch['db']}")
            print(f"   Excel:    {mismatch['excel']}")
    
    if missing_desc_db:
        print(f"\n⚠️  MISSING DESCRIPTIONS IN DATABASE (showing first 10):")
        for col in missing_desc_db[:10]:
            print(f"  - {col}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python verify_schema_match.py <chatbot_id>")
        print("\nThis script compares the schema stored in the database with Benchmarking.xlsx")
        sys.exit(1)
    
    chatbot_id = sys.argv[1]
    
    print(f"Loading semantic schema for chatbot: {chatbot_id}")
    db_schema = load_semantic_schema_from_db(chatbot_id)
    
    if db_schema:
        compare_schema_with_benchmark(db_schema)
    else:
        print("\n❌ Could not load schema from database. Make sure:")
        print("   1. The chatbot_id is correct")
        print("   2. The database is configured and schema is extracted")
        print("   3. Descriptions have been imported if needed")


