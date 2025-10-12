# Agents & Workflow

## Overview
`AgentManager` orchestrates a LangGraph pipeline with status updates and checkpointing (SQLite per chatbot under `backend/instance/checkpoints`).

## Nodes
1. Domain_Relevance_Checker → rejects out-of-domain questions
2. Intent_Picker → selects tables/columns, builds minimal intent JSON using knowledge cache
3. Query_Clarification → requests clarification if needed
4. Context_Clipper → narrows schema to relevant subset
5. Query_Generator → prompts LLM with template + DB-specific instructions to generate SQL
6. Query_Cleaner → sanitize/normalize SQL
7. Query_Validator → EXPLAIN validation (Postgres/SQLite), LLM-guided fixes when possible
8. Query_Executor → execute SQL via SQLAlchemy, return JSON data
9. Answer_Rephraser → final natural language response

## Status API
- `GET /api/conversations/{id}/status` fetches `AgentManager.get_processing_status()` showing step and progress.

## Templates
- Enhanced prompt is stored per chatbot in `chatbot_prompts` and injected into Query Generator.

## LLMs
- Selected per chatbot; see `app/agents/llm_factory.py`.
