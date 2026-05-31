# AI-Powered Supply Chain Risk Intelligence Assistant

An end-to-end supply chain risk intelligence system built with RAG, hybrid search,
multi-agent AI, anomaly detection, and an interactive analytics dashboard.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        Frontend (HTML/JS)                        │
│  Search · Recommendations · Multi-Agent · Dashboard · Anomalies  │
└───────────────────────────┬──────────────────────────────────────┘
                            │ REST (FastAPI)
┌───────────────────────────▼──────────────────────────────────────┐
│                    API Layer  /api/v1                             │
│   /search   /recommendations   /agents/analyze   /analytics      │
└─────┬──────────────┬───────────────┬────────────────┬────────────┘
      │              │               │                │
 ┌────▼────┐  ┌──────▼──────┐ ┌─────▼──────┐  ┌─────▼──────┐
 │  RAG    │  │ Recommend.  │ │  Multi-    │  │ Analytics  │
 │ Service │  │  Service    │ │  Agent     │  │ + Anomaly  │
 └────┬────┘  └──────┬──────┘ │ Orchestr.  │  │ Detection  │
      │              │        └─────┬──────┘  └────────────┘
      │         ┌────▼──────┐       │
 ┌────▼──────┐  │ Risk Score│  ┌────▼─────────────────────────┐
 │  Hybrid   │  │ Evaluation│  │  Parallel Specialized Agents │
 │  Search   │  │ (DeepEval │  │  ├─ SupplierRiskAgent        │
 │ BM25+Sem  │  │  LLM-Judge│  │  ├─ ShipmentAnalysisAgent    │
 └────┬──────┘  └───────────┘  │  ├─ InventoryIntelAgent      │
      │                        │  └─ RecommendationAgent       │
 ┌────▼──────────────────┐     └──────────────────────────────┘
 │  ChromaDB Vector Store│
 │  + BM25 Index         │
 └────┬──────────────────┘
      │
 ┌────▼──────────────────┐
 │  Embedding Model      │
 │  (all-MiniLM-L6-v2)   │
 └────┬──────────────────┘
      │
 ┌────▼──────────────────┐
 │  supply_chain_data.csv│
 │  (600 incidents)      │
 └───────────────────────┘
```

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI entrypoint
│   │   ├── core/
│   │   │   ├── config.py               # Settings (pydantic-settings)
│   │   │   ├── embeddings.py           # Sentence-Transformers wrapper
│   │   │   ├── vector_store.py         # ChromaDB integration
│   │   │   ├── hybrid_search.py        # BM25 + semantic RRF fusion
│   │   │   └── guardrails.py           # Input validation & safety
│   │   ├── models/schemas.py           # Pydantic request/response models
│   │   ├── data/
│   │   │   ├── generate_sample.py      # Synthetic dataset generator
│   │   │   ├── ingestion.py            # Data ingestion pipeline
│   │   │   ├── preprocessing.py        # Cleaning & risk score enrichment
│   │   │   └── chunking.py             # Doc chunking + token counting
│   │   ├── services/
│   │   │   ├── rag_service.py          # Core RAG (search + LLM generation)
│   │   │   ├── risk_scoring.py         # Supplier/inventory/shipment scoring
│   │   │   ├── anomaly_detection.py    # IsolationForest + correlations
│   │   │   └── evaluation_service.py   # DeepEval + LLM-as-judge
│   │   ├── agents/
│   │   │   ├── base_agent.py           # Abstract agent with tool-use support
│   │   │   ├── supplier_risk_agent.py
│   │   │   ├── shipment_analysis_agent.py
│   │   │   ├── inventory_intelligence_agent.py
│   │   │   ├── recommendation_agent.py
│   │   │   └── orchestrator.py         # Parallel A2A orchestration
│   │   └── api/routes/
│   │       ├── search.py               # POST /search, /search/hybrid
│   │       ├── recommendations.py      # POST /recommendations
│   │       ├── analytics.py            # GET /analytics/dashboard, /anomalies
│   │       └── agents.py               # POST /agents/analyze
│   ├── tests/
│   │   ├── test_search.py
│   │   └── test_agents.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html                      # Single-page dashboard
│   ├── styles.css
│   └── app.js
├── data/                               # Place supply_chain_data.csv here
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Generate Sample Dataset

```bash
cd backend
python -m app.data.generate_sample
```

This creates `data/supply_chain_data.csv` with 600 realistic supply chain incidents.

### 5. Start the Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

The server auto-ingests data on first startup, builds the ChromaDB vector store,
and constructs the BM25 index.

### 6. Open the Frontend

Open `frontend/index.html` directly in a browser, or serve with:

```bash
cd frontend
python -m http.server 3000
```

Then visit [http://localhost:3000](http://localhost:3000).

---

## Docker (Full Stack)

```bash
# Copy and fill in your API key
cp .env.example .env

# Build and start all services
docker-compose up --build

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

---

## API Usage Examples

### Semantic / Hybrid Search

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "supplier delivery delays for critical components",
    "top_k": 5,
    "use_hybrid": true,
    "severity": "critical"
  }'
