# User Guide

This guide walks end users through using CogniBot end-to-end: from creating a bot to analyzing data, rating answers, and exporting insights.

> For installation, see [Getting Started](getting-started.md). For API details, see [API Reference](reference/api.md). For the agent workflow, see [Agents & Workflow](guides/agents.md).

## 1. What is CogniBot?
CogniBot converts natural language into SQL to answer questions over your databases. It uses a semantic schema and a multi-step agent workflow to generate, validate, and execute safe queries, then explains the results in plain language. See the deep-dive on [Semantic Model & Knowledge Flow](advanced/semantic-deep-dive.md).

## 2. Prerequisites
- A running CogniBot (see [Getting Started](getting-started.md))
- Access to a database (PostgreSQL/SQLite/BigQuery)
- An LLM API key if not using the default provider

## 3. Frontend flow (simple UI walkthrough)
The web app in `frontend/` exposes a streamlined path. The following screens map to backend operations:

1) Chatbots page
- Create Chatbot → calls `POST /api/chatbots`
- Table lists name, LLM, temperature, status; clicking a row opens details

2) Configure database (wizard or panel)
- Choose DB type and fill fields → calls `POST /api/chatbots/{id}/database`
- After success, schema extraction and knowledge cache build run on the server

3) Configure LLM
- Pick provider and temperature → calls `POST /api/chatbots/{id}/llm`

4) Ready
- Click "Mark Ready" → calls `POST /api/chatbots/{id}/ready`
- Backend generates enhanced prompt and warms the agent cache

5) Conversations
- "New Conversation" → calls `POST /api/chatbots/{id}/conversations`
- Send messages in the chat input → calls `POST /api/conversations/{conversationId}/interactions`
- The right rail can show cleaned SQL and optional raw result data
- A status indicator can poll `GET /api/conversations/{conversationId}/status`

6) History and limits
- The conversation pane paginates using `GET /api/conversations/{conversationId}/interactions?limit=&offset=`
- The UI displays remaining messages based on the `limit_status` payload

7) Rating and details
- Thumbs up/down on each response → `POST /api/conversations/{cid}/interactions/{iid}/rating`
- "View SQL" → `GET /api/conversations/{cid}/interactions/{iid}`

8) Insights and Visualization
- BA Insights panel → `POST /api/ba-insights` (see [tutorial](tutorials/ba-insights.md))
- Visualization builder → `POST /api/visualize` (see [tutorial](tutorials/visualization.md))

## 4. Backend flow (API)
For direct API usage and examples, see [API Reference](reference/api.md) and the tutorials: [Create a Bot](tutorials/create-bot.md), [Run a Conversation](tutorials/run-conversation.md).

## 5. Track progress
Use the status endpoint to see where the agent is in the pipeline:
```http
GET /api/conversations/{conversationId}/status
```
You’ll see the current step (e.g., generating, validating, executing) and progress.

## 6. Review history and limits
List messages with pagination and limit status:
```http
GET /api/conversations/{conversationId}/interactions?limit=5&offset=0
```
CogniBot enforces a per-conversation cap (default 10). The response includes remaining allowance and a warning when close to limits.

## 7. View the SQL behind answers
For any interaction:
```http
GET /api/conversations/{conversationId}/interactions/{interactionId}
```
Returns the cleaned SQL used to produce the answer.

## 8. Rate answers
```http
POST /api/conversations/{conversationId}/interactions/{interactionId}/rating
{ "rating": 1 }
```
Retrieve ratings with a GET on the same path.

## 9. Troubleshooting
- Health: `GET /api/health`
- Reset agent cache: `POST /api/clear-agents`
- Clear a chatbot’s prompt: `POST /api/chatbots/{id}/clear-prompt`
- Logs: `backend/logs/app.log`

## 10. Best practices
- Ask focused questions with time ranges, measures, and dimensions
- Prefer consistent naming (match table/column names or configured synonyms)

## 11. Deleting data
- Delete conversations: `DELETE /api/conversations/{conversationId}`
- Delete a chatbot (removes related data): `DELETE /api/chatbots/{chatbot_id}`
