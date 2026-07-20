# 📦 NexusCore — Installation & Setup Guide

## Prerequisites

- **Python 3.10+** (3.12 recommended)
- **pip** (latest)
- **API Key**: At least one LLM provider API key (OpenAI, Anthropic, or both)
- **Docker** (optional, for production deployment)
- **Redis** (optional, for event-driven agent features)

---

## 1. Clone the Repository

```bash
git clone https://github.com/Sarancoding/AgenticForge.git
cd AgenticForge
```

---

## 2. Set Up Python Environment

```bash
python -m venv venv
source venv/bin/activate    # Linux/macOS
# or
venv\Scripts\activate       # Windows
```

---

## 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 4. Configure Environment Variables

Copy the template and fill in your API keys:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
# ─── Required: At least one LLM provider ──────────────────────────
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...

# ─── Optional: For vector memory (defaults to in-memory) ──────────
# CHROMA_PERSIST_DIR=./chroma_data

# ─── Optional: For event-driven agents ────────────────────────────
# REDIS_URL=redis://localhost:6379/0

# ─── Server Configuration ────────────────────────────────────────
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
```

> ⚠️ **Never commit `.env` to version control.** It is already in `.gitignore`.

---

## 5. Running the System

### 🔹 Development Mode — Backend Only

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 🔹 Development Mode — With Dashboard

**Terminal 1 (backend):**
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (dashboard):**
```bash
streamlit run ui/app.py --server.port 8501
```

### 🔹 Production Mode (Docker Compose)

```bash
docker-compose up --build
```

---

## 6. Quick Start Example

```python
"""Trigger a multi-agent debate with HITL fallback."""
import httpx

response = httpx.post(
    "http://localhost:8000/api/agents/debate",
    json={
        "task": "Design a microservices architecture for a real-time chat app",
        "num_proposers": 3,
        "require_human_approval": True,
        "max_tokens": 4000
    }
)
print(response.json())
```

---

## 7. Running Tests

```bash
pytest tests/ -v --cov=src
```

---

## 📁 Project Structure

```
AgenticForge/
├── src/
│   ├── agents/
│   │   ├── router.py           # CostAwareRouter
│   │   ├── react_agent.py      # ReAct planning agent
│   │   ├── debate_agent.py     # Multi-agent debate system
│   │   ├── self_reflective_agent.py
│   │   └── event_agent.py      # Event-triggered automation
│   ├── memory/
│   │   └── memory_manager.py   # HybridMemory
│   ├── tools/
│   │   └── orchestrator.py     # ToolOrchestrator
│   ├── workflows/
│   │   └── hitl_workflow.py    # HITL state graph
│   └── main.py                 # FastAPI entry point
├── tests/
│   ├── test_router.py
│   ├── test_react_loop.py
│   ├── test_memory.py
│   ├── test_hitl.py
│   └── test_orchestrator.py
├── ui/
│   └── app.py                  # Streamlit dashboard
├── docs/
│   └── overview.md             # Technical architecture docs
├── .env.example
├── .gitignore
├── requirements.txt
├── INSTALL.md
└── README.md
```
