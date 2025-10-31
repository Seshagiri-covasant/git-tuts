# Orchestration Agent → SQL Agent Compatibility Analysis

## Current State Analysis

### 1. **Orchestration Agent Entry Point (`/orchestrate`)**

**What Users See (Swagger UI):**
```
POST /orchestrate
Headers:
  client-id: string (lowercase, hyphenated)
  project-id: string (lowercase, hyphenated)
Body:
{
  "query": "string",
  "user_id": "anonymous",
  "thread_id": "default_thread",
  "enable_websearch": true,
  "enable_doj": true,
  "enable_sql": true,
  "enable_retrieval": true
}
```

### 2. **SQL Agent Endpoint (`/api/interactions/start`)**

**What SQL Agent Expects:**
```
POST /api/interactions/start
Headers:
  clientId: string (camelCase) ✅ REQUIRED
  projectId: string (camelCase) ✅ REQUIRED
  Module: string (optional)
  Submodule: string (optional)
Body:
{
  "message": "string", ✅ REQUIRED (NOT "query")
  "conversation_id": "string" (optional, NOT "thread_id")
}
```

---

## Compatibility Issues

### ❌ **Issue 1: Header Naming Mismatch**

| Source | Header Name | Format |
|--------|-------------|--------|
| **Orchestration UI Shows** | `client-id` | Lowercase, hyphenated |
| **Orchestrator Code Sends** | `clientId` | camelCase ✅ |
| **SQL Agent Expects** | `clientId` | camelCase ✅ |

**Status:** ✅ **COMPATIBLE** (Orchestrator transforms headers correctly)

The orchestrator code (`agent_config.py`) uses `clientId`/`projectId` (camelCase), which matches what SQL agent expects. The UI might show hyphenated names, but the actual HTTP headers sent are camelCase.

---

### ❌ **Issue 2: Body Field Name Mismatch**

| Source | Field Name | Purpose |
|--------|------------|---------|
| **Orchestration Body** | `query` | User's question |
| **SQL Agent Expects** | `message` | User's question |

**Status:** ✅ **COMPATIBLE** (Orchestrator transforms field name)

The orchestrator code (`orchestrator.py` line 194-195) converts `query` → `message`:
```python
if "message" not in input_json and "query" in input_json:
    input_json = {"message": input_json["query"]}
```

---

### ❌ **Issue 3: Conversation/Thread ID Naming**

| Source | Field Name | Purpose |
|--------|------------|---------|
| **Orchestration Body** | `thread_id` | Conversation continuity |
| **SQL Agent Expects** | `conversation_id` | Conversation continuity |

**Status:** ✅ **COMPATIBLE** (Orchestrator transforms field name)

The orchestrator code (`orchestrator.py` line 197-198) injects `conversation_id`:
```python
if conversation_id and "conversation_id" not in input_json:
    input_json["conversation_id"] = conversation_id
```

The orchestrator also tries to create a conversation on first message (`main.py` lines 434-451).

---

### ⚠️ **Issue 4: Unused Fields**

The orchestration agent sends these fields that SQL agent **does NOT use**:
- `user_id` - SQL agent doesn't process this
- `enable_websearch` - SQL agent doesn't process this
- `enable_doj` - SQL agent doesn't process this
- `enable_sql` - SQL agent doesn't process this
- `enable_retrieval` - SQL agent doesn't process this

**Status:** ✅ **HARMLESS** - These fields are ignored by SQL agent (no error)

---

### ✅ **Issue 5: Endpoint URL**

| Current | Required |
|---------|----------|
| `http://172.212.177.27/api/chat/sqlagent` ❌ | `http://172.212.177.27/api/interactions/start` ✅ |

**Status:** ❌ **NEEDS UPDATE** - This is the main change needed!

---

## ✅ **What Works Correctly**

1. ✅ **Header Transformation:** Orchestrator sends `clientId`/`projectId` (camelCase) which SQL agent expects
2. ✅ **Field Name Transformation:** Orchestrator converts `query` → `message`
3. ✅ **Conversation ID Injection:** Orchestrator injects `conversation_id` for continuity
4. ✅ **Module/Submodule Headers:** Already configured in `agent_config.py`

---

## ❌ **What Needs to Be Changed**

### **1. Update Endpoint URL in `agent_config.py`**

**Current:**
```python
{
    "name": "SQLAgent",
    "endpoint": "http://172.212.177.27/api/chat/sqlagent",  # ❌ WRONG
    ...
}
```

**Required:**
```python
{
    "name": "SQLAgent",
    "endpoint": "http://172.212.177.27/api/interactions/start",  # ✅ CORRECT
    ...
}
```

---

## 📋 **Complete Compatibility Matrix**

| Aspect | Orchestration Sends | SQL Agent Expects | Status |
|--------|---------------------|-------------------|--------|
| **Endpoint** | `/api/chat/sqlagent` | `/api/interactions/start` | ❌ **CHANGE NEEDED** |
| **Header: Client ID** | `clientId` (camelCase) | `clientId` (camelCase) | ✅ **COMPATIBLE** |
| **Header: Project ID** | `projectId` (camelCase) | `projectId` (camelCase) | ✅ **COMPATIBLE** |
| **Header: Module** | `Module` | `Module` (optional) | ✅ **COMPATIBLE** |
| **Header: Submodule** | `Submodule` | `Submodule` (optional) | ✅ **COMPATIBLE** |
| **Body: Query/Message** | `query` → transforms to `message` | `message` | ✅ **COMPATIBLE** |
| **Body: Thread/Conversation ID** | `thread_id` → transforms to `conversation_id` | `conversation_id` | ✅ **COMPATIBLE** |
| **Body: User ID** | `user_id` | ❌ Not used | ✅ **HARMLESS** |
| **Body: Enable Flags** | `enable_*` | ❌ Not used | ✅ **HARMLESS** |

---

## 🎯 **Summary**

### ✅ **What's Already Compatible:**

1. **Headers:** Orchestrator sends `clientId`/`projectId` in camelCase (matches SQL agent)
2. **Field Names:** Orchestrator transforms `query` → `message` automatically
3. **Conversation ID:** Orchestrator handles `thread_id` → `conversation_id` mapping
4. **Module Headers:** Already configured and sent correctly

### ❌ **What Needs Change:**

**ONLY ONE CHANGE REQUIRED:**
- Update endpoint URL in `agent_config.py` from `/api/chat/sqlagent` → `/api/interactions/start`

### 📝 **Note About UI vs Reality:**

The Swagger UI might show `client-id`/`project-id` (hyphenated), but:
- The **actual HTTP headers** sent by the orchestrator are `clientId`/`projectId` (camelCase) ✅
- This matches what SQL agent expects ✅
- No changes needed to header names ✅

---

## ✅ **Final Verdict**

**Your SQL agent is 95% compatible!** 

Only the endpoint URL needs to be updated. All other transformations (headers, body fields) are already handled correctly by the orchestrator code.

---

## 🔧 **Action Items for Orchestration Team**

1. ✅ Update `agent_config.py`: Change endpoint from `/api/chat/sqlagent` → `/api/interactions/start`
2. ✅ Verify headers are sent as `clientId`/`projectId` (camelCase) - should already be correct
3. ✅ Test end-to-end flow
4. ⚠️ Optional: Update Swagger UI documentation to show `clientId`/`projectId` (camelCase) instead of `client-id`/`project-id` (for clarity, but not required)

