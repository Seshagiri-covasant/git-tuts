# Tutorial: Run a Conversation

1. Confirm status
```bash
GET /api/chatbots/{id}
```
Ensure `status: "ready"`.

2. Create conversation (if not done)
```bash
POST /api/chatbots/{id}/conversations
{ "conversation_name": "Exploration", "owner": "user" }
```

3. Send messages
```bash
POST /api/conversations/{conversationId}/interactions
{ "request": "Total orders last 30 days by status" }
```

4. Track progress
```bash
GET /api/conversations/{conversationId}/status
```
Returns `current_step`, `progress`, and message.

5. Paginate history
```bash
GET /api/conversations/{conversationId}/interactions?limit=5&offset=0
```
Includes `limit_status` with remaining interactions before the cap.
