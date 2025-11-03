"""
Script to verify if column descriptions are populated in the semantic schema.
"""
import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.utils.database_util import ChatbotDbUtil

def verify_descriptions(chatbot_id: str = None):
    """Verify descriptions are populated for columns."""
    db = ChatbotDbUtil()
    
    if chatbot_id:
        chatbots = [db.get_chatbot(chatbot_id)]
        if not chatbots[0]:
            print(f"❌ Chatbot {chatbot_id} not found")
            return
    else:
        chatbots = db.get_all_chatbots()
        if not chatbots:
            print("❌ No chatbots found")
            return
    
    print("\n" + "="*80)
    print("DESCRIPTION VERIFICATION REPORT")
    print("="*80)
    
    for chatbot in chatbots:
        cid = chatbot.get('chatbot_id')
        name = chatbot.get('name', 'Unknown')
        
        print(f"\n📊 CHATBOT: {name} (ID: {cid})")
        print("-"*80)
        
        semantic_schema_json = db.get_semantic_schema(cid)
        if not semantic_schema_json:
            print(f"  ⚠️  No semantic schema found")
            continue
        
        try:
            semantic_schema = json.loads(semantic_schema_json)
            tables = semantic_schema.get('tables', {})
            
            total_columns = 0
            columns_with_desc = 0
            columns_without_desc = 0
            
            desc_by_table = {}
            no_desc_by_table = {}
            
            for table_id, table_data in tables.items():
                table_name = table_data.get('display_name') or table_data.get('name') or table_id
                columns = table_data.get('columns', {})
                
                table_with_desc = []
                table_without_desc = []
                
                for col_id, col_data in columns.items():
                    total_columns += 1
                    description = col_data.get('description', '') or ''
                    
                    if description and description.strip():
                        columns_with_desc += 1
                        table_with_desc.append(col_id)
                    else:
                        columns_without_desc += 1
                        table_without_desc.append(col_id)
                
                if table_with_desc:
                    desc_by_table[table_name] = len(table_with_desc)
                if table_without_desc:
                    no_desc_by_table[table_name] = len(table_without_desc)
            
            print(f"\n📈 SUMMARY:")
            print(f"  Total columns: {total_columns}")
            print(f"  ✅ Columns WITH descriptions: {columns_with_desc} ({columns_with_desc/total_columns*100:.1f}%)")
            print(f"  ❌ Columns WITHOUT descriptions: {columns_without_desc} ({columns_without_desc/total_columns*100:.1f}%)")
            
            if desc_by_table:
                print(f"\n✅ TABLES WITH DESCRIPTIONS:")
                for table, count in sorted(desc_by_table.items()):
                    print(f"  - {table}: {count} columns")
            
            if no_desc_by_table:
                print(f"\n❌ TABLES MISSING DESCRIPTIONS:")
                for table, count in sorted(no_desc_by_table.items()):
                    print(f"  - {table}: {count} columns missing descriptions")
            
            # Sample columns without descriptions
            if columns_without_desc > 0:
                print(f"\n📋 SAMPLE COLUMNS WITHOUT DESCRIPTIONS (first 10):")
                sample_count = 0
                for table_id, table_data in tables.items():
                    if sample_count >= 10:
                        break
                    table_name = table_data.get('display_name') or table_data.get('name') or table_id
                    columns = table_data.get('columns', {})
                    for col_id, col_data in columns.items():
                        if sample_count >= 10:
                            break
                        description = col_data.get('description', '') or ''
                        if not description or not description.strip():
                            print(f"  - {table_name}.{col_id}")
                            sample_count += 1
            
        except Exception as e:
            print(f"  ❌ Error processing schema: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    chatbot_id = sys.argv[1] if len(sys.argv) > 1 else None
    if chatbot_id:
        print(f"Verifying descriptions for chatbot: {chatbot_id}")
    else:
        print("Verifying descriptions for all chatbots")
    
    verify_descriptions(chatbot_id)


