# Orchestration Agent → SQL Agent Integration Specification

## Overview
This document specifies the exact requirements for the Orchestration Agent to properly call the SQL Agent backend.

## Current Orchestration Agent Configuration

Currently, the orchestration agent has:
```python
{
    "name": "SQLAgent",
    "endpoint": "http://172.212.177.27/api/chat/sqlagent",
    "headers": {
        "clientId": "1B3C139A-562B-4AD4-B107-8096115F5E9F",
        "projectId": "5CC5E342-4EAD-49D5-A595-963719A0EEC9",
        "Module": "P2P",
        "Submodule": "Payments",
        "shareData": "true"
    }
}
```

## Required Changes to Orchestration Agent

### 1. Update Endpoint URL

**Current (incorrect):**
```
http://172.212.177.27/api/chat/sqlagent
```

**Required (correct):**
```
http://172.212.177.27/api/interactions/start
```

### 2. Required Headers

The SQL Agent expects these headers (all must be sent):

| Header Name | Required | Description | Example |
|------------|----------|-------------|---------|
| `clientId` | **YES** | External client identifier | `1B3C139A-562B-4AD4-B107-8096115F5E9F` |
| `projectId` | **YES** | External project identifier | `5CC5E342-4EAD-49D5-A595-963719A0EEC9` |
| `Module` | Optional | Functional module context | `P2P` |
| `Submodule` | Optional | Functional submodule context | `Payments` |
| `Content-Type` | **YES** | Request content type | `application/json` |

**Note:** `shareData` header is not used by SQL Agent and can be omitted.

### 3. Request Body Format

**Required fields:**
```json
{
  "message": "user's natural language question"
}
```

**Optional fields:**
```json
{
  "message": "user's natural language question",
  "conversation_id": "optional-existing-conversation-id"
}
```

**Note:** 
- `chatbot_id` should NOT be in the body - it will be resolved automatically from `clientId`/`projectId` headers
- If `conversation_id` is provided, the SQL agent will continue the existing conversation
- If `conversation_id` is NOT provided, SQL agent will create a new conversation automatically

### 4. Complete Request Example

**Method:** `POST`  
**URL:** `http://172.212.177.27/api/interactions/start`  
**Headers:**
```
clientId: 1B3C139A-562B-4AD4-B107-8096115F5E9F
projectId: 5CC5E342-4EAD-49D5-A595-963719A0EEC9
Module: P2P
Submodule: Payments
Content-Type: application/json
```

**Body:**
```json
{
  "message": "who are top risk vendors",
  "conversation_id": "optional-conversation-id-if-continuing"
}
```

## Response Format

The SQL Agent returns one of three response types:

### 1. Successful Query Response

**Status:** `201 Created`

**Body:**
```json
{
  "interaction_id": "uuid-of-interaction",
  "conversation_id": "uuid-of-conversation",
  "response": "The answer to the user's question...",
  "cleaned_query": "SELECT ... FROM ...",
  "interaction_type": "response"
}
```

### 2. Clarification Needed

**Status:** `201 Created`

**Body:**
```json
{
  "question": "Which column did you mean?",
  "interaction_type": "clarification",
  "conversation_id": "uuid-of-conversation"
}
```

### 3. Human Approval Needed

**Status:** `201 Created`

**Body:**
```json
{
  "approval_request": {
    "source_agent": "SQL_Agent",
    "clarification_details": {
      "type": "CHOICE_SELECTION",
      "question_text": "Which option matches what you're looking for?",
      "options": [
        {
          "id": "column_name_1",
          "display_name": "Column Name 1",
          "description": "Description of column 1"
        }
      ]
    }
  },
  "clarification_questions": [],
  "similar_columns": [],
  "ambiguity_analysis": {},
  "interaction_type": "human_approval",
  "conversation_id": "uuid-of-conversation"
}
```

## Prerequisites (Before First Call)

### Chatbot Registration Required

Before the orchestration agent can call the SQL agent, the mapping between `clientId`/`projectId` and internal `chatbot_id` must be registered.

**Registration Endpoint:**
```
POST http://172.212.177.27/api/chatbots/{chatbot_id}/register
```

**Registration Body:**
```json
{
  "clientId": "1B3C139A-562B-4AD4-B107-8096115F5E9F",
  "projectId": "5CC5E342-4EAD-49D5-A595-963719A0EEC9"
}
```

**This registration is a one-time setup** - after registration, all subsequent calls using those `clientId`/`projectId` headers will automatically map to the correct `chatbot_id`.

