# API Reference

Base URL: `/api`

## Health
- GET `/health`

## Chatbots
- GET `/chatbots`
- POST `/chatbots` { name, temperature? }
- GET `/chatbots/{chatbot_id}`
- DELETE `/chatbots/{chatbot_id}`
- POST `/chatbots/{chatbot_id}/database`
- POST `/chatbots/{chatbot_id}/llm`
- PUT `/chatbots/{chatbot_id}/llm`
- POST `/chatbots/{chatbot_id}/ready`
- POST `/chatbots/{chatbot_id}/restart`
- POST `/chatbots/{chatbot_id}/database/update-schema`
- GET `/chatbots/{chatbot_id}/semantic-schema`
- PUT `/chatbots/{chatbot_id}/semantic-schema`
- POST `/chatbots/{chatbot_id}/knowledge-base`

## Conversations
- POST `/chatbots/{chatbot_id}/conversations`
- GET `/chatbots/{chatbot_id}/conversations`
- GET `/conversations/{conversation_id}`
- DELETE `/conversations/{conversation_id}`
- POST `/conversations/{conversation_id}/interactions`
- GET `/conversations/{conversation_id}/interactions`
- GET `/conversations/{conversation_id}/interactions/{interaction_id}` (cleaned query)
- POST `/conversations/{conversation_id}/interactions/{interaction_id}/rating`
- GET `/conversations/{conversation_id}/interactions/{interaction_id}/rating`
- GET `/conversations/{conversation_id}/status`
- GET `/conversations/{conversation_id}/interaction-count`

## Templates
- POST `/chatbots/{chatbot_id}/template`
- PUT `/chatbots/{chatbot_id}/template`
- GET `/chatbots/{chatbot_id}/template`
- GET `/templates`
- POST `/templates`
- GET `/templates/{template_id}`
- PUT `/templates/{template_id}`
- DELETE `/templates/{template_id}`
- POST `/templates/{template_id}/preview`

## Benchmarking / Tests
- POST `/chatbots/{chatbot_id}/benchmark`
- GET `/chatbots/{chatbot_id}/benchmark`
- GET `/chatbots/{chatbot_id}/benchmark/details`
- GET `/chatbots/{chatbot_id}/performance`
- POST `/chatbots/{chatbot_id}/benchmark/cleanup`
- POST `/chatbots/{chatbot_id}/custom-tests`
- GET `/chatbots/{chatbot_id}/custom-tests`
- GET `/chatbots/{chatbot_id}/custom-tests/suites`
- POST `/chatbots/{chatbot_id}/custom-tests/run`
- GET `/chatbots/{chatbot_id}/custom-tests/metrics`
- DELETE `/custom-tests/{test_id}`

## System
- POST `/clear-agents`
- POST `/chatbots/{chatbot_id}/clear-prompt`
- POST `/test-connection`
