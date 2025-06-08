# Sales Discovery Bot - Repository Structure

```
sales-discovery-bot/
├── .github/
│   └── workflows/
│       └── update-layout.yml    # Auto-updates this file on push
├── agent/                       # Core agent logic
│   ├── __init__.py
│   ├── config.py               # Configuration and environment
│   ├── logic.py                # Main LangGraph agent
│   ├── prompts.py              # System prompts
│   ├── state.py                # Conversation state management
│   └── tools.py                # Business logic tools
├── api/                        # FastAPI application
│   ├── __init__.py
│   ├── database.py             # PostgreSQL connection
│   ├── main.py                 # API endpoints
│   └── models.py               # Pydantic models
├── docs/
│   └── DEVELOPMENT.md          # Development guide
├── jobs/
│   └── worker.py               # Background worker (optional)
├── k8s/                        # Kubernetes manifests
│   ├── configmap.yaml
│   ├── deployment.yaml
│   ├── keda-scaler.yaml
│   ├── namespace.yaml
│   ├── service.yaml
│   └── vault-policy.hcl
├── monitoring/                 # Observability configs
│   ├── alerts.yaml
│   └── dashboard.json
├── scripts/
│   └── init_db.py              # Database initialization
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_integration.py
│   ├── test_performance.py
│   └── test_unit.py
├── .env.example                # Environment template
├── .gitignore
├── BUILD_GUIDE.md             # Complete build history
├── docker-compose.dev.yml      # Local development services
├── docker-compose.yml          # Production compose
├── Dockerfile                  # Multi-stage build
├── pyproject.toml             # Python project config
├── README.md                  # Project overview
├── REPO_LAYOUT.md            # This file
└── requirements.txt           # Python dependencies
```

## Key Components

### `/agent`
Core business logic using LangGraph for stateful conversation management. The 6-step sales discovery flow is implemented here.

### `/api`
FastAPI application providing REST endpoints, widget serving, and health checks.

### `/k8s`
Production-ready Kubernetes configurations with KEDA autoscaling and Vault integration.

### `/tests`
Comprehensive test suite including unit, integration, and performance tests.

## Quick Navigation

- **Start here**: [README.md](README.md)
- **Build details**: [BUILD_GUIDE.md](BUILD_GUIDE.md)
- **Local setup**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)

Generated on: 2025-06-07