## Error Responses

### 404 - Chatbot Not Found
```json
{
  "error": "No chatbot mapped for provided clientId/projectId"
}
```
**Action:** Register the chatbot using the registration endpoint above.

### 400 - Bad Request
```json
{
  "error": "Must provide chatbot_id or clientId/projectId"
}
```
**Action:** Ensure both `clientId` and `projectId` headers are present.

### 400 - Missing Message
```json
{
  "error": "Invalid request body: {'message': ['Missing data for required field.']}"
}
```
**Action:** Ensure `message` field is present in request body.

## Orchestration Agent Code Changes

### In `agent_config.py`:

**Current:**
```python
{
    "name": "SQLAgent",
    "endpoint": "http://172.212.177.27/api/chat/sqlagent",
    "input_schema": {
        "message": "str",
        "conversation_id": "str"
    },
    "headers": {
        "clientId": "1B3C139A-562B-4AD4-B107-8096115F5E9F",
        "projectId": "5CC5E342-4EAD-49D5-A595-963719A0EEC9",
        "Module": "P2P",
        "Submodule": "Payments",
        "shareData": "true"
    }
}
```

**Required:**
```python
{
    "name": "SQLAgent",
    "endpoint": "http://172.212.177.27/api/interactions/start",  # ✅ CHANGED
    "input_schema": {
        "message": "str",
        "conversation_id": "str"  # Optional
    },
    "headers": {
        "clientId": "1B3C139A-562B-4AD4-B107-8096115F5E9F",  # ✅ REQUIRED
        "projectId": "5CC5E342-4EAD-49D5-A595-963719A0EEC9",  # ✅ REQUIRED
        "Module": "P2P",  # Optional
        "Submodule": "Payments",  # Optional
        "Content-Type": "application/json"  # ✅ REQUIRED
        # "shareData": "true"  # ❌ REMOVE - not used
    }
}
```

### In `orchestrator.py`:

The orchestrator should already be sending headers correctly. Verify:

1. **Headers are passed to HTTP request:**
   ```python
   headers = agent_cfg.get("headers") if agent_cfg and agent_cfg["name"] == "SQLAgent" else None
   ```

2. **Body format is correct:**
   ```python
   if agent_cfg and agent_cfg["name"] == "SQLAgent":
       if "message" not in input_json and "query" in input_json:
           input_json = {"message": input_json["query"]}
       if conversation_id and "conversation_id" not in input_json:
           input_json["conversation_id"] = conversation_id
   ```

3. **Request is sent with headers:**
   ```python
   tasks.append(async_post(endpoint, input_json, headers=headers))
   ```

## Conversation ID Handling

The SQL agent supports conversation continuity:

1. **First message (new conversation):**
   - Don't send `conversation_id` in body
   - SQL agent creates a new conversation automatically
   - Response includes `conversation_id` for future messages

2. **Follow-up messages (same conversation):**
   - Include `conversation_id` from previous response in the request body
   - SQL agent continues the same conversation thread

**Example flow:**
```python
# First call
response1 = call_sql_agent(message="who are top risk vendors")
conversation_id = response1["conversation_id"]

# Second call (continuing conversation)
response2 = call_sql_agent(
    message="show me details of the first one",
    conversation_id=conversation_id
)
```

## Testing Checklist

Before deploying, verify:

- [ ] Endpoint URL is `/api/interactions/start` (not `/api/chat/sqlagent`)
- [ ] `clientId` header is sent
- [ ] `projectId` header is sent
- [ ] `Content-Type: application/json` header is sent
- [ ] Request body contains `message` field
- [ ] Request body uses `message` (not `query`)
- [ ] Chatbot is registered via `/api/chatbots/{chatbot_id}/register` endpoint
- [ ] Response parsing handles all three response types (response, clarification, approval)
- [ ] Conversation ID is extracted and used for follow-up messages

## Summary of Changes

| Item | Current | Required | Action |
|------|---------|----------|--------|
| Endpoint | `/api/chat/sqlagent` | `/api/interactions/start` | ✅ Change endpoint |
| Headers | All present | All present | ✅ Keep as-is |
| Body field | `message` | `message` | ✅ Already correct |
| `shareData` header | Present | Not used | ⚠️ Can remove (optional) |
| `Content-Type` header | ? | `application/json` | ✅ Ensure present |
| Chatbot registration | ? | Required | ✅ Must register once |

## Contact

If you have questions about this integration, please contact the SQL Agent team.




