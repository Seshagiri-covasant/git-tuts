"""
Test script for intent picker agent.
Tests column selection with sample queries.
"""
import sys
import os
import json

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.agents.intent_picker import AdvancedIntentPicker
from backend.app.utils.database_util import ChatbotDbUtil
from backend.app.services.knowledge_cache_service import get_knowledge_data
from langchain_openai import ChatOpenAI

def test_intent_picker(chatbot_id: str, test_question: str):
    """Test intent picker with a sample question."""
    
    print("\n" + "="*80)
    print("INTENT PICKER TEST")
    print("="*80)
    print(f"Chatbot ID: {chatbot_id}")
    print(f"Test Question: {test_question}")
    print("="*80 + "\n")
    
    # Initialize database connection
    db = ChatbotDbUtil()
    chatbot = db.get_chatbot(chatbot_id)
    if not chatbot:
        print(f"❌ Chatbot {chatbot_id} not found")
        return
    
    print(f"✅ Chatbot found: {chatbot.get('name', 'Unknown')}\n")
    
    # Get knowledge data (schema)
    try:
        knowledge_data = get_knowledge_data(chatbot_id, db)
        if not knowledge_data:
            print("❌ Could not load knowledge data (schema)")
            return
        
        schema = knowledge_data.get('schema', {})
        tables = schema.get('tables', {})
        print(f"✅ Knowledge data loaded:")
        print(f"   Tables: {len(tables)}")
        
        # Check description coverage
        total_cols = 0
        cols_with_desc = 0
        for table_name, table_data in tables.items():
            columns = table_data.get('columns', {})
            for col_name, col_data in columns.items():
                total_cols += 1
                if isinstance(col_data, dict):
                    desc = col_data.get('description', '') or ''
                    if desc and desc.strip():
                        cols_with_desc += 1
        
        desc_percent = (cols_with_desc / total_cols * 100) if total_cols > 0 else 0
        print(f"   Total columns: {total_cols}")
        print(f"   Columns with descriptions: {cols_with_desc} ({desc_percent:.1f}%)")
        print()
        
    except Exception as e:
        print(f"❌ Error loading knowledge data: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Initialize LLM (you may need to set OPENAI_API_KEY environment variable)
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        print("✅ LLM initialized (GPT-4o)\n")
    except Exception as e:
        print(f"❌ Error initializing LLM: {e}")
        print("   Make sure OPENAI_API_KEY environment variable is set")
        return
    
    # Initialize intent picker
    intent_picker = AdvancedIntentPicker(llm)
    
    # Prepare state
    state = {
        'user_question': test_question,
        'conversation_history': [],
        'knowledge_data': knowledge_data
    }
    
    # Run intent picker
    print("🔄 Running intent picker...\n")
    try:
        result = intent_picker.run(state)
        
        intent = result.get('intent', {})
        selected_tables = intent.get('tables', [])
        selected_columns = intent.get('columns', [])
        reasoning = intent.get('reasoning', 'No reasoning provided')
        confidence = result.get('confidence_scores', {})
        
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)
        print(f"📊 Selected Tables: {selected_tables}")
        print(f"📋 Selected Columns: {selected_columns}")
        print(f"🎯 Confidence Scores: {confidence}")
        print(f"\n💭 Reasoning:\n{reasoning}\n")
        
        # Validate selections
        print("="*80)
        print("VALIDATION")
        print("="*80)
        
        # Check if tables exist
        for table in selected_tables:
            if table in tables:
                print(f"✅ Table '{table}' exists in schema")
            else:
                print(f"❌ Table '{table}' NOT FOUND in schema")
        
        # Check if columns exist in selected tables
        for col in selected_columns:
            found = False
            for table in selected_tables:
                if table in tables:
                    table_columns = tables[table].get('columns', {})
                    if col in table_columns:
                        found = True
                        col_data = table_columns[col]
                        desc = col_data.get('description', '') if isinstance(col_data, dict) else ''
                        if desc:
                            print(f"✅ Column '{col}' in table '{table}' (has description)")
                        else:
                            print(f"⚠️  Column '{col}' in table '{table}' (NO description)")
                        break
            
            if not found:
                print(f"❌ Column '{col}' NOT FOUND in selected tables")
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n❌ Error running intent picker: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_intent_picker.py <chatbot_id> <test_question>")
        print("\nExample:")
        print('  python test_intent_picker.py "your-chatbot-id" "Which vendors have payment risk score above 10?"')
        sys.exit(1)
    
    chatbot_id = sys.argv[1]
    test_question = " ".join(sys.argv[2:])
    
    test_intent_picker(chatbot_id, test_question)


