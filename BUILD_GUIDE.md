# Sales Discovery Bot - Build Guide & Progress Tracker

**Last Updated**: 2025-01-07 22:50 UTC
**Build Session**: Session 1 - Initial Build
**Agent Status**: 🟡 PARTIALLY COMPLETE (Core built, needs testing & deployment)

---

## 🎯 Project Overview

**Purpose**: Build a conversational sales discovery agent for Insta Agents that:
- Conducts structured 6-step conversations with business owners
- Identifies automation opportunities
- Proposes MVP AI agent solutions
- Recommends partnership tiers ($1,250/$2,500/$5,000)
- Drives demo bookings via Calendly
- Stores conversations in PostgreSQL for follow-up

**Target Deployment**: 
- Embeddable widget for websites
- Email campaign integration
- Direct API access

---

## 🏗️ Architecture Decisions Made

### Framework Selection
- **LangGraph** v0.0.20 - For stateful conversation management
- **LangChain-OpenAI** v0.0.5 - For LLM integration
- **FastAPI** - For API endpoints
- **PostgreSQL + AsyncPG** - For conversation persistence
- **Redis** - For state management
- **KEDA** - For autoscaling based on HTTP RPS

### Model Selection
- **Primary**: GPT-4o (conversational, balanced cost/performance)
- **Token Limits**: 1000 tokens per response
- **Daily Limits**: 1M tokens, $50 cost limit

---

## ✅ What's Been Built (Session 1)

### 1. **Repository Structure** ✅
- Created GitHub repo: `Instabidsai/sales-discovery-bot`
- Established standard agent directory structure
- Added comprehensive README with deployment instructions

### 2. **Core Agent Logic** ✅
```python
# Key files created:
agent/
├── __init__.py          ✅ Package initialization
├── config.py            ✅ Configuration management (env vars, pricing tiers)
├── prompts.py           ✅ System prompts and conversation templates
├── state.py             ✅ LangGraph state management (ConversationState)
├── logic.py             ✅ Main agent with 6-stage flow
└── tools.py             ✅ Business extraction, MVP generation, tier selection
```

**Conversation Flow Implemented**:
1. `understand` → Ask 2-3 business questions
2. `identify` → Find MVP opportunity  
3. `scope` → Get specific requirements
4. `propose` → Generate formatted proposal
5. `recommend` → Suggest partnership tier
6. `book` → Show Calendly link

### 3. **API Layer** ✅
```python
api/
├── __init__.py          ✅
├── main.py              ✅ FastAPI app with CORS, health, metrics
├── models.py            ✅ Pydantic models for requests/responses
└── database.py          ✅ Async PostgreSQL manager
```

**Endpoints Created**:
- `POST /chat` - Process conversations
- `GET /health` - Health checks
- `GET /metrics` - Prometheus metrics
- `GET /conversation/{id}` - Retrieve history
- `GET /widget.js` - Embeddable JavaScript
- `GET /widget` - Chat interface HTML

### 4. **Database Schema** ✅
```sql
-- Tables created via migrations:
- conversations (id, source, state, metadata)
- messages (conversation_id, role, content)
- leads (conversation_id, business_info, mvp_proposal, tier)
```

### 5. **Test Suite** ✅
```python
tests/
├── test_unit.py         ✅ Agent logic, extraction, proposals
├── test_integration.py  ✅ API endpoints, database ops
└── test_performance.py  ✅ Response time, concurrency, memory
```

### 6. **Kubernetes Configs** ✅
```yaml
k8s/
├── namespace.yaml       ✅ Agents namespace
├── configmap.yaml       ✅ Non-sensitive config
├── deployment.yaml      ✅ Main deployment with Vault
├── service.yaml         ✅ ClusterIP + Ingress
├── keda-scaler.yaml     ✅ Autoscaling (1-20 pods)
└── vault-policy.hcl     ✅ Secret access policy
```

### 7. **Docker & Local Dev** ✅
- Multi-stage Dockerfile for minimal production image
- docker-compose.yml for local development
- Non-root user, health checks included

### 8. **Monitoring** ✅
- Prometheus metrics exported
- Grafana dashboard JSON
- Alert rules for errors, latency, conversions

---

## ❌ What Still Needs Building

### 1. **Environment & Secrets Setup** 🔴
```bash
# Required secrets (not yet in Vault):
OPENAI_API_KEY          # For LLM calls
POSTGRES_DSN            # Database connection
REDIS_URL               # State management
CALENDLY_URL            # Demo booking link
```

