#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete end-to-end test of the memory and clarification system
"""
import sys
sys.path.append('.')
from app.agents.agent_manager import AgentManager
from app.repositories.chatbot_db_util import ChatbotDbUtil
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

def test_end_to_end_flow():
    print('🧪 Testing Complete End-to-End Flow...')
    print('=' * 60)
    
    try:
        # Initialize components
        db = ChatbotDbUtil()
        agent = AgentManager(
            db_util=None,
            checkpoint=None,
            template='Test template',
            chatbot_db_util=db,
            chatbot_id='test'
        )
        
        test_conv_id = 'bd3d3270-5280-49ce-a749-5a80916e91d8'
        
        print('📊 Step 1: Testing memory retrieval...')
        history = agent._get_conversation_history(test_conv_id)
        print(f'   Retrieved {len(history)} messages from database')
        
        if not history:
            print('❌ No conversation history found!')
            return
            
        print('📊 Step 2: Analyzing message format...')
        for i, msg in enumerate(history):
            print(f'   Message {i+1}: {msg.__class__.__name__} - {msg.content[:50]}...')
        
        print('📊 Step 3: Testing QueryClarificationAgent with real conversation...')
        from app.agents.query_clarification import QueryClarificationAgent
        clarification_agent = QueryClarificationAgent()
        
        # Create state with the real conversation history
        state = {
            'messages': history,
            'intent': {
                'tables': ['Payments'],
                'columns': [],
                'filters': []
            }
        }
        
        print('📊 Step 4: Running clarification agent...')
        result = clarification_agent.run(state, 'test', db)
        
        print('📊 Step 5: Analyzing results...')
        clarification_needed = result.get('clarification_needed', False)
        original_question = result.get('original_question', 'None')
        updated_intent = result.get('intent', {})
        
        print(f'   Clarification needed: {clarification_needed}')
        print(f'   Original question: {original_question}')
        print(f'   Updated intent: {updated_intent}')
        
        # Check if this is a clarification response scenario
        last_message = history[-1] if history else None
        if last_message and hasattr(last_message, 'content'):
            last_content = last_message.content
            print(f'   Last message content: {last_content[:100]}...')
            
            # Check if the last message looks like a clarification response
            is_clarification_response = any(col in last_content for col in [
                'Overall_Tran_Risk_Score', 'ML_Risk_Score', 'Overall_Risk_Score'
            ])
            
            print(f'   Looks like clarification response: {is_clarification_response}')
            
            if is_clarification_response and not clarification_needed:
                print('✅ SUCCESS: Clarification response was properly detected and processed!')
                print('✅ The system correctly recognized the user response and stopped asking for clarification.')
            elif is_clarification_response and clarification_needed:
                print('❌ FAILED: System still asking for clarification despite user response.')
            else:
                print('ℹ️  INFO: This appears to be a new query, not a clarification response.')
        
        print('📊 Step 6: Testing intent update...')
        columns = updated_intent.get('columns', [])
        if columns:
            print(f'   Updated columns: {columns}')
            if 'Overall_Tran_Risk_Score' in str(columns):
                print('✅ SUCCESS: Column was correctly added to intent!')
            else:
                print('❌ FAILED: Column was not properly added to intent.')
        else:
            print('ℹ️  No columns in updated intent.')
            
        print('=' * 60)
        print('🎯 END-TO-END TEST COMPLETE')
        
    except Exception as e:
        print(f'❌ Error during end-to-end test: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_end_to_end_flow()

