# Conversation Storage Monitoring Guide

This guide helps you monitor and verify that conversations are being stored properly in your NL2SQL application.

## 🔍 Quick Check

To quickly check if conversations are being stored, run:

```bash
python monitor_conversations.py
```

This will run all monitoring tools and show you the status of conversation storage.

## 📊 Available Monitoring Tools

### 1. **Storage Status Check**
```bash
python check_conversation_storage.py
```
- ✅ Checks database connection
- ✅ Verifies conversation tables exist
- ✅ Shows existing conversation data
- ✅ Tests conversation creation
- ✅ Monitors application logs

### 2. **Log Analysis**
```bash
python view_conversation_logs.py
```
- 📄 Analyzes all log files for conversation activity
- 🔍 Shows recent conversation-related entries
- 🚨 Identifies any errors
- 📊 Provides activity summary

### 3. **Storage Test**
```bash
python test_conversation_storage.py
```
- 🧪 Creates test conversations and interactions
- ✅ Verifies data is stored in database
- 🧹 Cleans up test data
- 📊 Reports test results

### 4. **Real-time Monitoring**
```bash
python check_conversation_storage.py --real-time
```
- 🔄 Monitors for new conversations every 10 seconds
- 📈 Shows real-time activity
- 🛑 Press Ctrl+C to stop

## 🗄️ Database Storage Structure

Your conversations are stored in **PostgreSQL** using these tables:

### `conversations` Table
```sql
conversation_id    VARCHAR(36) PRIMARY KEY
chatbot_id         VARCHAR(36) NOT NULL
conversation_name  VARCHAR(255)
conversation_type  VARCHAR(50)
template_id        INTEGER
start_time         TIMESTAMP
end_time           TIMESTAMP
status             VARCHAR(50)
owner              VARCHAR(100)
```

### `interactions` Table
```sql
interaction_id     VARCHAR(36) PRIMARY KEY
conversation_id    VARCHAR(36) REFERENCES conversations(conversation_id)
request            VARCHAR(2000)    -- User's question
final_result       TEXT            -- AI's response
cleaned_query      VARCHAR(2000)    -- Generated SQL
start_time         TIMESTAMP
end_time           TIMESTAMP
is_system_message  BOOLEAN
rating             INTEGER          -- User feedback
ba_summary         TEXT            -- Business analytics
```

## 📝 Log Files to Check

Monitor these log files for conversation activity:

- `logs/app.log` - Main application logs
- `conversation_storage.log` - Storage-specific logs
- `conversation_test.log` - Test execution logs
- `schema_test.log` - Schema-related logs

## 🔧 Troubleshooting

### No Conversations Found
1. **Check if application is running**
2. **Verify database connection**
3. **Check if tables exist**
4. **Look for errors in logs**

### Database Connection Issues
1. **Check environment variables:**
   - `DB_USER`
   - `DB_PASSWORD` 
   - `DB_HOST`
   - `DB_PORT`
   - `DB_NAME`

2. **Verify PostgreSQL is running**
3. **Check network connectivity**

### Storage Not Working
1. **Run the test script:**
   ```bash
   python test_conversation_storage.py
   ```

2. **Check for errors in logs:**
   ```bash
   python view_conversation_logs.py
   ```

3. **Verify database permissions**

## 📊 Monitoring Commands

### Quick Status Check
```bash
python monitor_conversations.py --check
```

### View Recent Activity
```bash
python monitor_conversations.py --logs
```

### Test Storage
```bash
python monitor_conversations.py --test
```

### Real-time Monitoring
```bash
python monitor_conversations.py --real-time
```

## 🎯 What to Look For

### ✅ Healthy Storage Indicators
- Database connection successful
- Tables exist and accessible
- Recent conversations in database
- No errors in logs
- Test conversations created successfully

### ❌ Problem Indicators
- Database connection failed
- Tables missing
- No recent activity
- Errors in logs
- Test conversations failed

## 📈 Monitoring Dashboard

Run this to get a complete overview:

```bash
python monitor_conversations.py --all
```

This will show:
- 📊 Database status
- 💬 Recent conversations
- 💭 Recent interactions  
- 📄 Log analysis
- 🧪 Test results
- 🚨 Any errors

## 🔄 Continuous Monitoring

For production environments, set up continuous monitoring:

```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/backend && python check_conversation_storage.py --check-only
```

## 📞 Support

If you're still having issues:

1. **Check the logs** for specific error messages
2. **Verify database connectivity**
3. **Ensure application is running**
4. **Test with the provided scripts**

The monitoring tools will help you identify exactly where the conversation storage might be failing! 🎯


