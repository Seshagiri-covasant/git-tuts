# Enhanced Conversational Intent Analyzer

This document explains the enhanced conversational intent analyzer that provides ChatGPT/Claude/Gemini-like conversational experiences for natural language to SQL queries.

## Overview

The enhanced conversational system follows the AWS sample repository pattern of decomposing NL-to-SQL conversion into smaller sub-problems, enabling the use of smaller LLMs while maintaining high accuracy and providing a conversational experience.

## Key Components

### 1. AdvancedConversationalIntentAnalyzer

The core component that analyzes user intent and determines if clarification is needed.

**Key Features:**
- Schema-aware intent analysis
- Ambiguity detection
- Entity validation against database schema
- Conversational memory management
- Multi-round clarification support

**Usage:**
```python
from app.agents.advanced_conversational_intent_analyzer import AdvancedConversationalIntentAnalyzer

# Initialize with LLM
intent_analyzer = AdvancedConversationalIntentAnalyzer(llm, chatbot_db_util, chatbot_id)

# Analyze user intent
state = {
    "user_question": "Show me employees",
    "conversation_history": [],
    "knowledge_data": schema_data
}

result = intent_analyzer.analyze_intent(state)
```

### 2. EnhancedQueryClarification

Handles the conversational clarification flow, similar to ChatGPT interactions.

**Key Features:**
- Multi-turn clarification conversations
- Context-aware question generation
- User response interpretation
- Intent modification support

**Usage:**
```python
from app.agents.enhanced_query_clarification import EnhancedQueryClarification

# Initialize clarification agent
clarification_agent = EnhancedQueryClarification(llm, chatbot_db_util, chatbot_id)

# Handle clarification flow
result = clarification_agent.run(state)
```

### 3. ConversationalMemoryManager

Manages conversation memory and state throughout the interaction.

**Key Features:**
- Conversation history loading
- State tracking
- Memory persistence
- Context management

**Usage:**
```python
from app.agents.conversational_memory_manager import ConversationalMemoryManager

# Initialize memory manager
memory_manager = ConversationalMemoryManager(chatbot_db_util, chatbot_id)

# Load conversation history
conversation_history = memory_manager.load_conversation_history(conversation_id)
```

## Conversation Flow

### 1. Initial Intent Analysis

When a user asks a question, the system:

1. **Analyzes Intent**: Uses the LLM to understand the user's intent
2. **Validates Against Schema**: Checks if identified entities exist in the database
3. **Detects Ambiguities**: Identifies unclear or ambiguous parts of the query
4. **Determines Clarification Need**: Decides if clarification is needed

### 2. Clarification Process

If clarification is needed:

1. **Generates Questions**: Creates specific clarification questions
2. **Engages in Dialogue**: Asks follow-up questions like ChatGPT
3. **Handles Responses**: Processes user responses and updates understanding
4. **Iterates**: Continues until intent is clear

### 3. Confirmation Process

Once intent is clear:

1. **Generates Summary**: Creates a summary of understood intent
2. **Seeks Confirmation**: Asks user to confirm understanding
3. **Handles Modifications**: Allows user to modify intent if needed
4. **Proceeds**: Moves to query generation when confirmed

## Example Conversation

```
User: "Show me the data"

AI: "I'd like to make sure I understand your question correctly so I can give you the best results.

1. What specific data are you looking for? (employees, projects, departments, etc.)
2. Which table or tables should I query?
3. Do you want to see all records or apply any filters?

Please provide the additional information so I can help you get exactly what you need."

User: "I want to see employees in the engineering department"

AI: "Perfect! Based on your question, I understand you want to:

• Work with employee data
• Query the following tables: employees
• Focus on these columns: name, department
• Perform a filter operation

Does this look correct? If yes, I'll proceed with generating the SQL query. If you'd like to make any changes, just let me know!"

User: "Yes, that's correct"

AI: "Perfect! I'll now generate the SQL query based on your requirements."
```

## Integration with Existing System

### 1. Planner Integration

The enhanced clarification is integrated into the existing planner workflow:

```python
# In planner.py
from .enhanced_query_clarification import EnhancedQueryClarification

# Create enhanced clarification agent
enhanced_clarification = EnhancedQueryClarification(
    query_clarification.llm, chatbot_db_util, chatbot_id
)

# Add to workflow
self.workflow.add_node("Enhanced_Query_Clarification", enhanced_clarification.run)
```

### 2. Agent Manager Integration

The agent manager now includes memory management:

```python
# In agent_manager.py
from .conversational_memory_manager import ConversationalMemoryManager

# Initialize memory manager
self.memory_manager = ConversationalMemoryManager(chatbot_db_util, chatbot_id)
```

## Configuration

### Environment Variables

No additional environment variables are required. The system uses existing LLM and database configurations.

### Template Integration

The system works with existing prompt templates and enhances them with conversational capabilities.

## Testing

Run the test script to see the enhanced conversational flow in action:

```bash
python test_enhanced_conversational_flow.py
```

This will demonstrate:
- Intent analysis with different query types
- Clarification flow for ambiguous queries
- Memory management
- Complete conversation flows

## Benefits

### 1. Improved User Experience
- Natural conversation flow like ChatGPT/Claude
- No need to be perfectly specific in initial queries
- Guided clarification process

### 2. Better Accuracy
- Schema-aware validation
- Multi-round clarification
- Intent confirmation before query generation

### 3. Reduced LLM Costs
- Uses smaller models effectively
- Decomposes complex problems into simpler ones
- Follows AWS sample pattern for efficiency

### 4. Maintainable Code
- Modular design
- Clear separation of concerns
- Easy to extend and modify

## Troubleshooting

### Common Issues

1. **Memory Not Loading**: Check if chatbot_db_util is properly initialized
2. **Clarification Loops**: Ensure proper state management in conversation flow
3. **Intent Analysis Failures**: Verify LLM configuration and schema data

### Debug Information

Use the conversation summary for debugging:

```python
summary = memory_manager.get_conversation_summary()
print(f"Conversation state: {summary}")
```

## Future Enhancements

1. **Voice Integration**: Add speech-to-text capabilities
2. **Multi-language Support**: Support for different languages
3. **Advanced Context**: Better business context understanding
4. **Learning**: Learn from user interactions to improve responses

## References

- [AWS Natural Language Data Retrieval Sample](https://github.com/aws-samples/blog-natural-language-data-retrieval)
- LangChain Documentation
- LangGraph Documentation


