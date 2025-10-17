# Enhanced Conversational Intent Analyzer System

## 🎯 Overview

The Enhanced Conversational Intent Analyzer System is a comprehensive solution for building advanced conversational AI agents that can engage in natural dialogue with users to understand their intent and generate accurate SQL queries. The system features:

- **200+ line comprehensive prompts** without hardcoding
- **Agent thoughts and reasoning** logging
- **ConversationBufferMemory** for proper context management
- **Multi-turn conversation** capability
- **Schema-aware clarification** system
- **Comprehensive error handling** and fallback strategies

## 🏗️ Architecture

### Core Components

1. **EnhancedAgentManager** - Orchestrates the complete workflow
2. **AdvancedConversationalIntentAnalyzer** - Handles conversational intent analysis
3. **EnhancedIntentPicker** - Picks user intent with deep analysis
4. **EnhancedQueryGenerator** - Generates SQL with comprehensive prompts
5. **EnhancedQueryValidator** - Validates SQL for syntax, security, and performance
6. **EnhancedQueryExecutor** - Executes queries and processes results

### Workflow Phases

```
Initial Question → Intent Analysis → Intent Picking → Query Generation → Query Validation → Query Execution → Results
```

## 🚀 Features

### 1. Comprehensive Prompts (200+ Lines Each)

Each agent uses detailed, comprehensive prompts that:
- **No Hardcoding**: Completely generic and flexible
- **Schema-Aware**: Leverages database schema information
- **Business Context**: Understands business requirements
- **Error Handling**: Includes comprehensive error handling
- **Quality Assurance**: Built-in quality checks

### 2. Agent Thoughts and Reasoning

Every agent logs detailed thoughts and reasoning:
```python
thought = f"[AGENT THOUGHT] Starting intent analysis for: '{user_question}'"
self.agent_thoughts.append(thought)
```

**Example Agent Thoughts:**
- `[AGENT THOUGHT] Starting intent analysis for: 'Which payments have a risk score above 10?'`
- `[AGENT THOUGHT] Intent analysis complete: SELECT`
- `[AGENT THOUGHT] Generated SQL: SELECT * FROM payments WHERE risk_score > 10`
- `[AGENT THOUGHT] Query validation: Valid`
- `[AGENT THOUGHT] Query execution: Success`

### 3. ConversationBufferMemory

Proper memory management for multi-turn conversations:
```python
self.memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    output_key="output"
)
```

### 4. Multi-Turn Conversation Flow

The system supports natural conversation flow:
1. **Initial Question** - User asks a question
2. **Intent Analysis** - System analyzes intent
3. **Clarification** - If needed, system asks for clarification
4. **User Response** - User provides clarification
5. **Intent Refinement** - System refines understanding
6. **Query Generation** - System generates SQL
7. **Execution** - System executes and returns results

### 5. Schema-Aware Clarification

The system intelligently asks for clarification based on:
- **Schema Information** - Available tables, columns, metrics
- **Business Context** - Business meaning of data
- **Ambiguity Detection** - Identifies unclear elements
- **Context Preservation** - Maintains conversation context

## 📁 File Structure

```
cogni-bot/backend/app/agents/
├── enhanced_agent_manager.py              # Main orchestrator
├── advanced_conversational_intent_analyzer.py  # Conversational intent analysis
├── enhanced_intent_picker.py            # Intent picking with deep analysis
├── enhanced_query_generator.py           # SQL generation with comprehensive prompts
├── enhanced_query_validator.py           # Query validation and security analysis
├── enhanced_query_executor.py            # Query execution and result processing
└── test_enhanced_workflow.py             # Test script
```

## 🔧 Usage

### Basic Usage

```python
from app.agents.enhanced_agent_manager import EnhancedAgentManager
from app.utils.llm_util import get_llm

# Initialize
llm = get_llm()
agent_manager = EnhancedAgentManager(llm, chatbot_db_util, chatbot_id, app_db_util)

# Execute workflow
state = {
    'user_question': 'Which payments have a risk score above 10?',
    'conversation_history': [],
    'agent_thoughts': []
}

result = agent_manager.execute(state)
```

### Handling Clarifications

```python
# If clarification is needed
if result.get('clarification_needed'):
    clarification_state = {
        **result,
        'user_question': 'I want to see all payment details with risk scores above 10',
        'conversation_history': result.get('conversation_history', []) + [{
            'role': 'assistant',
            'content': result.get('clarification_question', '')
        }]
    }
    
    clarification_result = agent_manager.handle_clarification_response(clarification_state)
```

### Accessing Agent Thoughts

```python
# Get all agent thoughts
agent_thoughts = result.get('agent_thoughts', [])
for thought in agent_thoughts:
    print(f"💭 {thought}")

# Get conversation summary
summary = agent_manager.get_conversation_summary()
print(f"📊 Conversation Phase: {summary['conversation_phase']}")
print(f"💭 Agent Thoughts: {len(summary['agent_thoughts'])}")
```

## 🧪 Testing

### Run Test Suite

```bash
cd cogni-bot/backend
python test_enhanced_workflow.py
```

### Test Cases

The test suite includes:
1. **Clear Questions** - Direct, unambiguous requests
2. **Ambiguous Questions** - Vague requests requiring clarification
3. **Complex Questions** - Multi-part requests with aggregations

### Example Test Output

