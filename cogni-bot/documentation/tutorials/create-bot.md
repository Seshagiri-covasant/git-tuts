# Tutorial: Create Your First Chatbot

## 1) Create a chatbot
```bash
POST /api/chatbots
{ "name": "SalesBot", "temperature": 0.4 }
```

## 2) Configure database
- PostgreSQL example:
```json
{
  "db_type": "postgresql",
  "db_name": "sales",
  "username": "app",
  "password": "secret",
  "host": "db.local",
  "port": 5432
}
```
- SQLite example:
```json
{ "db_type": "sqlite", "db_name": "sample" }
```
- BigQuery example:
```json
{ "db_type": "bigquery", "project_id": "acme", "dataset_id": "analytics", "credentials_json": "{...}" }
```

## 3) Configure LLM
```bash
POST /api/chatbots/{id}/llm
{ "llm_name": "COHERE", "temperature": 0.4 }
```

## 4) Mark ready
```bash
POST /api/chatbots/{id}/ready
```

## 5) Create a conversation
```bash
POST /api/chatbots/{id}/conversations
{ "conversation_name": "Q1 Pipeline", "owner": "analyst" }
```

## 6) Ask a question
```bash
POST /api/conversations/{conversationId}/interactions
{ "request": "Show top 10 customers by revenue in Q1" }
```
Response includes `final_result`, `cleaned_query`, and optional `raw_result_set`, `ba_summary`.
