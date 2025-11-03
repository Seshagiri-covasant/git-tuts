# Register Endpoint Usage Guide

## Overview
The register endpoint maps external `clientId`/`projectId` (from orchestrator) to your internal `chatbot_id`.

## Endpoints

### Localhost
```
POST http://127.0.0.1:5000/api/chatbots/{chatbot_id}/register
```

### Production (Deployed)
```
POST https://your-deployed-domain.com/api/chatbots/{chatbot_id}/register
```

## Request Format

**Method:** `POST`  
**URL:** `/api/chatbots/{chatbot_id}/register`  
**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
  "clientId": "1B3C139A-562B-4AD4-B107-8096115F5E9F",
  "projectId": "5CC5E342-4EAD-49D5-A595-963719A0EEC9"
}
```

**URL Parameter:**
- `chatbot_id`: Your internal chatbot UUID (e.g., `7fdeda20-9621-4130-b7c9-106cedf0f12f`)

## Response

**Success (200):**
```json
{
  "message": "Chatbot registered successfully",
  "chatbot_id": "7fdeda20-9621-4130-b7c9-106cedf0f12f",
  "clientId": "1B3C139A-562B-4AD4-B107-8096115F5E9F",
  "projectId": "5CC5E342-4EAD-49D5-A595-963719A0EEC9",
  "message": "External IDs registered successfully"
}
```

**Error (400):**
```json
{
  "error": "Invalid request body: {'clientId': ['Missing data for required field.'], 'projectId': ['Missing data for required field.']}"
}
```

**Error (404):**
```json
{
  "error": "Chatbot not found"
}
```

## Usage Examples

### Postman (Localhost)
1. Method: `POST`
2. URL: `http://127.0.0.1:5000/api/chatbots/YOUR_CHATBOT_ID/register`
3. Headers: `Content-Type: application/json`
4. Body: 
   ```json
   {
     "clientId": "YOUR_CLIENT_ID",
     "projectId": "YOUR_PROJECT_ID"
   }
   ```

### cURL (Localhost)
```bash
curl -X POST http://127.0.0.1:5000/api/chatbots/YOUR_CHATBOT_ID/register \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "YOUR_CLIENT_ID",
    "projectId": "YOUR_PROJECT_ID"
  }'
```

### cURL (Production)
```bash
curl -X POST https://your-deployed-domain.com/api/chatbots/YOUR_CHATBOT_ID/register \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "YOUR_CLIENT_ID",
    "projectId": "YOUR_PROJECT_ID"
  }'
```

### Python Script (Production)
```python
import requests

url = "https://your-deployed-domain.com/api/chatbots/YOUR_CHATBOT_ID/register"
headers = {"Content-Type": "application/json"}
payload = {
    "clientId": "YOUR_CLIENT_ID",
    "projectId": "YOUR_PROJECT_ID"
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

## After Registration

Once registered, the orchestrator can call your unified interaction endpoint:

```
POST https://your-deployed-domain.com/api/interactions/start
Headers:
  clientId: YOUR_CLIENT_ID
  projectId: YOUR_PROJECT_ID
  Module: P2P
  Submodule: Payments
Body:
{
  "message": "who are top risk vendors"
}
```

The system will automatically map `clientId`/`projectId` → `chatbot_id` using the registered mapping.

## Security Considerations

**⚠️ Currently, the register endpoint has NO authentication. In production, you should:**

1. **Add API Key Authentication:**
   - Require an API key in headers: `X-API-Key: your-secret-key`
   - Validate the key before allowing registration

2. **Add Role-Based Access:**
   - Only allow admins/service accounts to register chatbots
   - Use JWT tokens or similar authentication

3. **Network Security:**
   - Restrict access via firewall/VPN
   - Use HTTPS only in production
   - Consider IP whitelisting

4. **Rate Limiting:**
   - Prevent abuse with rate limiting
   - Monitor for suspicious registration attempts

## Bulk Registration Script

For multiple chatbots, you can use this Python script:

```python
import requests

BASE_URL = "https://your-deployed-domain.com/api"
API_KEY = "your-api-key"  # If authentication is added

chatbots = [
    {
        "chatbot_id": "chatbot-uuid-1",
        "clientId": "client-id-1",
        "projectId": "project-id-1"
    },
    {
        "chatbot_id": "chatbot-uuid-2",
        "clientId": "client-id-2",
        "projectId": "project-id-2"
    }
]

for cb in chatbots:
    url = f"{BASE_URL}/chatbots/{cb['chatbot_id']}/register"
    payload = {
        "clientId": cb["clientId"],
        "projectId": cb["projectId"]
    }
    headers = {
        "Content-Type": "application/json",
        # "X-API-Key": API_KEY  # Uncomment when auth is added
    }
    
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        print(f"✅ Registered {cb['chatbot_id']}")
    else:
        print(f"❌ Failed: {cb['chatbot_id']} - {response.json()}")
```

## Troubleshooting

**Error: "Chatbot not found"**
- Verify the `chatbot_id` exists in your database
- Check the chatbot was created successfully

**Error: "Invalid request body"**
- Ensure `clientId` and `projectId` are both provided
- Check JSON format is valid

**Error: "Failed to update chatbot"**
- Check database connection
- Verify chatbot table structure has `client_id` and `project_id` columns



