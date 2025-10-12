# Tutorial: Generate BA Insights

BA insights summarize result sets in business language.

1. Get your chatbot id and ensure it’s ready.
2. Prepare the table descriptor array and prompt:
```json
{
  "table": [{"name": "orders"}],
  "prompt": "Summarize revenue trends",
  "chatbot_id": "<id>"
}
```
3. Call
```bash
POST /api/ba-insights
```
4. Response
```json
{ "summary": "Revenue increased 12% MoM..." }
```
Uses the current chatbot LLM and temperature.
