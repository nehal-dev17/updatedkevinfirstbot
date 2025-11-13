# AI Wellness Companion API - Production Setup

A production-ready FastAPI backend for an AI-powered wellness companion using Google Gemini and AWS DynamoDB.

## 📁 Project Structure

```
backend/
├── routes/
│   ├── __init__.py
│   ├── user.py          # Profile endpoints
│   └── chat.py          # Chat & history endpoints
├── services/
│   ├── __init__.py
│   └── ai_service.py    # Gemini AI integration
├── main.py              # FastAPI application
├── models.py            # Pydantic models
├── database.py          # DynamoDB connection & setup
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
└── .env.example         # Environment template
```

## 🚀 Setup Instructions

### 1. Prerequisites
- Python 3.8+
- AWS Account with DynamoDB access
- Google AI API Key (Gemini)

### 2. Installation

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the backend directory:

```bash
# Copy example file
cp .env.example .env
```

Fill in your credentials in `.env`:

```env
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1

DDB_TABLE_CONVERSATIONS=wellness_conversations
DDB_TABLE_PROFILES=wellness_profiles

GOOGLE_GENAI_API_KEY=your_gemini_api_key_here

ENVIRONMENT=production
PORT=8000
CORS_ORIGINS=*
```

### 4. DynamoDB Tables

The application will automatically create these tables on startup:

**wellness_conversations**
- Partition Key: `user_id` (Number)
- Sort Key: `timestamp` (String)
- Billing Mode: PAY_PER_REQUEST

**wellness_profiles**
- Partition Key: `user_id` (Number)
- Billing Mode: PAY_PER_REQUEST

> **Note:** Tables will be created automatically. No manual setup needed!

### 5. Run the Application

```bash
# Development mode (with auto-reload)
ENVIRONMENT=development uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### Health Check
- `GET /` - Basic health check
- `GET /health` - Detailed health status

### User Profile
- `GET /api/v1/profile/{user_id}` - Get user profile
- `PUT /api/v1/profile/{user_id}` - Create/update profile
- `DELETE /api/v1/profile/{user_id}` - Delete profile

### Chat & History
- `POST /api/v1/chat/{user_id}` - Send message and get AI response
- `GET /api/v1/history/{user_id}?limit=50` - Get conversation history
- `DELETE /api/v1/history/{user_id}` - Clear conversation history and save summary

## 🆕 New Features

### 1. Integer User IDs
All endpoints now use integer `user_id` instead of strings:
```bash
# OLD: /api/v1/chat with body {"user_id": "123", "message": "..."}
# NEW: /api/v1/chat/123 with body {"message": "..."}
```

### 2. Conversation Summaries
When you delete conversation history, the system:
- ✅ Generates an AI-powered summary of the conversation
- ✅ Extracts key topics and sentiment
- ✅ Stores the summary in the user profile
- ✅ Uses summaries in future conversations for context
- ✅ Returns the summary in the delete response

**Summary includes:**
- Brief overview of the conversation
- Key wellness topics discussed
- Emotional sentiment (positive/neutral/concerned)
- Insights about user's wellness journey
- Message count and date range

### 3. Context-Aware Responses
The bot now considers:
- Current conversation
- User profile preferences
- **Past conversation summaries** (up to 3 most recent)

This means the bot remembers previous discussions even after history is cleared!

## 📝 API Documentation

Once running, access interactive API docs at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔧 Example Usage

### Create/Update Profile
```bash
curl -X PUT "http://localhost:8000/api/v1/profile/123" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 30,
    "background": "Software Engineer",
    "preferences": {"meditation": true, "exercise": true}
  }'
```

### Send Chat Message (Updated)
```bash
curl -X POST "http://localhost:8000/api/v1/chat/123" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am feeling stressed lately. Can you help?"
  }'
```

### Get Conversation History
```bash
curl "http://localhost:8000/api/v1/history/123?limit=10"
```

### Clear History (with Summary)
```bash
curl -X DELETE "http://localhost:8000/api/v1/history/123"
```

**Response includes:**
```json
{
  "status": "success",
  "message": "Cleared 20 messages and saved conversation summary",
  "user_id": 123,
  "deleted_count": 20,
  "summary": {
    "summary": "User discussed stress management and sleep issues...",
    "key_topics": ["stress", "sleep", "meditation"],
    "sentiment": "concerned",
    "message_count": 20,
    "created_at": "2024-01-15T10:30:00.000000"
  }
}
```

## 🔐 Security Considerations

### For Production Deployment:

1. **Environment Variables**: Never commit `.env` file
2. **CORS**: Update `CORS_ORIGINS` to specific domains
3. **AWS Credentials**: Use IAM roles instead of access keys when possible
4. **API Keys**: Rotate keys regularly
5. **HTTPS**: Always use HTTPS in production
6. **Rate Limiting**: Add rate limiting middleware
7. **Authentication**: Implement user authentication/authorization

## 📊 Database Schema

### Conversations Table
```json
{
  "user_id": 123,
  "timestamp": "2024-01-15T10:30:00.000000#user#uuid",
  "role": "user",
  "content": "I'm feeling stressed",
  "keywords": ["stress"]
}
```

### Profiles Table
```json
{
  "user_id": 123,
  "age": 30,
  "background": "Software Engineer",
  "preferences": {"meditation": true},
  "history": [
    {
      "timestamp": "2024-01-15T10:30:00.000000",
      "keywords": ["stress"],
      "snippet": "I'm feeling stressed lately..."
    }
  ],
  "summaries": [
    {
      "summary": "Previous conversation about stress management",
      "key_topics": ["stress", "meditation", "sleep"],
      "sentiment": "concerned",
      "insights": "User showed interest in meditation techniques",
      "message_count": 15,
      "created_at": "2024-01-14T20:00:00.000000",
      "date_range": {
        "start": "2024-01-14T10:00:00.000000",
        "end": "2024-01-14T20:00:00.000000"
      }
    }
  ],
  "created_at": "2024-01-15T10:00:00.000000",
  "updated_at": "2024-01-15T10:30:00.000000"
}
```

## 🐛 Troubleshooting

### AWS Credentials Error
```
RuntimeError: AWS credentials not found
```
**Solution**: Ensure `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set in `.env`

### Table Creation Timeout
```
Failed to create table
```
**Solution**: Check AWS permissions. Ensure your IAM user has DynamoDB create/describe permissions.

### User ID Type Error
If you get errors about user_id type, ensure:
- You're using integer user IDs (123, not "123")
- For existing tables with String keys, you may need to recreate them

### Gemini API Error
```
RuntimeError: GOOGLE_GENAI_API_KEY not found
```
**Solution**: Add your Google AI API key to `.env`

## 🚀 Migration from Old Code

If you have existing data with string user_ids:

1. **Option A**: Create new tables (recommended)
   - Update `.env` with new table names
   - Let the app create new tables with Number keys

2. **Option B**: Manual migration
   - Export data from old tables
   - Convert string IDs to integers
   - Import to new tables

## 📦 Features Summary

- ✅ Automatic table creation
- ✅ Integer user IDs
- ✅ Profile management
- ✅ Conversation history tracking
- ✅ **AI-powered conversation summaries**
- ✅ **Context preservation across sessions**
- ✅ Keyword extraction
- ✅ Context-aware responses
- ✅ Error handling
- ✅ API documentation
- ✅ Health checks
- ✅ CORS support

## 📄 License

This project is proprietary and confidential.

## 👥 Support

For issues or questions, contact the development team.