### 2. **Container Build & Registry** 🔴
- Haven't built Docker image yet
- Need to push to ghcr.io/instabidsai/sales-discovery-bot
- No CI/CD pipeline set up

### 3. **Database Deployment** 🔴
- PostgreSQL instance not provisioned
- Migrations not run
- No backup strategy

### 4. **Testing & Validation** 🔴
- Unit tests written but not executed
- Integration tests need live services
- No load testing performed
- LangGraph conversation flow not validated

### 5. **Deployment Prerequisites** 🔴
- Kubernetes cluster access needed
- KEDA not installed
- Vault not configured
- Prometheus/Grafana not set up
- Ingress controller needed
- TLS certificates for salesbot.insta-agents.com

### 6. **Widget Integration** 🔴
- JavaScript widget created but not tested
- CORS headers configured but not validated
- No example integration code
- No email template for campaigns

---

## 📋 Next Steps (Session 2 Focus)

### Immediate Priorities:
1. **Local Testing**
   ```bash
   # Set up .env file with:
   OPENAI_API_KEY=sk-...
   POSTGRES_DSN=postgresql://...
   REDIS_URL=redis://localhost:6379
   
   # Run locally:
   docker-compose up
   pytest tests/
   ```

2. **Fix Any Issues**
   - Verify LangGraph state transitions work
   - Test conversation persistence
   - Validate proposal generation

3. **Build & Push Container**
   ```bash
   docker build -t ghcr.io/instabidsai/sales-discovery-bot:v1.0.0 .
   docker push ghcr.io/instabidsai/sales-discovery-bot:v1.0.0
   ```

4. **Deploy Infrastructure**
   - Provision PostgreSQL (Supabase/RDS)
   - Set up Redis instance
   - Configure Vault secrets
   - Install KEDA in cluster

5. **Deploy to K8s**
   ```bash
   kubectl apply -f k8s/
   ```

---

## 🐛 Known Issues & Fixes Needed

### 1. **LangGraph Version**
- Currently using `langgraph==0.0.20`
- Latest syntax verified via Context7
- May need to update imports if newer version required

### 2. **Memory Management**
- No conversation summarization implemented
- Could hit token limits on long conversations
- Consider adding `langmem` for message history management

### 3. **Error Handling**
- Need retry logic for LLM calls
- Database connection pooling needs testing
- No graceful degradation if services unavailable

---

## 📊 Success Metrics

Once deployed, monitor:
- **Conversations Started**: Target 100/day
- **Completion Rate**: Target >30% reach proposal
- **Demo Bookings**: Target >10% of completions
- **Response Time**: <2s p95
- **Availability**: 99.9% uptime
- **Cost per Conversation**: <$0.10

---

## 🔧 Development Commands

```bash
# Local development
cp .env.example .env          # Configure environment
docker-compose up -d          # Start services
python -m scripts.init_db     # Initialize database
python -m pytest tests/ -v    # Run tests
python -m api.main            # Start API locally

# Docker operations
docker build -t salesbot .    # Build image
docker run -p 8000:8000 salesbot  # Run container

# Kubernetes operations
kubectl apply -f k8s/namespace.yaml
kubectl create secret generic salesbot-secrets --from-env-file=.env
kubectl apply -f k8s/
kubectl port-forward svc/sales-discovery-bot 8000:80

# Monitoring
kubectl logs -l app=sales-discovery-bot -f
kubectl exec -it deploy/sales-discovery-bot -- curl localhost:8000/health
```

---

## 📝 Notes for Next Session

1. **Check Local .env File**: User mentioned having API keys locally
2. **Test LangGraph Flow**: Critical path - ensure state transitions work
3. **Validate Proposals**: Test quality of generated MVP proposals
4. **Performance Testing**: Verify can handle 100 concurrent conversations
5. **Widget Testing**: Create test page with embedded widget

---

## 🔗 External Dependencies

- **OpenAI API**: For GPT-4o model access
- **PostgreSQL**: Version 15+ with UUID extension
- **Redis**: Version 7+ for state management
- **Kubernetes**: 1.25+ with KEDA 2.10+
- **Vault**: For secret management
- **Prometheus + Grafana**: For monitoring
- **GitHub Container Registry**: For image storage

---

**End of Session 1 Build Guide**

To continue in next session, start here:
1. Read this BUILD_GUIDE.md
2. Check `git status` in the repo
3. Review any error logs from attempted deployments
4. Continue from "Next Steps" section above