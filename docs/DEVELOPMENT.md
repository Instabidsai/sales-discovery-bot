# Development Guide

## Local Setup

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Redis (via Docker)
- PostgreSQL (via Docker)

### Environment Variables

Create a `.env` file:
```env
# Required
OPENAI_API_KEY=sk-...
POSTGRES_DSN=postgresql://salesbot:password@localhost:5434/salesbot
REDIS_URL=redis://localhost:6381/0
CALENDLY_URL=https://calendly.com/your-link

# Optional
DEBUG_LOCAL=true
LOG_LEVEL=INFO
DAILY_TOKEN_LIMIT=1000000
DAILY_COST_LIMIT=50.0
```

### Docker Services

Start local services:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

This starts:
- PostgreSQL on port 5434
- Redis on port 6381

### Database Setup

Initialize the database:
```bash
python -m scripts.init_db
```

## Running the Agent

### API Server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Worker (if using queue mode)
```bash
python -m jobs.worker
```

## Testing

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Tests
```bash
pytest tests/test_unit.py -v
pytest tests/test_integration.py -v
pytest tests/test_performance.py -v
```

### Test Coverage
```bash
pytest tests/ --cov=agent --cov=api --cov-report=html
```

## API Endpoints

### Chat Endpoint
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": "optional-uuid",
    "message": "I run a marketing agency",
    "source": "web"
  }'
```

### Health Check
```bash
curl http://localhost:8000/health
```

### Metrics
```bash
curl http://localhost:8000/metrics
```

### Get Conversation
```bash
curl http://localhost:8000/conversation/{conversation_id}
```

## Widget Integration

### Embed in Website
```html
<script src="https://your-domain.com/widget.js"></script>
<script>
  InstaSalesBot.init({
    position: 'bottom-right',
    primaryColor: '#4F46E5'
  });
</script>
```

### Email Campaign
```html
<a href="https://your-domain.com/widget?source=email&campaign=launch">
  Chat with our AI Sales Assistant
</a>
```

## Debugging

### View Logs
```bash
# API logs
docker-compose logs -f api

# Database queries
docker-compose logs -f postgres

# Redis operations
docker-compose logs -f redis
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U salesbot -d salesbot

# View conversations
SELECT * FROM conversations ORDER BY created_at DESC LIMIT 5;

# View messages
SELECT * FROM messages WHERE conversation_id = 'uuid-here';
```

### Redis Access
```bash
# Connect to Redis
docker-compose exec redis redis-cli

# View keys
KEYS *

# Get conversation state
GET conversation:uuid-here
```

## Common Issues

### Port Conflicts
If default ports are in use, modify `docker-compose.dev.yml`:
- PostgreSQL: Change 5434 to another port
- Redis: Change 6381 to another port

### Import Errors
Always use virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Database Connection
Verify PostgreSQL is running:
```bash
docker-compose ps
```

### LangGraph State Errors
Ensure you're using the correct version:
```bash
pip show langgraph  # Should be 0.0.20+
```

## Performance Tips

1. **Token Usage**: Monitor daily limits in logs
2. **Database Pooling**: Configured for 10 connections
3. **Redis TTL**: Conversations expire after 24 hours
4. **Response Caching**: Consider caching common responses

## Deployment Checklist

- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Docker image builds successfully
- [ ] Database migrations applied
- [ ] Health check endpoint responding
- [ ] Monitoring configured
- [ ] Secrets in Vault
- [ ] CORS settings verified
- [ ] Rate limiting configured
- [ ] Error alerts set up
