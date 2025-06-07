# Sales Discovery Bot - Development Guide

## Quick Start for New Sessions

**Starting a new development session?** Follow these steps:

1. **Read the Build Guide**: Check `BUILD_GUIDE.md` for current status
2. **Set up environment**: Copy `.env.example` to `.env` and add keys
3. **Start services**: Run `docker-compose up -d`
4. **Run tests**: Execute `pytest tests/` to verify everything works

---

## Architecture Overview

### Conversation State Machine (LangGraph)

```python
# The agent uses a 6-stage conversation flow:
START → UNDERSTAND → IDENTIFY → SCOPE → PROPOSE → RECOMMEND → BOOK → END

# Each stage has specific objectives:
- UNDERSTAND: Gather business context (2-3 questions)
- IDENTIFY: Find the MVP opportunity
- SCOPE: Get detailed requirements
- PROPOSE: Generate formatted proposal
- RECOMMEND: Suggest partnership tier
- BOOK: Drive to Calendly demo
```

### Key Components

1. **LangGraph Agent** (`agent/logic.py`)
   - Manages conversation state
   - Orchestrates stage transitions
   - Maintains context across messages

2. **FastAPI Backend** (`api/main.py`)
   - Handles HTTP requests
   - Manages database operations
   - Serves widget interface

3. **PostgreSQL Storage**
   - Conversations table: Full state persistence
   - Messages table: Chat history
   - Leads table: Qualified opportunities

---

## Local Development

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Environment Setup

```bash
# 1. Clone the repository
git clone https://github.com/Instabidsai/sales-discovery-bot
cd sales-discovery-bot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# 5. Start infrastructure
docker-compose up -d

# 6. Initialize database
python -m scripts.init_db

# 7. Run the API
python -m uvicorn api.main:app --reload
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/test_unit.py -v          # Unit tests only
pytest tests/test_integration.py -v   # Integration tests
pytest tests/test_performance.py -v   # Performance tests

# Run with coverage
pytest tests/ --cov=agent --cov=api --cov-report=html
```

---

## Code Structure

### Agent Logic (`agent/`)

```python
# agent/logic.py - Main conversation orchestrator
class SalesDiscoveryAgent:
    def __init__(self, config):
        self.llm = ChatOpenAI(...)           # LLM instance
        self.checkpointer = InMemorySaver()  # State persistence
        self.graph = self._build_graph()     # LangGraph state machine
    
    async def process_message(self, conversation_id, message):
        # Main entry point for processing messages
        pass
```

### State Management (`agent/state.py`)

```python
# ConversationState tracks:
- messages: Full conversation history
- stage: Current conversation stage
- business_info: Extracted company details
- mvp_proposal: Generated proposal
- partnership_tier: Recommended tier
```

### API Endpoints (`api/main.py`)

```python
# Key endpoints:
POST /chat           # Process a message
GET /health          # Health check
GET /metrics         # Prometheus metrics
GET /conversation/{id}  # Get history
GET /widget.js       # Embeddable script
```

---

## Debugging Tips

### Common Issues

1. **Import Errors**
   ```python
   # Wrong:
   from langgraph import StateGraph  # Old syntax
   
   # Correct:
   from langgraph.graph import StateGraph  # Current syntax
   ```

2. **State Persistence**
   ```python
   # Always use thread_id for conversation continuity:
   config = {"configurable": {"thread_id": conversation_id}}
   ```

3. **Token Limits**
   ```python
   # Monitor token usage:
   if estimated_tokens > daily_limit:
       raise TokenLimitExceeded()
   ```

### Logging

```python
# Enable debug logging:
import logging
logging.basicConfig(level=logging.DEBUG)

# Key loggers to watch:
- agent.logic
- api.main
- api.database
```

---

## Deployment

### Building the Container

```bash
# Build production image
docker build -t ghcr.io/instabidsai/sales-discovery-bot:latest .

# Test locally
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e POSTGRES_DSN=$POSTGRES_DSN \
  ghcr.io/instabidsai/sales-discovery-bot:latest

# Push to registry
docker push ghcr.io/instabidsai/sales-discovery-bot:latest
```

### Kubernetes Deployment

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets
kubectl create secret generic salesbot-secrets \
  --from-literal=openai-api-key=$OPENAI_API_KEY \
  --from-literal=postgres-dsn=$POSTGRES_DSN \
  -n agents

# Deploy application
kubectl apply -f k8s/

# Check status
kubectl get pods -n agents -l app=sales-discovery-bot
kubectl logs -n agents -l app=sales-discovery-bot -f
```

---

## Performance Optimization

### Token Management

```python
# Implement token budgets:
class TokenBudgetManager:
    daily_limit = 1_000_000
    cost_per_1k = 0.02
    
    async def check_budget(self, estimated_tokens):
        # Prevent overspending
        pass
```

### Scaling Strategies

1. **KEDA Autoscaling**: Configured for 1-20 pods
2. **Redis Caching**: Cache common responses
3. **Connection Pooling**: PostgreSQL pool size 5-20
4. **Async Everything**: All I/O operations are async

---

## Monitoring

### Key Metrics

```python
# Prometheus metrics exposed:
- conversations_started_total
- conversations_completed_total  
- demos_booked_total
- response_time_seconds (histogram)
- partnership_tier_distribution
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/metrics

# Database connectivity
kubectl exec -it deploy/sales-discovery-bot -- \
  python -c "from api.database import DatabaseManager; ..."
```

---

## Contributing

### Code Style

- Use Black for formatting: `black .`
- Sort imports with isort: `isort .`
- Type hints required for all functions
- Docstrings for all public methods

### Pull Request Process

1. Create feature branch: `git checkout -b feature/your-feature`
2. Write tests for new functionality
3. Ensure all tests pass: `pytest tests/`
4. Update documentation if needed
5. Submit PR with clear description

---

## Troubleshooting

### LangGraph Issues

```python
# Verify state transitions:
result = agent.graph.get_state(config)
print(f"Current stage: {result.values.get('stage')}")
print(f"Message count: {len(result.values.get('messages', []))}")
```

### Database Issues

```sql
-- Check conversation state:
SELECT conversation_id, state->>'stage', created_at 
FROM conversations 
ORDER BY created_at DESC 
LIMIT 10;

-- Check message flow:
SELECT role, content, created_at 
FROM messages 
WHERE conversation_id = 'your-id' 
ORDER BY created_at;
```

### Memory Leaks

```python
# Monitor memory usage:
import psutil
process = psutil.Process()
print(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")
```

---

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [KEDA Scaling Guide](https://keda.sh/docs/)
- [OpenAI API Reference](https://platform.openai.com/docs/)

---

**For session continuity, always start by reading BUILD_GUIDE.md!**