```

### Risk Mitigation Recommendations (with LLM Judge)

```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "query": "port congestion is impacting our shipment schedules significantly",
    "evaluate_quality": true
  }'
```

### Multi-Agent Analysis (Supplier + Shipment + Inventory + Recommendation)

```bash
curl -X POST http://localhost:8000/api/v1/agents/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "query": "warehouse inventory approaching stockout and supplier delays increasing",
    "include_all_agents": true,
    "supplier_id": "S003"
  }'
```

### Analytics Dashboard

```bash
curl http://localhost:8000/api/v1/analytics/dashboard
```

### Anomaly Detection

```bash
curl "http://localhost:8000/api/v1/analytics/anomalies?contamination=0.05"
```

### Force Data Re-ingestion

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"force_rebuild": true}'
```

---

## Key Features

### Requirement 1 — Basic

| Feature | Implementation |
|---|---|
| Basic RAG | `rag_service.py` — retrieve → truncate → Claude generation |
| Hybrid Search | `hybrid_search.py` — BM25 (rank_bm25) + semantic (ChromaDB) via RRF |
| Semantic Search | `vector_store.py` — cosine similarity with all-MiniLM-L6-v2 |
| Metadata Filtering | ChromaDB `$where` filters on supplier, warehouse, severity, status |
| Risk Recommendation Engine | `risk_scoring.py` + `rag_service.py` |
| Input Validation Guardrails | `guardrails.py` — injection detection, supply chain relevance check |
| Incident Similarity Ranking | Hybrid RRF + logistics-aware reranker |
| Recommendation Generation | Claude claude-sonnet-4-6 with prompt caching |
| API Endpoints | FastAPI with 8 endpoints, Swagger docs at `/docs` |

### Requirement 2 — Advanced

| Feature | Implementation |
|---|---|
| DeepEval Evaluation | `evaluation_service.py` — Answer Relevancy, Faithfulness, Precision, Recall |
| Anomaly Correlation Analysis | `anomaly_detection.py` — IsolationForest + Pearson correlations |
| Logistics Embedding Reranking | `hybrid_search.py:rerank()` — field-based boost on domain signals |
| LLM-as-Judge | `evaluation_service.py:llm_judge_recommendations()` |
| Token Optimization | `chunking.py:truncate_context()` — tiktoken budget management |
| Supplier Risk Agent | `supplier_risk_agent.py` — tool use, escalation logic |
| Shipment Analysis Agent | `shipment_analysis_agent.py` — route + delay analysis |
| Inventory Intelligence Agent | `inventory_intelligence_agent.py` — stockout risk, demand tools |
| Recommendation Agent | `recommendation_agent.py` — synthesis + proactive alerts |
| A2A Escalation Workflow | `orchestrator.py` — threshold-based cross-agent escalation |
| Supply Chain Dashboard | Frontend + `/api/v1/analytics/dashboard` |
| Front-End Interface | `frontend/` — 5-tab SPA: Search, Recommendations, Agents, Dashboard, Anomalies |

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Dataset

The synthetic dataset (`supply_chain_data.csv`) contains 600 incidents with fields:

| Field | Description |
|---|---|
| `incident_id` | Unique incident identifier |
| `supplier_id` | Supplier code (S001–S020) |
| `warehouse_location` | US warehouse city |
| `region` | Geographic region |
| `incident_type` | Supplier Delay, Port Congestion, Stockout Risk, etc. |
| `product_category` | Electronics, Automotive Parts, etc. |
| `shipment_status` | On-Time / Delayed / Critical Delay / In-Transit / Delivered |
| `severity` | low / medium / high / critical |
| `inventory_level` | Current stock units |
| `delivery_delay` | Days delayed |
| `transportation_cost` | Freight cost USD |
| `order_quantity` | Units ordered |
| `demand_forecast` | Projected demand |
| `resolution_time_days` | Days to resolve |
| `timestamp` | Incident date (2024–2026) |
| `incident_description` | Natural language description for RAG |

Use the [Supply Chain Logistics Dataset](https://www.kaggle.com/) from Kaggle to
replace with real data — ensure the field names match or update `preprocessing.py`.
