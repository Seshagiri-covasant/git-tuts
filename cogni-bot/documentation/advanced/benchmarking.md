# Benchmarking & Test Suite

## Built-in benchmark
- Create baseline conversation `Test Suite` automatically on ready
- Endpoints provide status, details, and performance metrics

### Run
- `POST /api/chatbots/{id}/benchmark` (optional `temperature`)
- Poll `GET /api/chatbots/{id}/benchmark`
- Details: `GET /api/chatbots/{id}/benchmark/details`
- Metrics: `GET /api/chatbots/{id}/performance`

## Custom tests
- Create: `POST /api/chatbots/{id}/custom-tests` with original_sql + natural_question
- List: `GET /api/chatbots/{id}/custom-tests`
- Suites: `GET /api/chatbots/{id}/custom-tests/suites`
- Run: `POST /api/chatbots/{id}/custom-tests/run` (filter by test_name)
- Metrics: `GET /api/chatbots/{id}/custom-tests/metrics`
- Delete: `DELETE /api/custom-tests/{test_id}`

## Scoring
- Efficiency = correct / total based on generated SQL matches; persisted to chatbot efficiency
