# Vintality AI Layer — LLM-Powered Agronomic Advisor

A production-ready demo of an AI layer for precision viticulture. Built as a portfolio project demonstrating **structured RAG**, **Claude tool-use**, and **domain-specific prompt engineering** — the core architecture described in Vintality's LLM Integration Developer role.

## What this demonstrates

| Capability | Implementation |
|---|---|
| **Structured RAG over database** | Tool functions query PostgreSQL (not document stores) for exact sensor readings |
| **Document RAG (pgvector)** | Sensor troubleshooting knowledge base with vector similarity search |
| **Claude tool-use / function calling** | 6 tools Claude selects autonomously based on natural language questions |
| **Multi-step reasoning** | Agentic loop — Claude calls multiple tools across rounds to build complete answers |
| **Agronomic interpretation** | Domain-tuned system prompt grounds responses in viticulture knowledge |
| **Context window management** | Farm profile in system prompt; sensor data fetched on-demand via tools |
| **Hallucination validation** | Post-response check verifies numerical claims against tool-returned data |
| **Streaming responses (SSE)** | Real-time token streaming from Claude → FastAPI → React frontend |
| **Interactive dashboard** | Block status cards, soil/disease charts, weather strip, with "Ask AI" deep-links |

## Architecture

```
React Chat UI (Vite)
    ↓ POST /api/chat/stream (SSE)
FastAPI Backend
    ↓ Claude Messages API (tool-use)
Claude Agent (Anthropic API)
    ↓ tool_use → execute → tool_result → repeat
Tool Functions (Python)
    ↓ SQL queries
PostgreSQL + PostGIS + pgvector
    (sensor data, models, forecasts, knowledge base)
```

## Demo farm scenario

**Naramata Hills Vineyard** — 4 blocks on the Naramata Bench, Okanagan Valley:

- **B5 (Cab Franc)**: Critically dry — VWC declining to 28%, deficit at 34mm, last irrigation 5 days ago. Demonstrates irrigation urgency detection.
- **B3 (Pinot Noir)**: PM risk climbing to 72 — high humidity, north-facing, spray was 9+ days ago. Demonstrates disease risk alerting.
- **B7 (Chardonnay)**: Healthy baseline — well irrigated, low disease risk. Demonstrates normal conditions reporting.
- **B9 (Merlot)**: Sensor anomaly — TH-B9b reads 3°C above block average. Demonstrates divergence detection.

## Quick start

### Prerequisites
- Docker Desktop
- Python 3.11+
- Node.js 18+
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### 1. Start the database

```bash
docker compose up -d
```

This starts PostgreSQL 16 with PostGIS and pgvector, creates the schema, and seeds realistic vineyard data (7 days of hourly sensor readings).

### 2. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp ../.env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Test with the CLI (no frontend needed)

```bash
python -m test_cli
```

Try these queries:
1. "Is it safe to irrigate Block 5 today?"
2. "Why is PM risk spiking on my Pinot Noir?"
3. "Which blocks need attention most urgently?"
4. "Check the sensors in Block B9"

### 4. Start the API server

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Start the frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Tool library

| Tool | Description | Maps to JD scope |
|---|---|---|
| `get_soil_moisture` | VWC, deficit, field capacity, irrigation history per block | Phase 1: Soil/irrigation queries |
| `get_disease_risk` | PM and Botrytis scores, driving conditions, spray status | Phase 1: Disease risk queries |
| `get_weather_forecast` | 24-48h forecast with spray window assessment | Phase 1: Weather queries |
| `get_canopy_environment` | Temp, humidity, VPD with sensor divergence detection | Phase 1: Canopy queries |
| `get_farm_overview` | Cross-block comparison ranked by urgency | Phase 1: Cross-block comparison |
| `search_knowledge_base` | pgvector doc search for sensor troubleshooting | Phase 4: Support knowledge base |

## Technical stack

- **LLM**: Anthropic Claude (Sonnet) with tool-use / function calling
- **Backend**: Python, FastAPI, SSE streaming
- **Database**: PostgreSQL 16 + PostGIS (spatial) + pgvector (embeddings)
- **Frontend**: React 18, Vite, SSE client
- **Infra**: Docker Compose

## Project structure

```
vintality-demo/
├── docker-compose.yml        # PostgreSQL + PostGIS + pgvector
├── db/
│   └── init.sql              # Schema: farms, blocks, sensors, readings, models
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── config.py         # Environment config
│   │   ├── database.py       # SQLAlchemy connection
│   │   ├── agent/
│   │   │   ├── orchestrator.py  # Agentic tool-use loop (core)
│   │   │   └── prompts.py       # System prompt + session context
│   │   ├── tools/
│   │   │   ├── definitions.py   # Tool JSON schemas for Claude
│   │   │   ├── soil.py          # get_soil_moisture
│   │   │   ├── disease.py       # get_disease_risk
│   │   │   ├── weather.py       # get_weather_forecast
│   │   │   ├── canopy.py        # get_canopy_environment
│   │   │   └── overview.py      # get_farm_overview
│   │   └── routes/
│   │       └── chat.py          # REST + SSE streaming endpoints
│   ├── test_cli.py           # Interactive CLI for testing
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx            # Dashboard layout shell
    │   ├── Chat.jsx           # Chat UI with SSE streaming
    │   └── styles.css         # Dashboard styling
    └── package.json
```

## Built by

**Ojasv Issar** — [ojasvissar.github.io/og](https://ojasvissar.github.io/og) | [GitHub](https://github.com/ojasvissar)

MDS Candidate @ UBC Vancouver | Data Science + LLM Integration
