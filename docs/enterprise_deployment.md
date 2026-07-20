# 🏢 NexusCore Enterprise Deployment Guide

## Architecture Overview

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   Load        │────▶│  FastAPI      │────▶│  Vector DB    │
│   Balancer    │     │  (x3 replicas)│     │  (ChromaDB)   │
└───────────────┘     └───────┬───────┘     └───────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Observability    │
                    │  Stack            │
                    │  ┌─────────────┐  │
                    │  │ LangSmith / │  │
                    │  │ Phoenix     │  │
                    │  └─────────────┘  │
                    │  ┌─────────────┐  │
                    │  │ Metrics +   │  │
                    │  │ Alerts      │  │
                    │  └─────────────┘  │
                    └───────────────────┘
```

## Production Deployment (Docker Compose)

Create `docker-compose.yml`:

```yaml
version: "3.9"
services:
  nexuscore-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
      - LOG_LEVEL=INFO
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      retries: 3

  nexuscore-dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    ports:
      - "8501:8501"
    depends_on:
      - nexuscore-api

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma
    ports:
      - "8001:8000"

  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"
    volumes:
      - phoenix_data:/data

volumes:
  chroma_data:
  phoenix_data:
```

## Environment Variables (Production)

```env
# ─── Required ─────────────────────────────────────
OPENAI_API_KEY=sk-...
# ─── Observability ────────────────────────────────
LANGSMITH_API_KEY=lsv2_...
PHOENIX_COLLECTOR_ENDPOINT=http://phoenix:6006/v1/traces
# ─── Server ───────────────────────────────────────
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
# ─── Memory ───────────────────────────────────────
CHROMA_HOST=chromadb
CHROMA_PORT=8000
```

## Scaling Guidelines

| Component | Strategy |
|---|---|
| **API Servers** | Horizontal scaling behind load balancer (stateless) |
| **Vector DB** | ChromaDB in persistent mode with replication |
| **Tracing** | Phoenix/OpenTelemetry collector for high throughput |
| **Memory** | In-memory buffer + persistent vector store |
| **Event Queue** | Redis/RabbitMQ for event-driven agents |

## Monitoring & SLAs

| Metric | Target | Alert |
|---|---|---|
| p95 Latency | < 2s | > 10s |
| Success Rate | > 99% | < 95% |
| Cost/Task | < $0.01 | > $0.05 |
| Uptime | 99.9% | Any downtime |

## Security

- All API keys stored as environment variables (never in code)
- HITL approval required for destructive operations
- Full audit trail for every agent decision
- Tool permission levels (user/admin/system)
- Rate limiting via reverse proxy
