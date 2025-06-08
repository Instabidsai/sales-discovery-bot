# Build stage
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage  
FROM python:3.11-slim

# GitHub Container Registry label - REQUIRED for package association
LABEL org.opencontainers.image.source="https://github.com/Instabidsai/sales-discovery-bot"

# Security: non-root user
RUN groupadd -r agent && useradd -r -g agent agent

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application - copy individual directories
WORKDIR /app
COPY --chown=agent:agent agent/ ./agent/
COPY --chown=agent:agent jobs/ ./jobs/
COPY --chown=agent:agent api/ ./api/
COPY --chown=agent:agent tests/ ./tests/

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

USER agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
