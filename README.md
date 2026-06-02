# AI-Powered Supply Chain Risk Intelligence Assistant

An end-to-end supply chain risk intelligence system built with RAG, hybrid search,
multi-agent AI, anomaly detection, and an interactive analytics dashboard.

> **Live stack:** Python 3.13 · FastAPI 0.136 · OpenAI GPT-4o-mini · text-embedding-3-small · Pure-numpy VectorStore · BM25 · IsolationForest · DeepEval

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                      Frontend SPA (HTML/JS)                      │
│  Search · Recommendations · Multi-Agent · Dashboard · Anomalies  │
└───────────────────────────┬──────────────────────────────────────┘
                            │ REST (FastAPI 0.136)
┌───────────────────────────▼──────────────────────────────────────┐
│                    API Layer  /api/v1  (9 endpoints)             │
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
 │  Numpy VectorStore    │
 │  (embeddings.npy +    │
 │   documents.json)     │
 │  + BM25 Index         │
 └────┬──────────────────┘
      │
 ┌────▼──────────────────────────────────────────┐
 │  EmbeddingModel  (auto-probe + fallback)       │
 │  Primary:  text-embedding-3-small  (1536-dim)  │
 │  Fallback: all-MiniLM-L6-v2        (384-dim)   │
 └────┬──────────────────────────────────────────┘
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
│   │   ├── main.py                     # FastAPI entrypoint + lifespan
│   │   ├── core/
│   │   │   ├── config.py               # Settings + make_openai_client()
│   │   │   ├── embeddings.py           # OpenAI API + ST fallback
│   │   │   ├── vector_store.py         # Numpy store + dimension guard
│   │   │   ├── hybrid_search.py        # BM25 + semantic RRF fusion
│   │   │   └── guardrails.py           # Injection detection + relevance
│   │   ├── models/schemas.py           # Pydantic request/response models
│   │   ├── data/
│   │   │   ├── generate_sample.py      # Synthetic 600-record dataset
│   │   │   ├── ingestion.py            # Batch ingestion pipeline
│   │   │   ├── preprocessing.py        # Cleaning + risk enrichment
│   │   │   └── chunking.py             # Row-to-doc + tiktoken counting
│   │   ├── services/
│   │   │   ├── rag_service.py          # RAG pipeline (search + generate)
│   │   │   ├── risk_scoring.py         # 4-dimension weighted scoring
│   │   │   ├── anomaly_detection.py    # IsolationForest + correlations
│   │   │   └── evaluation_service.py   # DeepEval + LLM-as-judge
│   │   ├── agents/
│   │   │   ├── base_agent.py           # Abstract base + tool-use loop
│   │   │   ├── supplier_risk_agent.py
│   │   │   ├── shipment_analysis_agent.py
│   │   │   ├── inventory_intelligence_agent.py
│   │   │   ├── recommendation_agent.py
│   │   │   └── orchestrator.py         # Parallel A2A orchestration
│   │   └── api/routes/
│   │       ├── search.py               # POST /search, /search/hybrid
│   │       ├── recommendations.py      # POST /recommendations
│   │       ├── analytics.py            # GET /dashboard, /anomalies
│   │       └── agents.py               # POST /agents/analyze
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html                      # 5-tab SPA dashboard
│   ├── styles.css
│   └── app.js
├── diagrams/
│   ├── DIAGRAMS.md                     # Mermaid source (GitHub-rendered)
│   ├── diagrams.html                   # Interactive diagram viewer
│   └── FLOW_DOCUMENT.html              # Print-ready A4 document
├── QA_DOCUMENT.html                    # Panel evaluation Q&A (10 criteria)
├── data/                               # supply_chain_data.csv goes here
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Setup

### 1. Prerequisites

- Python 3.11+ (tested on 3.13)
- An OpenAI-compatible API key (OpenAI or gateway)

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY and optionally OPENAI_BASE_URL
```

**Minimum `.env` for a direct OpenAI connection:**
```
OPENAI_API_KEY=sk-...your-key...
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
MAX_TOKENS=4096
```

**Using a custom gateway (e.g. educational keygateway):**
```
OPENAI_API_KEY=learner039
OPENAI_BASE_URL=https://keygateway.arshnivlabs.com/v1
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
MAX_TOKENS=500
```
> The client automatically disables SSL cert verification when `OPENAI_BASE_URL` is set,
> so corporate/educational gateways with non-public CA certificates work out of the box.

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

> **No MSVC / C++ build tools required.** The vector store is pure-numpy. `sentence-transformers`
> is included as an automatic embedding fallback if the OpenAI embeddings endpoint is unreachable.

### 4. Generate Sample Dataset

```bash
cd backend
python -m app.data.generate_sample
```

Creates `backend/data/supply_chain_data.csv` with 600 realistic supply chain incidents.

### 5. Start the Backend

```bash
cd backend
uvicorn app.main:app --port 8000
```

On first startup the server:
1. Probes the OpenAI embeddings endpoint (→ falls back to local `all-MiniLM-L6-v2` if unreachable)
2. Ingests all 600 incidents in batches of 100
3. Builds the BM25 in-memory index
4. Serves requests on `http://localhost:8000`

> **Embedding model change?** The vector store detects a model or dimension mismatch on startup
> and automatically clears and re-indexes — no manual intervention needed.

### 6. Open the Frontend

Open `frontend/index.html` directly in a browser (no server needed), or:

```bash
cd frontend && python -m http.server 3000
```

Visit `http://localhost:3000` — the health badge in the header turns green when the server is ready.

---

## Docker (Full Stack)

```bash
cp .env.example .env   # fill in OPENAI_API_KEY
docker-compose up --build

# Backend:  http://localhost:8000
# Frontend: http://localhost:3000
# Swagger:  http://localhost:8000/docs
```

