#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory-only test that focuses on conversation context without database execution
"""
import sys
sys.path.append('.')
from app.agents.agent_manager import AgentManager
from app.repositories.chatbot_db_util import ChatbotDbUtil
from app.agents.intent_picker import IntentPickerAgent
from app.agents.query_clarification import QueryClarificationAgent
from app.agents.context_clipper import ContextClipperAgent
from app.agents.query_generator import QueryGeneratorAgent
from langchain_core.messages import HumanMessage, AIMessage

def test_memory_system_only():
    """Test the memory system components without database execution"""
    print('🧪 MEMORY-ONLY TEST - Testing Memory System Components')
    print('=' * 70)
    
    try:
        # Initialize components
        print('📊 Step 1: Initializing components...')
        db = ChatbotDbUtil()
        
        test_conv_id = 'bd3d3270-5280-49ce-a749-5a80916e91d8'
        
        print('📊 Step 2: Testing memory retrieval...')
        agent = AgentManager(
            db_util=None,
            checkpoint=None,
            template='Test template',
            chatbot_db_util=db,
            chatbot_id='test'
        )
        
        history = agent._get_conversation_history(test_conv_id)
        print(f'   Retrieved {len(history)} messages from conversation history')
        
        if not history:
            print('❌ No conversation history found!')
            return
            
        print('📊 Step 3: Testing conversation context building...')
        from app.agents.intent_picker import IntentPickerAgent
        intent_picker = IntentPickerAgent(llm=None)  # We'll test without LLM
        
        # Build conversation context
        conversation_context = intent_picker._build_conversation_context(history)
        print(f'   Conversation context: {conversation_context}')
        
        print('📊 Step 4: Testing intent inference from conversation...')
        # Simulate the state with conversation history
        state = {
            'messages': history + [HumanMessage(content="Show me more details about these payments")]
        }
        
        # Test intent inference
        inferred_intent = intent_picker._infer_intent_from_conversation(
            {"tables": [], "columns": []}, 
            conversation_context, 
            "Show me more details about these payments"
        )
        
        print(f'   Inferred intent: {inferred_intent}')
        
        print('📊 Step 5: Testing schema inference from conversation...')
        context_clipper = ContextClipperAgent()
        
        # Test schema inference
        inferred_schema = context_clipper._infer_schema_from_conversation(
            history, 
            ["Payments"], 
            ["Payments.Overall_Tran_Risk_Score"]
        )
        
        print(f'   Inferred schema keys: {list(inferred_schema.keys())}')
        
        print('📊 Step 6: Testing complete memory flow...')
        
        # Test the complete memory flow without database execution
        memory_working = True
        
        # Check 1: Conversation history retrieved
        if len(history) < 2:
            print('❌ FAILED: Not enough conversation history')
            memory_working = False
        else:
            print('✅ PASSED: Conversation history retrieved')
        
        # Check 2: Conversation context built
        if not conversation_context:
            print('❌ FAILED: No conversation context built')
            memory_working = False
        else:
            print('✅ PASSED: Conversation context built')
        
        # Check 3: Intent inferred from context
        if not inferred_intent.get('tables') or not inferred_intent.get('columns'):
            print('❌ FAILED: Intent not inferred from conversation context')
            memory_working = False
        else:
            print('✅ PASSED: Intent inferred from conversation context')
        
        # Check 4: Schema inferred from context
        if not inferred_schema:
            print('❌ FAILED: Schema not inferred from conversation context')
            memory_working = False
        else:
            print('✅ PASSED: Schema inferred from conversation context')
        
        # Check 5: Risk score context detected
        if 'Overall_Tran_Risk_Score' not in str(inferred_intent.get('columns', [])):
            print('❌ FAILED: Risk score context not detected')
            memory_working = False
        else:
            print('✅ PASSED: Risk score context detected')
        
        print('=' * 70)
        print('🎯 MEMORY-ONLY TEST RESULTS')
        print()
        
        if memory_working:
            print('✅ MEMORY SYSTEM IS WORKING PERFECTLY!')
            print('✅ All memory components are functioning correctly')
            print('✅ Conversation context is being used properly')
            print('✅ Follow-up queries are treated as continuations')
            print('✅ No issues found in the memory system')
        else:
            print('❌ MEMORY SYSTEM HAS ISSUES')
            print('❌ Some memory components are not working correctly')
        
        return memory_working
        
    except Exception as e:
        print(f'❌ Error during memory-only test: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_memory_system_only()

