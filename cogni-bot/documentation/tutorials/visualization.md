# Tutorial: Build a Visualization

1. Provide table, prompt, SQL query, and chatbot id.
```json
{
  "table": [{"name": "orders"}],
  "prompt": "Daily revenue last 30 days",
  "sql_query": "SELECT date, SUM(amount) as revenue FROM orders GROUP BY date",
  "chatbot_id": "<id>"
}
```
2. Call
```bash
POST /api/visualize
```
3. Response
```json
{ "chart_config": { "type": "line", "x": "date", "y": "revenue", ... } }
```
Render with your preferred chart lib.