```
🧪 TEST CASE 1: Clear Question
📝 Question: Which payments have a risk score above 10?
🎯 Expected Phase: completed

📊 RESULTS:
  - Conversation Phase: completed
  - Workflow Status: completed
  - Clarification Needed: False
  - Generated SQL: SELECT * FROM payments WHERE risk_score > 10
  - Execution Success: True
  - Row Count: 25

💭 AGENT THOUGHTS (5 thoughts):
  1. [MANAGER THOUGHT] Starting enhanced workflow for: 'Which payments have a risk score above 10?'
  2. [AGENT THOUGHT] Starting intent analysis for: 'Which payments have a risk score above 10?'
  3. [AGENT THOUGHT] Intent analysis complete: SELECT
  4. [AGENT THOUGHT] Generated SQL: SELECT * FROM payments WHERE risk_score > 10
  5. [MANAGER THOUGHT] Workflow completed with status: completed
```

## 🔍 Agent Thoughts Examples

### Intent Analysis Thoughts
```
[AGENT THOUGHT] Starting intent analysis for: 'Which payments have a risk score above 10?'
[AGENT THOUGHT] Analyzing initial question: 'Which payments have a risk score above 10?'
[AGENT THOUGHT] Parsed analysis: {'needs_clarification': False, 'gathered_info': {...}}
[AGENT THOUGHT] Moving to summary phase - question appears clear
[AGENT THOUGHT] Intent analysis complete: SELECT
```

### Query Generation Thoughts
```
[AGENT THOUGHT] Starting SQL generation for: 'Which payments have a risk score above 10?'
[AGENT THOUGHT] Generated SQL: SELECT * FROM payments WHERE risk_score > 10
[AGENT THOUGHT] SQL generation complete: Success
```

### Validation Thoughts
```
[AGENT THOUGHT] Starting query validation for: 'SELECT * FROM payments WHERE risk_score > 10'
[AGENT THOUGHT] Query validation: Valid
[AGENT THOUGHT] Validation complete: Valid
```

### Execution Thoughts
```
[AGENT THOUGHT] Starting query execution for: 'SELECT * FROM payments WHERE risk_score > 10'
[AGENT THOUGHT] Query execution complete: True
[AGENT THOUGHT] Query execution: Success
```

## 🎯 Key Benefits

### 1. **No Hardcoding**
- All prompts are completely generic
- No hardcoded table names, column names, or metric names
- Flexible and adaptable to any schema

### 2. **Comprehensive Logging**
- Detailed agent thoughts and reasoning
- Complete workflow visibility
- Easy debugging and troubleshooting

### 3. **Natural Conversation**
- Human-like dialogue flow
- Context-aware clarifications
- Progressive information gathering

### 4. **Schema Awareness**
- Leverages database schema information
- Understands business context
- Provides intelligent suggestions

### 5. **Error Handling**
- Comprehensive error detection
- Graceful fallback strategies
- Detailed error reporting

## 🔧 Configuration

### Environment Variables

```bash
# Database configuration
DATABASE_URL=postgresql://user:password@localhost:5432/database
CHATBOT_DB_URL=sqlite:///chatbot.db

# LLM configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_API_BASE=https://your-openai-endpoint.com
```

### LLM Configuration

```python
from app.utils.llm_util import get_llm

# The system uses the configured LLM from llm_util
llm = get_llm()
```

## 📊 Performance Considerations

### Memory Management
- **ConversationBufferMemory**: Efficient memory management
- **Context Preservation**: Maintains conversation context
- **Thought Tracking**: Tracks agent reasoning

### Query Optimization
- **Schema Validation**: Ensures query efficiency
- **Index Usage**: Optimizes for available indexes
- **Performance Analysis**: Analyzes query performance

### Error Recovery
- **Graceful Degradation**: Handles errors gracefully
- **Fallback Strategies**: Provides alternative approaches
- **User Guidance**: Guides users through issues

## 🚀 Future Enhancements

### Planned Features
1. **Advanced Memory Management** - Long-term memory capabilities
2. **Multi-Modal Support** - Support for images and documents
3. **Real-Time Collaboration** - Multi-user conversation support
4. **Advanced Analytics** - Detailed conversation analytics
5. **Custom Agent Types** - Specialized agents for different domains

### Integration Opportunities
1. **API Integration** - REST API for external systems
2. **WebSocket Support** - Real-time communication
3. **Database Integration** - Direct database connections
4. **Cloud Deployment** - Cloud-native deployment options

## 📝 Contributing

### Development Guidelines
1. **No Hardcoding** - Keep all prompts generic
2. **Comprehensive Logging** - Add detailed agent thoughts
3. **Error Handling** - Include comprehensive error handling
4. **Testing** - Add test cases for new features
5. **Documentation** - Update documentation for changes

### Code Standards
- **Type Hints** - Use proper type annotations
- **Docstrings** - Include comprehensive docstrings
- **Error Handling** - Handle all possible errors
- **Logging** - Add detailed logging throughout

## 📞 Support

For questions, issues, or contributions:
1. **GitHub Issues** - Report bugs and feature requests
2. **Documentation** - Check this documentation
3. **Code Review** - Submit pull requests for review
4. **Testing** - Run test suite before submitting

---

**Enhanced Conversational Intent Analyzer System** - Building the future of conversational AI for database interactions.
