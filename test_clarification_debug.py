#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to debug clarification system
"""
import sys
sys.path.append('.')
from app.agents.query_clarification import QueryClarificationAgent
from app.repositories.chatbot_db_util import ChatbotDbUtil

def test_clarification_logic():
    print('🔍 Testing Clarification Logic...')
    try:
        db = ChatbotDbUtil()
        agent = QueryClarificationAgent()
        
        # Simulate the conversation state
        test_conv_id = 'bd3d3270-5280-49ce-a749-5a80916e91d8'
        
        # Get conversation history
        with db.db_engine.connect() as conn:
            query = db.interactions_table.select().where(
                db.interactions_table.c.conversation_id == test_conv_id
            ).order_by(db.interactions_table.c.start_time.desc()).limit(10)
            
            interactions = conn.execute(query).fetchall()
            
            conversation_history = []
            for interaction in reversed(interactions):
                interaction_dict = dict(interaction._mapping)
                
                if interaction_dict.get('request'):
                    conversation_history.append({
                        "role": "human", 
                        "content": interaction_dict['request']
                    })
                
                if interaction_dict.get('final_result'):
                    conversation_history.append({
                        "role": "assistant", 
                        "content": interaction_dict['final_result']
                    })
        
        print(f'📊 Retrieved {len(conversation_history)} messages')
        
        # Test the clarification logic
        state = {
            'messages': conversation_history,
            'intent': {
                'tables': ['Payments'],
                'columns': [],
                'filters': ['Payments.Overall_Tran_Risk_Score > 10']
            }
        }
        
        print('🧪 Testing clarification detection...')
        result = agent.run(state, 'test', db)
        
        print(f'📋 Clarification needed: {result.get("clarification_needed", False)}')
        print(f'📋 Original question: {result.get("original_question", "None")}')
        
        if result.get("clarification_needed"):
            print('✅ Clarification is being triggered correctly')
        else:
            print('❌ Clarification is NOT being triggered - this is the problem!')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_clarification_logic()

