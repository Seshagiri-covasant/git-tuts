# CogniBot Documentation

Welcome to CogniBot — a natural language to SQL analytics assistant with conversation memory, semantic schema, multi-LLM support, and benchmarking.

## What you’ll find here
- Overview of features and architecture
- Installation and quickstart
- Guides for configuration, deployment, semantic schema, agents, and knowledge cache
- Tutorials for creating a bot, running conversations, BA insights, and visualization
- API reference, data models, and environment variables
- Advanced topics: benchmarking, scaling, security, observability

## Repository layout
- Backend Flask app under `cogni-bot/backend`
- Frontend Vite+React app under `cogni-bot/frontend`
- Config in `cogni-bot/backend/config.py`, `requirements.txt`

## Quick links
- Getting started: getting-started.md
- User guide: user-guide.md
- Semantic deep-dive: advanced/semantic-deep-dive.md
- API reference: reference/api.md
- Architecture: guides/agents.md

## Support
If you run into issues, check logs under `cogni-bot/backend/logs/app.log` and health endpoint `/api/health`.