---

## API Usage Examples

### Hybrid Incident Search

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

### Multi-Agent Analysis (with A2A Escalation)

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

### Force Re-indexing (after data or model change)

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
| Basic RAG | `rag_service.py` — retrieve → token-budget → GPT-4o-mini generation |
| Hybrid Search | `hybrid_search.py` — BM25 + semantic via Reciprocal Rank Fusion |
| Semantic Search | `vector_store.py` — cosine similarity, numpy-based |
| Metadata Filtering | `$where` filters on supplier, warehouse, severity, status, incident_type |
| Risk Recommendation Engine | `risk_scoring.py` + `rag_service.py` |
| Input Validation Guardrails | `guardrails.py` — injection detection, domain relevance scoring |
| Incident Similarity Ranking | RRF fusion + logistics-aware field-match reranker |
| Recommendation Generation | GPT-4o-mini with structured PRIORITY 1-5 output format |
| API Endpoints | FastAPI 9 endpoints, Swagger at `/docs`, ReDoc at `/redoc` |

### Requirement 2 — Advanced

| Feature | Implementation |
|---|---|
| DeepEval Evaluation | `evaluation_service.py` — Answer Relevancy, Faithfulness, Precision, Recall |
| Anomaly Correlation Analysis | `anomaly_detection.py` — IsolationForest + Pearson correlations |
| Logistics Embedding Reranking | `hybrid_search.py:rerank()` — field-match domain boost |
| LLM-as-Judge | `evaluation_service.py:llm_judge_recommendations()` — 5-dimension scoring |
| Token Optimization | `chunking.py:truncate_context()` — tiktoken budget management |
| Supplier Risk Agent | `supplier_risk_agent.py` — GPT-4o-mini tool use + escalation |
| Shipment Analysis Agent | `shipment_analysis_agent.py` — route + delay root cause analysis |
| Inventory Intelligence Agent | `inventory_intelligence_agent.py` — stockout risk + demand tools |
| Recommendation Agent | `recommendation_agent.py` — synthesis + proactive alerts |
| A2A Escalation Workflow | `orchestrator.py` — threshold-based cross-agent escalation chain |
| Supply Chain Dashboard | Frontend + `GET /api/v1/analytics/dashboard` |
| Front-End Interface | `frontend/` — 5-tab SPA (zero-dependency, no build step) |

---

## Fallback Mechanisms

The system is designed to degrade gracefully rather than fail hard:

| Layer | Trigger | Fallback |
|---|---|---|
| **Embedding model** | OpenAI `/embeddings` endpoint unreachable | Local `all-MiniLM-L6-v2` (384-dim, no API needed) |
| **Vector store** | Embedding model/dimension changed | Auto-clear stale index + re-ingest on startup |
| **LLM parsing** | No `PRIORITY` blocks in GPT response | First 5 lines wrapped as generic recommendations |
| **DeepEval** | Library not installed / API error | Placeholder scores (0.70–0.80) with note |
| **Agent execution** | Agent timeout (>60s) or crash | Stub result (risk=0.0, `"Manual review required"`) |
| **Agent selection** | No query keywords matched | Run all 3 specialist agents (safe default) |
| **BM25 index** | Index not yet built | Auto-rebuild from vector store corpus |
| **Server startup** | Dataset file not found | Server starts with empty store (search returns `[]`) |
| **Data preprocessing** | Missing or malformed CSV fields | `fillna(0)` for numerics, `"Unknown"` for strings |

---

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | — | **Yes** | OpenAI API key or gateway key |
| `OPENAI_BASE_URL` | `None` | No | Custom gateway URL (SSL verify auto-disabled) |
| `LLM_MODEL` | `gpt-4o-mini` | No | OpenAI model for generation + agents |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | No | OpenAI embedding model (falls back to ST) |
| `MAX_TOKENS` | `500` | No | Max tokens per LLM call (set ≤ 500 for gateways) |
| `CHROMA_PERSIST_DIRECTORY` | `./chroma_db` | No | Vector store persist path |
| `CHROMA_BASE_DIR` | `./chroma_sessions` | No | Session-scoped store root |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | No | See fallback section above |
| `TOP_K_RESULTS` | `10` | No | Default search top-k |
| `HYBRID_ALPHA` | `0.5` | No | Semantic weight in RRF (0=BM25 only, 1=semantic only) |
| `DATA_PATH` | `./data/supply_chain_data.csv` | No | Dataset file path |
| `ANOMALY_CONTAMINATION` | `0.05` | No | IsolationForest contamination rate |

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Dataset

The synthetic dataset (`supply_chain_data.csv`) — 600 incidents, 16 fields:

| Field | Description |
|---|---|
| `incident_id` | Unique identifier (`INC00001`–`INC00600`) |
| `supplier_id` | Supplier code (`S001`–`S020`) |
| `warehouse_location` | US city (12 locations) |
| `region` | Geographic region |
| `incident_type` | Supplier Delay · Port Congestion · Stockout Risk · etc. (8 types) |
| `product_category` | Electronics · Automotive Parts · etc. (8 categories) |
| `shipment_status` | On-Time / Delayed / Critical Delay / In-Transit / Delivered |
| `severity` | low / medium / high / critical |
| `inventory_level` | Current stock units |
| `delivery_delay` | Days delayed |
| `transportation_cost` | Freight cost (USD) |
| `order_quantity` | Units ordered |
| `demand_forecast` | Projected demand |
| `resolution_time_days` | Days to resolve |
| `timestamp` | Incident date (2024–2026) |
| `incident_description` | Natural language description (**primary RAG field**) |

To use real data, replace `data/supply_chain_data.csv` with the
[Supply Chain Logistics Dataset](https://www.kaggle.com/) — update field names in `preprocessing.py` if needed.
