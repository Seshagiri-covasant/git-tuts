# Observability & Logging (Implemented Behavior)

## Logging
- Logging is initialized in `app/factory.py` via `setup_logging()` from `app/utils/monitoring.py`.
- Database operations in some services are wrapped by `monitored_database_operation` to record timings.

## Health/status endpoints
- `GET /api/health` and `GET /api/system/status` return health/system information assembled by `system_service`.
- `GET /api/conversations/{id}/status` returns the current processing status from `AgentManager` (step, progress, message).

## Benchmark metrics endpoints
- `/api/chatbots/{id}/benchmark` (POST/GET)
- `/api/chatbots/{id}/benchmark/details`
- `/api/chatbots/{id}/performance`
- `/api/chatbots/{id}/custom-tests` and related metrics endpoints

These are the observability capabilities present in the codebase.
