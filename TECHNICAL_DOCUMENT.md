# Technical Document
# AI-Powered Supply Chain Risk Intelligence Assistant

**Version:** 1.1.0  
**Date:** 2026-06-02  
**Stack:** Python 3.13 · FastAPI 0.136 · OpenAI GPT-4o-mini · text-embedding-3-small · Pure-Numpy VectorStore · BM25 · DeepEval · scikit-learn

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Data Layer](#4-data-layer)
5. [Core Infrastructure Services](#5-core-infrastructure-services)
6. [RAG Pipeline](#6-rag-pipeline)
7. [Risk Intelligence Services](#7-risk-intelligence-services)
8. [Multi-Agent Architecture](#8-multi-agent-architecture)
9. [Evaluation Framework](#9-evaluation-framework)
10. [API Design](#10-api-design)
11. [Frontend Architecture](#11-frontend-architecture)
12. [Design Decisions & Trade-offs](#12-design-decisions--trade-offs)
13. [Deployment](#13-deployment)
14. [Security Considerations](#14-security-considerations)
15. [Project File Structure](#15-project-file-structure)

---

## 1. Executive Summary

### Problem Statement

Global supply chains involve thousands of concurrent events — supplier delays, port congestion, inventory shortages, transportation bottlenecks, and demand fluctuations. Operations teams struggle to synthesize this distributed information into actionable intelligence because data is fragmented across procurement systems, logistics platforms, and warehouse records.

### Solution

The AI-Powered Supply Chain Risk Intelligence Assistant is an end-to-end microservice that enables operations teams to:

- **Query** historical supply chain incidents using natural language
- **Retrieve** semantically similar past disruptions via hybrid search
- **Score** operational risk across supplier, inventory, shipment, and demand dimensions
- **Generate** explainable, prioritized mitigation recommendations via a RAG pipeline
- **Analyze** risks in parallel across four specialized AI agents
- **Detect** statistical anomalies in operational data
- **Visualize** KPIs through an interactive analytics dashboard

### Key Design Principles

| Principle | Application |
|---|---|
| **Modularity** | Each layer (data, search, agents, API) is independently replaceable |
| **Explainability** | Every recommendation traces back to retrieved historical evidence |
| **Token Efficiency** | Context windows are budget-managed before LLM calls |
| **Resilience** | Agent failures are isolated; the orchestrator continues with partial results |
| **Extensibility** | New agents, datasets, and search strategies plug in without core changes |

---

## 2. System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (SPA)                                    │
│         Search │ Recommendations │ Multi-Agent │ Dashboard │ Anomalies      │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ HTTP / REST
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI APPLICATION                                  │
│                         /api/v1  (9 endpoints)                              │
├──────────────┬────────────────────┬──────────────────┬──────────────────────┤
│  /search     │  /recommendations  │  /agents/analyze │  /analytics          │
└──────┬───────┴────────┬───────────┴────────┬─────────┴──────────┬───────────┘
       │                │                    │                    │
       ▼                ▼                    ▼                    ▼
┌──────────────┐ ┌─────────────┐  ┌──────────────────┐ ┌───────────────────┐
│  RAG Service │ │  RAG Service│  │   Orchestrator   │ │ Analytics Service │
│  (search)    │ │  (generate) │  │  (multi-agent)   │ │ (dashboard/       │
└──────┬───────┘ └──────┬──────┘  └─────────┬────────┘ │  anomalies)       │
       │                │                   │          └───────────────────┘
       ▼                ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CORE SERVICES LAYER                                     │
├──────────────────┬──────────────────┬───────────────┬──────────────────────┤
│  HybridSearch    │   RiskScoring    │  GuardRails   │   TokenOptimizer     │
│  (BM25+Semantic) │   (multi-dim)    │  (validation) │   (tiktoken)         │
└──────────────────┴──────────────────┴───────────────┴──────────────────────┘
       │                                               │
       ▼                                               ▼
┌────────────────────────┐              ┌──────────────────────────────────┐
│   NUMPY VECTOR STORE   │              │   OPENAI GPT-4o-mini (via GW)    │
│   embeddings.npy       │              │   - Recommendation generation    │
│   documents.json       │              │   - Multi-agent tool use         │
│   BM25 Index           │              │   - LLM-as-judge evaluation      │
└────────────┬───────────┘              └──────────────────────────────────┘
             │
             ▼
┌────────────────────────┐
│   DATA LAYER           │
│   supply_chain_data.csv│
│   Preprocessing        │
│   Chunking (tiktoken)  │
└────────────────────────┘
```

### Request Lifecycle — Recommendation Flow

```
User Query
    │
    ▼
[1] Guardrails (injection check, relevance score)
    │
    ▼
[2] Sanitize query
    │
    ▼
[3] Hybrid Search (BM25 + Semantic → RRF → Rerank)
    │  top_k=8 candidate incidents
    ▼
[4] Token Budget Management (truncate_context, max 8000 tokens)
    │  trimmed context docs
    ▼
[5] Risk Scoring (supplier/inventory/shipment/demand dimensions)
    │  RiskScore object
    ▼
[6] Prompt Assembly (system prompt + risk context + user query)
    │
    ▼
[7] OpenAI GPT-4o-mini Call (chat.completions, max_tokens=500)
    │  raw LLM response
    ▼
[8] Response Parsing (extract recommendations, summary)
    │
    ▼
[9] Optional: LLM-as-Judge / DeepEval scoring
    │
    ▼
RecommendationResponse → API → Frontend
```

### Request Lifecycle — Multi-Agent Flow

```
User Query
    │
    ▼
[1] Guardrails + Sanitize
    │
    ▼
[2] Agent Selection (keyword routing or include_all_agents=true)
    │
    ▼
[3] Context Retrieval (Hybrid Search, top_k=10)
    │
    ├─────────────────────────────────────────────┐
    ▼                                             ▼
[4a] ThreadPoolExecutor (max_workers=3)           │
    ├── SupplierRiskAgent.analyze()               │
    ├── ShipmentAnalysisAgent.analyze()           │
    └── InventoryIntelligenceAgent.analyze()      │
                                                  │
    ◄─────────────────────────────────────────────┘
    ▼
[5] A2A Escalation Check (risk_score > 0.7)
    │  Optional: escalation_chain entries
    ▼
[6] RecommendationAgent.analyze(findings from all agents)
    │  synthesized result
    ▼
[7] Consolidate: weighted risk, merged recs, proactive alerts
    │
    ▼
OrchestratorResponse → API → Frontend
```

---

## 3. Technology Stack

### Backend

| Component | Library | Version | Purpose |
|---|---|---|---|
| Web Framework | FastAPI | 0.136.3 | REST API, OpenAPI docs (upgraded for starlette 1.x compat) |
| ASGI Server | Uvicorn | 0.30.6 | Production ASGI server |
| LLM Provider | OpenAI SDK | 1.55.3 | GPT-4o-mini via custom gateway (SSL-disabled client) |
| Vector Store | Pure NumPy | 2.2.3 | `embeddings.npy` + `documents.json` — no C++ build tools |
| Embedding — Primary | OpenAI API | — | `text-embedding-3-small` · 1536-dim · via gateway |
| Embedding — Fallback | Sentence-Transformers | 3.3.1 | `all-MiniLM-L6-v2` · 384-dim · local · auto-probe fallback |
| Keyword Search | rank-bm25 | 0.2.2 | BM25Okapi sparse retrieval, in-memory |
| Data Processing | Pandas / NumPy | 2.2.3 / 2.2.3 | CSV ingestion, feature engineering |
| Anomaly Detection | scikit-learn | 1.6.1 | IsolationForest, StandardScaler |
| Evaluation | DeepEval | optional | RAG quality metrics (graceful placeholder if absent) |
| Schema Validation | Pydantic v2 | 2.9.2 | Request/response models, field validation |
| Configuration | pydantic-settings | 2.6.1 | `.env` loading + `make_openai_client()` factory |
| Token Counting | tiktoken | 0.8.0 | `cl100k_base` tokenizer, context budget management |
| Synthetic Data | Faker | 30.3.0 | Dataset generation utilities |
| Testing | pytest | 8.3.3 | Unit tests — no API key needed (mocked LLM calls) |

### Frontend

| Component | Technology | Purpose |
|---|---|---|
| UI Framework | Vanilla HTML5/CSS3/JS | Zero-dependency SPA, no build step |
| Styling | Custom CSS (CSS variables) | Dark theme dashboard with responsive grid |
| HTTP Client | Native `fetch()` | Async API calls |
| Charts | CSS-based progress bars | Risk score visualization |

### Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| Containerization | Docker + Dockerfile | Reproducible backend build |
| Orchestration | Docker Compose | Multi-service local deployment |
| Static Serving | Nginx Alpine | Frontend file serving in Docker |
| Environment | `.env` / `.env.example` | Secret management via env vars |

---

## 4. Data Layer

### 4.1 Dataset

**File:** `data/supply_chain_data.csv`  
**Records:** 600 synthetic supply chain incidents (2024–2026)  
**Generator:** `backend/app/data/generate_sample.py`

#### Schema

| Field | Type | Description |
|---|---|---|
| `incident_id` | string | Unique identifier `INC00001`–`INC00600` |
| `supplier_id` | string | Supplier code `S001`–`S020` |
| `warehouse_location` | string | US city/state (12 locations) |
| `region` | string | Geographic grouping (Northeast, South, West, etc.) |
| `incident_type` | string | One of 8 incident categories |
| `product_category` | string | One of 8 product categories |
| `shipment_status` | string | On-Time / Delayed / Critical Delay / In-Transit / Delivered |
| `severity` | string | low / medium / high / critical |
| `inventory_level` | float | Current stock in units (0–1000+) |
| `delivery_delay` | float | Days delayed (0–30+, exponential distribution) |
| `transportation_cost` | float | Freight cost in USD (100–5000+, normal distribution) |
| `order_quantity` | integer | Units ordered (normal distribution) |
| `demand_forecast` | integer | Projected demand (±40% of order quantity) |
| `resolution_time_days` | integer | Days to resolve the incident |
| `timestamp` | date | Incident date (uniformly distributed 2024–2026) |
| `incident_description` | text | Natural language description (**primary RAG field**) |

#### Incident Types and Generation Logic

```
Supplier Delay       → higher delivery_delay (exponential × 2)
Port Congestion      → elevated delivery_delay, higher transport cost
Stockout Risk        → critically low inventory_level (exponential × 0.3)
Transportation Issue → variable transport cost spike
Demand Spike         → demand_forecast >> inventory_level
Quality Issue        → random delay for inspection/rework
Weather Disruption   → delay spike with regional focus
Customs Delay        → administrative delay pattern
```

#### Severity Assignment Formula

```python
def severity_from_delay(delay, inv_level, status):
    if status == "Critical Delay" or delay > 14 or inv_level < 50:
        return "critical"
    elif delay > 7 or inv_level < 150:
        return "high"
    elif delay > 3 or inv_level < 300:
        return "medium"
    return "low"
```

### 4.2 Preprocessing Pipeline

**File:** `backend/app/data/preprocessing.py`

The preprocessing pipeline performs five operations:

1. **Load and Validate** — CSV loaded via Pandas; required columns checked (`supplier_id`, `incident_description`)
2. **Type Coercion** — Numeric fields coerced with `pd.to_numeric(..., errors='coerce').fillna(0)`
3. **String Normalization** — Categorical fields stripped, null-filled with `"Unknown"`
4. **Deduplication** — Rows deduplicated by `incident_id`
5. **Risk Score Enrichment** — Computed `risk_score` column added before indexing

**Risk Score Formula (row-level):**
```
score = delay_component + inventory_component + status_component + severity_component
delay_component:     0.4 if delay>14 | 0.3 if >7 | 0.2 if >3 | 0.1 if >0
inventory_component: 0.3 if inv<50  | 0.2 if <150 | 0.1 if <300
status_component:    0.2 if Critical Delay | 0.1 if Delayed
severity_component:  low=0.0 | medium=0.1 | high=0.2 | critical=0.3
```

Additional derived fields:
- `inventory_turnover` = `inventory_level / order_quantity`
- `delay_ratio` = `delivery_delay / resolution_time_days`

### 4.3 Document Chunking

**File:** `backend/app/data/chunking.py`

Each CSV row is converted to a **single structured document** — not split further — because each row represents a complete incident with bounded text length.

**Document assembly (`row_to_document`):**

```
[incident_description]
Incident Type: [type]. Supplier: [id]. Warehouse: [location].
Region: [region]. Status: [status]. Severity: [severity].
Delivery Delay: [N] days. Inventory Level: [N] units.
Transportation Cost: $[N]. Product Category: [cat]. Date: [date]
```

This structured format ensures that:
- The description provides semantic richness for dense retrieval
- Metadata fields appear verbatim for BM25 keyword matching
- The full document is self-contained for LLM context

**Token counting** uses `tiktoken` with `cl100k_base` encoding (same tokenizer as GPT-4). Token count is stored in metadata for downstream budget management.

### 4.4 Ingestion Pipeline

**File:** `backend/app/data/ingestion.py`

```
CSV file
   │
   ├── load_and_clean()     → cleaned DataFrame
   ├── enrich_dataframe()   → adds risk_score, inventory_turnover
   ├── dataframe_to_documents() → List[{id, content, metadata}]
   │
   └── Batch ingestion (100 docs/batch)
       ├── encode(texts)    → embeddings via OpenAI API (or ST fallback)
       └── add_documents()  → upsert to numpy vector store
```

**Idempotency:** Ingestion checks `vector_store.count() > 0` before running. Use `force_rebuild=True` to re-index from scratch.

**Startup auto-ingestion:** `main.py` lifespan hook calls `pipeline.ingest()` on server start if the store is empty.

**Embedding model change detection:** `VectorStore` stores `store_meta.json` with the active model name and dimension. On startup, if the stored model/dimension doesn't match the configured model, the store is automatically cleared and re-indexed.

---

## 5. Core Infrastructure Services

### 5.1 Embedding Model

**File:** `backend/app/core/embeddings.py`

The embedding model uses an **auto-probe + fallback** strategy at startup:

```
Startup
  │
  ├─ Probe: call OpenAI /embeddings with ["probe"]
  │   ├─ Success → use text-embedding-3-small  (1536-dim, via gateway)
  │   └─ Failure → load all-MiniLM-L6-v2 locally  (384-dim, no API needed)
```

| Property | Primary (OpenAI) | Fallback (SentenceTransformers) |
|---|---|---|
| Model | `text-embedding-3-small` | `all-MiniLM-L6-v2` |
| Dimension | 1536 | 384 |
| Source | OpenAI API via gateway | Local disk (~80 MB) |
| Batch size | 100 texts/request | 64 texts/CPU batch |
| Normalisation | L2 (client-side) | L2 (normalize_embeddings=True) |

**Gateway SSL:** `make_openai_client()` passes `httpx.Client(verify=False)` when `OPENAI_BASE_URL` is set — necessary for corporate/educational gateways whose TLS certificate is signed by a non-public CA (`certifi` does not trust it, but the system curl store does).

**Singleton pattern:** `EmbeddingModel` uses `__new__` — the probe runs exactly once per process, then `_initialised = True` prevents re-running.

### 5.2 Vector Store (Pure NumPy)

**File:** `backend/app/core/vector_store.py`

The vector store is implemented entirely in NumPy — no C++ build tools required (ChromaDB was replaced due to Python 3.13 + Windows MSVC compilation constraints).

**Persistence:**
```
./chroma_db/
  ├── embeddings.npy      # float32 array [N × D]
  ├── documents.json      # list of {id, content, metadata}
  └── store_meta.json     # {"embedding_model": "text-embedding-3-small"}
```

**Cosine similarity (batch):**
```python
q_norm = q / (||q|| + ε)
embs_normed = embs / (||embs|| + ε)
scores = embs_normed @ q_norm   # vectorised dot product
```

**Model compatibility guard (`_check_model_compatibility`):**
Two-step check on every startup:
1. Model name: `store_meta.json["embedding_model"]` vs `settings.EMBEDDING_MODEL`
2. Dimension: `embeddings.npy.shape[1]` vs known dims (`text-embedding-3-small=1536`, `all-MiniLM-L6-v2=384`)

If either mismatches → all store files deleted → server triggers re-ingestion on next request.

**Metadata filtering:** Python-native `$eq`, `$ne`, `$and`, `$or` operators — same interface as the original ChromaDB `$where` syntax, applied as list comprehension over `documents.json`.

**Upsert semantics:** `add_documents()` checks `_id_to_idx` — existing documents are overwritten in-place; new documents are appended.

### 5.3 Hybrid Search Engine

**File:** `backend/app/core/hybrid_search.py`

The hybrid search combines two fundamentally different retrieval strategies and merges them using **Reciprocal Rank Fusion (RRF)**.

#### BM25 (Sparse Retrieval)

- Library: `rank_bm25.BM25Okapi`
- Tokenization: lowercase whitespace splitting
- Index built in-memory from the full ChromaDB corpus on startup
- Strengths: exact keyword matching, supplier IDs, incident types, warehouse names
- Weaknesses: vocabulary mismatch (synonyms, paraphrasing)

**BM25Okapi scoring formula:**
```
BM25(q, d) = Σ IDF(qᵢ) × (f(qᵢ, d) × (k1 + 1)) / (f(qᵢ, d) + k1 × (1 - b + b × |d|/avgdl))

where: k1 = 1.5, b = 0.75 (BM25Okapi defaults)
```

#### Semantic Search (Dense Retrieval)

- Query encoded via `all-MiniLM-L6-v2` (384-dim L2-normalized vector)
- ChromaDB HNSW ANN search over the embedded corpus
- Score = `1 - cosine_distance` (range: 0–1, higher = more similar)
- Strengths: conceptual similarity, paraphrasing, domain synonyms
- Weaknesses: exact entity matching (supplier IDs, cost figures)

#### Reciprocal Rank Fusion (RRF)

RRF merges rankings from both strategies without requiring score normalization:

```python
RRF_score(doc, k=60) = α × 1/(k + rank_semantic) + (1-α) × 1/(k + rank_bm25)
```

Where:
- `α = HYBRID_ALPHA` (default 0.5, configurable via `.env`)
- `k = 60` (standard RRF constant, reduces sensitivity to top-rank dominance)
- Final ranking: documents sorted by descending RRF score

**Why RRF over score normalization?** BM25 scores are unnormalized (range varies with corpus), making direct combination unreliable. RRF operates purely on rank positions, making it robust to scale differences.

#### Logistics-Aware Reranker

After RRF, a lightweight reranker applies domain-specific boosts:

```python
boost += 0.05 for each metadata field (incident_type, severity,
         warehouse_location, supplier_id, product_category)
         whose value appears verbatim in the query string
```

This ensures that exact entity mentions (e.g., `"supplier S003"`, `"critical"`, `"Chicago"`) surface to the top of the final ranked list.

### 5.4 Input Validation & Guardrails

**File:** `backend/app/core/guardrails.py`

Three-layer validation applied to every incoming query:

**Layer 1 — Format Validation**
```
- Minimum length: 3 characters
- Maximum length: 1000 characters
- Non-empty after strip
```

**Layer 2 — Injection Detection**

Regular expression patterns block prompt injection attempts and other adversarial inputs:
```
"ignore/disregard all previous instructions"
"system prompt"
"jailbreak"
"act as if"
<script> tags (XSS)
SQL keywords (SELECT/INSERT/DROP/etc.)
Shell commands (rm -rf, exec())
```

**Layer 3 — Supply Chain Relevance Scoring**

A keyword match score ensures queries are domain-relevant before consuming LLM tokens:
```python
SUPPLY_CHAIN_KEYWORDS = [
    "supplier", "shipment", "delivery", "warehouse", "inventory",
    "logistics", "transport", "freight", "port", "delay", ...
]
confidence = min(matched_keywords / 3.0, 1.0)
is_relevant = confidence >= 0.33  # at least 1 keyword match
```

**Sanitization:** Removes extra whitespace, special characters (`<>{}|\\^` \``) that could interfere with prompt construction.

---

## 6. RAG Pipeline

**File:** `backend/app/services/rag_service.py`

### 6.1 Pipeline Stages

```
Stage 1: Validate + Sanitize query
Stage 2: Hybrid Search (top_k × 2 candidates)
Stage 3: Rerank (logistics-aware boost → top_k final)
Stage 4: Token Budget Management (truncate to max_context_tokens)
Stage 5: Risk Score Computation (multi-dimensional)
Stage 6: Prompt Assembly
Stage 7: LLM Generation (GPT-4o)
Stage 8: Response Parsing
```

### 6.2 Token Budget Management

**File:** `backend/app/data/chunking.py` — `truncate_context()`

Before constructing the LLM prompt, retrieved documents are trimmed to stay within `MAX_CONTEXT_TOKENS = 8000` tokens:

```python
def truncate_context(documents, max_tokens=6000):
    selected = []
    used_tokens = 0
    for doc in documents:          # documents already ranked by relevance
        tokens = doc["metadata"]["token_count"]
        if used_tokens + tokens > max_tokens:
            break                   # budget exhausted — stop here
        selected.append(doc)
        used_tokens += tokens
    return selected
```

This ensures the highest-ranked, most relevant documents always fit within the context window, preventing `context_length_exceeded` errors with large corpora.

### 6.3 Prompt Engineering

The recommendation prompt is structured to elicit consistently formatted responses:

```
System: [Supply chain risk analyst persona — cached]

User:
Supply Chain Risk Analysis Request
Query: [user's query]

Risk Assessment:
- Overall Risk Score: [X%]
- Risk Level: [CRITICAL/HIGH/MEDIUM/LOW]
- Supplier/Inventory/Shipment Risk breakdown
- Key Risk Factors: [top 3]

Historical Context (Similar Incidents):
[Incident 1] [description]
  Severity: X | Type: Y | Delay: N days | Inventory: N units
...

Please provide:
1. A brief summary (2-3 sentences)
2. Exactly 5 prioritized recommendations, each formatted as:
   PRIORITY [1-5]: [Action]
   Timeline: [Immediate/24h/Week/Month]
   Owner: [Role/Team]
   Expected Impact: [Specific outcome]
```

The strict output format enables deterministic parsing via regex without JSON mode.

### 6.4 Response Parsing

`_parse_recommendations()` uses a two-pass regex strategy:
1. **Primary:** Match `PRIORITY [N]: ... Timeline: ... Owner: ... Expected Impact: ...` blocks
2. **Fallback:** If no structured blocks found, extract first 5 non-empty lines as plain actions

`_extract_summary()` extracts lines before the first `PRIORITY` keyword as the executive summary.

---

## 7. Risk Intelligence Services

### 7.1 Multi-Dimensional Risk Scoring

**File:** `backend/app/services/risk_scoring.py`

Risk is scored across four independent dimensions, each computed from the retrieved incident set:

#### Supplier Risk (weight: 35%)
```
avg_delay > 14 days → 0.9
avg_delay > 7 days  → 0.65
avg_delay > 3 days  → 0.40
avg_delay > 0 days  → 0.15
```

#### Inventory Risk (weight: 30%)
```
avg_inventory < 50 units   → 0.95  (critical stockout)
avg_inventory < 150 units  → 0.70  (safety stock breach)
avg_inventory < 300 units  → 0.40  (approaching threshold)
avg_inventory ≥ 300 units  → 0.15  (adequate)
```

#### Shipment Risk (weight: 25%)
```
delayed_ratio > 60%  → 0.85
delayed_ratio > 30%  → 0.55
delayed_ratio ≤ 30%  → 0.20
```

#### Demand Risk (weight: 10%)
```
avg_cost > $3,000  → 0.70  (transportation cost spike)
avg_cost > $2,000  → 0.45  (elevated costs)
avg_cost ≤ $2,000  → 0.20  (normal range)
```

#### Severity Multiplier
```
critical incidents present → × 1.2
>1 high severity incidents → × 1.1
```

#### Overall Score Formula
```
overall = min(
    (supplier_risk × 0.35 + inventory_risk × 0.30 +
     shipment_risk × 0.25 + demand_risk × 0.10) × severity_mult,
    1.0
)
```

#### Risk Level Thresholds
```
≥ 0.75 → CRITICAL
≥ 0.50 → HIGH
≥ 0.25 → MEDIUM
< 0.25 → LOW
```

### 7.2 Anomaly Detection

**File:** `backend/app/services/anomaly_detection.py`

#### IsolationForest Algorithm

IsolationForest detects anomalies by measuring how easily a data point can be isolated from the rest of the dataset using random binary trees:

```
anomaly_score ∝ 1 / average_path_length_to_isolation
```

Points requiring fewer splits to isolate are more anomalous.

**Configuration:**
```python
IsolationForest(
    n_estimators=100,    # number of isolation trees
    contamination=0.05,  # expected fraction of anomalies (configurable)
    random_state=42
)
```

**Feature Matrix:** Five numeric features, StandardScaler normalized before fitting:
```
[delivery_delay, inventory_level, transportation_cost,
 order_quantity, demand_forecast]
```

#### Anomaly Feature Attribution

For each detected anomaly, individual features contributing to the anomalous score are identified by Z-score:
```python
z_score = |feature_value - population_mean| / population_std
if z_score > 2.5: flag as anomalous
```

#### Correlation Analysis

Four Pearson correlation insights are computed post-detection:

| Correlation | Threshold | Insight |
|---|---|---|
| delay ↔ transport_cost | |r| > 0.30 | Delays coincide with cost spikes |
| inventory ↔ delay | |r| > 0.20 | Stockout risk grows with delays |
| demand ↔ transport_cost | |r| > 0.25 | Peak demand strains capacity |
| High delay frequency | > 20% | Systemic delay pattern |

---

## 8. Multi-Agent Architecture

### 8.1 Agent Design Pattern

**File:** `backend/app/agents/base_agent.py`

All agents inherit from `BaseSupplyChainAgent`, which provides:

```
AbstractMethods (subclasses must implement):
  system_prompt → str          Agent-specific LLM persona
  tools         → List[Dict]   OpenAI function-calling tool schemas
  analyze()     → AgentResult  Core analysis logic

Concrete Methods (shared):
  client        → OpenAI        Lazy-initialized singleton client
  _call_llm()                   LLM call with tool-use loop
  _handle_tool_call()           Tool dispatch (overridable)
  _build_context_summary()      Context formatting helper
```

#### Tool Use Pattern (OpenAI Function Calling)

```
[1] Build messages: [system, user]
[2] call chat.completions.create(tools=..., tool_choice="auto")
[3] if response.choices[0].message.tool_calls:
      for each tool_call:
        result = _handle_tool_call(name, json.loads(arguments))
        append tool_result message
      [4] second LLM call with tool results in context
[5] return final message.content
```

#### Output Format Contract

All agents structure their LLM output identically for deterministic parsing:

```
RISK_SCORE: [0.0-1.0]
FINDINGS:
- [finding 1]
- [finding 2]
RECOMMENDATIONS:
- [action 1]
- [action 2]
ESCALATE: [YES/NO]
```

### 8.2 Specialized Agents

#### Supplier Risk Agent
**File:** `backend/app/agents/supplier_risk_agent.py`

| Property | Value |
|---|---|
| Focus | Supplier delivery performance, SLA compliance, single-source dependency |
| Tool | `get_supplier_history(supplier_id, metric)` |
| Escalation Trigger | Risk score > 0.7 |
| Key Metrics Analyzed | Average delay, on-time delivery rate, incident frequency |

#### Shipment Analysis Agent
**File:** `backend/app/agents/shipment_analysis_agent.py`

| Property | Value |
|---|---|
| Focus | Route disruptions, port congestion, carrier capacity, customs delays |
| Tool | `get_route_status(origin, destination, transport_mode)` |
| Escalation Trigger | Critical delay patterns detected |
| Key Metrics Analyzed | Delay ratio, status distribution, transit time variance |

#### Inventory Intelligence Agent
**File:** `backend/app/agents/inventory_intelligence_agent.py`

| Property | Value |
|---|---|
| Focus | Stockout prediction, safety stock adequacy, demand-supply gaps |
| Tools | `check_inventory_levels(warehouse, product)` + `get_demand_forecast(product, horizon)` |
| Escalation Trigger | Any warehouse at critical stockout risk (< 50 units) |
| Key Metrics Analyzed | Inventory level vs demand forecast, days of supply, replenishment lead time |

#### Recommendation Agent
**File:** `backend/app/agents/recommendation_agent.py`

| Property | Value |
|---|---|
| Focus | Cross-agent synthesis, conflict resolution, proactive alerting |
| Tools | None (synthesis-only) |
| Escalation Trigger | Consolidated risk > 0.85 triggers director-level escalation |
| Input | `agent_findings: List[AgentResult]` from all specialist agents |

The Recommendation Agent receives serialized findings from all three specialist agents and synthesizes:
1. A consolidated risk narrative
2. Cross-cutting mitigation strategies
3. Proactive disruption alerts (`PROACTIVE_ALERTS:` section)
4. Business continuity elements

### 8.3 Multi-Agent Orchestrator

**File:** `backend/app/agents/orchestrator.py`

#### Parallel Execution

Specialist agents run concurrently via `ThreadPoolExecutor` (max_workers=3):

```python
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(agent.analyze, query, context, **kwargs): agent_type
        for agent_type, agent in agent_map.items()
        if agent_type in selected_agents
    }
    for future in as_completed(futures):
        result = future.result(timeout=60)
```

Wall-clock time ≈ slowest single agent, not sum of all agents.

**Error isolation:** If one agent raises an exception, it returns a stub `AgentResult` with `risk_score=0.0` rather than crashing the entire analysis.

#### Agent Selection (Query Routing)

When `include_all_agents=False`, the orchestrator routes based on query keywords:

```
"supplier" / "vendor" / "delivery"     → SupplierRiskAgent
"shipment" / "port" / "transport"      → ShipmentAnalysisAgent
"inventory" / "stock" / "demand"       → InventoryIntelligenceAgent
```

No keyword match → all agents invoked (safe fallback).

#### A2A (Agent-to-Agent) Escalation Workflow

```
[1] After parallel phase, check: any agent.escalated == True?
[2] For each escalated agent:
      chain_entry = "{AgentName} → RecommendationAgent: {reason}"
      append to escalation_chain
[3] If avg(escalated_risk_scores) > 0.85:
      chain_entry += "RecommendationAgent → Operations Director: ..."
[4] RecommendationAgent receives escalation signals in its findings context
[5] OrchestratorResponse.escalation_chain returned to client
```

#### Risk Consolidation

Weighted average across specialist agents (by agent type):

```
supplier_risk:        weight = 0.35
shipment_analysis:    weight = 0.30
inventory_intelligence: weight = 0.35
```

---

## 9. Evaluation Framework

**File:** `backend/app/services/evaluation_service.py`

### 9.1 DeepEval RAG Metrics

Four standard RAG evaluation metrics are computed via DeepEval when `evaluate_quality=true`:

| Metric | What It Measures | Threshold |
|---|---|---|
| **Answer Relevancy** | Does the generated response answer the query? | 0.5 |
| **Faithfulness** | Are the claims in the response grounded in the retrieved context? | 0.5 |
| **Contextual Precision** | Are retrieved documents relevant to the ground truth? | 0.5 |
| **Contextual Recall** | Does the retrieved context cover all necessary information? | 0.5 |

DeepEval uses the configured LLM (GPT-4o-mini) as the judge internally. It is an **optional dependency** — if not installed or configured, the system returns placeholder scores (0.70–0.80) without failing.

**Graceful degradation:** If DeepEval is not configured (missing `OPENAI_API_KEY` in DeepEval's internal config), the service returns placeholder scores with a note rather than failing.

### 9.2 LLM-as-Judge

The system implements its own LLM judge for recommendation quality, independent of DeepEval:

**Judge Dimensions (0–10 each):**

| Dimension | Description |
|---|---|
| **Relevance** | How relevant are the recommendations to the stated risk? |
| **Actionability** | How specific and immediately implementable are they? |
| **Completeness** | Do they address all major risk dimensions? |
| **Feasibility** | Are timelines and owners realistic? |
| **Evidence-Based** | Are recommendations grounded in the historical incident data? |

**Judge Output:**
```
RELEVANCE: 8/10 - Recommendations directly address port congestion risk
ACTIONABILITY: 7/10 - Three of five actions have specific next steps
COMPLETENESS: 6/10 - Demand risk dimension underaddressed
FEASIBILITY: 9/10 - Timelines and owners are realistic
EVIDENCE_BASED: 8/10 - References historical incidents effectively
OVERALL_VERDICT: APPROVED
OVERALL_SCORE: 7.6/10
FEEDBACK: [2-3 sentences]
```

The judge is invoked when `evaluate_quality=true` in the recommendation request. Results are returned as `evaluation_score` and `llm_judge_verdict` in the `RecommendationResponse`.

---

## 10. API Design

### 10.1 Base URL

```
http://localhost:8000/api/v1
```

### 10.2 Endpoint Reference

| Method | Path | Description | Auth |
|---|---|---|---|
| `GET` | `/health` | System health + document count | None |
| `POST` | `/ingest` | Trigger data ingestion | None |
| `POST` | `/search` | Semantic or hybrid incident search | None |
| `POST` | `/search/hybrid` | Forced hybrid search | None |
| `POST` | `/recommendations` | RAG recommendations + risk scoring | None |
| `POST` | `/agents/analyze` | Multi-agent parallel analysis | None |
| `GET` | `/analytics/dashboard` | Aggregated KPI metrics | None |
| `GET` | `/analytics/anomalies` | IsolationForest anomaly detection | None |

### 10.3 Request Schemas

#### `POST /search`

```json
{
  "query": "supplier delivery delays for critical components",
  "top_k": 5,
  "use_hybrid": true,
  "supplier_id": "S003",
  "warehouse_location": "Chicago, IL",
  "shipment_status": "Delayed",
  "severity": "high",
  "incident_type": "Supplier Delay"
}
```

#### `POST /recommendations`

```json
{
  "query": "port congestion impacting shipment schedules",
  "severity": "critical",
  "supplier_id": "S001",
  "evaluate_quality": true
}
```

#### `POST /agents/analyze`

```json
{
  "query": "inventory approaching stockout and supplier delays increasing",
  "supplier_id": "S003",
  "warehouse_location": "New York, NY",
  "include_all_agents": true
}
```

#### `GET /analytics/anomalies`

```
?contamination=0.05
```

### 10.4 Response Schemas

#### `SearchResponse`
```json
{
  "query": "supplier delivery delays",
  "results": [
    {
      "id": "INC00042",
      "content": "Supplier S003 reported...",
      "supplier_id": "S003",
      "severity": "high",
      "delivery_delay": 12.5,
      "inventory_level": 180.0,
      "score": 0.8432,
      "rank": 1
    }
  ],
  "total_found": 5,
  "search_method": "hybrid",
  "latency_ms": 142.3
}
```

#### `RecommendationResponse`
```json
{
  "query": "...",
  "risk_assessment": {
    "overall_score": 0.72,
    "supplier_risk": 0.85,
    "inventory_risk": 0.40,
    "shipment_risk": 0.65,
    "demand_risk": 0.30,
    "risk_level": "high",
    "risk_factors": ["Critical supplier delays averaging 11.2 days", "..."]
  },
  "recommendations": [
    {
      "priority": 1,
      "action": "Activate backup supplier S007 for critical component orders",
      "timeline": "Immediate",
      "owner": "Procurement Team",
      "expected_impact": "Reduce single-source dependency; restore 80% supply capacity within 48h"
    }
  ],
  "summary": "...",
  "confidence_score": 0.82,
  "evaluation_score": 0.76,
  "llm_judge_verdict": "APPROVED",
  "latency_ms": 2840.1
}
```

#### `OrchestratorResponse`
```json
{
  "query": "...",
  "agents_invoked": ["SupplierRiskAgent", "ShipmentAnalysisAgent", "InventoryIntelligenceAgent", "RecommendationAgent"],
  "agent_results": [
    {
      "agent_name": "SupplierRiskAgent",
      "agent_type": "supplier_risk",
      "findings": ["Supplier S003 has 3 critical delays in past 6 months"],
      "risk_score": 0.78,
      "recommendations": ["Dual-source critical components immediately"],
      "escalated": true,
      "escalation_reason": "Supplier risk score exceeds threshold (>0.7)"
    }
  ],
  "consolidated_risk_score": 0.69,
  "consolidated_recommendations": [...],
  "proactive_alerts": ["Port congestion at LA typically peaks Q4 — pre-position inventory"],
  "escalation_chain": ["SupplierRiskAgent → RecommendationAgent: Supplier risk score exceeds threshold"],
  "summary": "...",
  "latency_ms": 6120.5
}
```

### 10.5 Error Handling

All endpoints return standard HTTP error codes:

| Code | Condition |
|---|---|
| `400 Bad Request` | Invalid query (too short, injection detected, etc.) |
| `422 Unprocessable Entity` | Pydantic validation failure (wrong field types) |
| `500 Internal Server Error` | LLM call failure, vector store error |
| `503 Service Unavailable` | Health check failure |

---

## 11. Frontend Architecture

**Files:** `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`

### 11.1 SPA Structure

The frontend is a **zero-dependency Single Page Application** — no frameworks, no build tools, no CDN dependencies. This ensures it opens directly from the filesystem without any server setup.

**Five tabs, each mapping to a backend capability:**

| Tab | API Endpoint | Feature |
|---|---|---|
| Search | `POST /search` | Natural language incident retrieval with filters |
| Recommendations | `POST /recommendations` | Risk assessment + mitigation strategies |
| Multi-Agent | `POST /agents/analyze` | Parallel agent results + escalation chain |
| Dashboard | `GET /analytics/dashboard` | KPI metrics grid + distribution charts |
| Anomalies | `GET /analytics/anomalies` | Anomaly cards + correlation insights |

### 11.2 Design System

CSS custom properties define a consistent dark-mode design system:

```css
:root {
  --bg:       #0f1117  /* page background */
  --surface:  #1a1d27  /* card background */
  --surface2: #22263a  /* input/nested background */
  --border:   #2e3250  /* subtle borders */
  --accent:   #4f7fff  /* primary blue */
  --accent2:  #7c5cfc  /* purple for recommendations */
  --success:  #34d399  /* green (low risk) */
  --warning:  #fbbf24  /* amber (medium/high risk) */
  --danger:   #f87171  /* red (critical) */
}
```

Severity colors map directly from API `severity` values to CSS classes (`critical`, `high`, `medium`, `low`), ensuring visual consistency with the risk assessment data.

### 11.3 Risk Visualization

Risk scores are rendered as animated CSS progress bars:

```javascript
function riskBar(label, score, colorClass) {
  const pct = Math.round(score * 100);
  return `<div class="risk-row">
    <span class="risk-label">${label}</span>
    <div class="risk-bar-wrap">
      <div class="risk-bar ${colorClass}" style="width:${pct}%"></div>
    </div>
    <span class="risk-value">${pct}%</span>
  </div>`;
}
```

Bar width is set via inline `style`, and the CSS `transition: width 0.5s` creates a smooth animation on data load.

### 11.4 Health Badge

The header health badge polls `GET /health` every 30 seconds and updates to reflect:
- Green dot: API healthy, document count shown
- Red dot: API unreachable

---

## 12. Design Decisions & Trade-offs

### 12.1 Vector Store: Pure NumPy vs. ChromaDB vs. Pinecone

| Factor | Pure NumPy (chosen) | ChromaDB | Pinecone |
|---|---|---|---|
| Setup | Zero dependencies | Requires C++ build tools (MSVC on Windows) | Managed cloud |
| Python 3.13 compat | Yes — no native code | No — `chroma-hnswlib` has no Py 3.13 wheel | Yes |
| Persistence | `.npy` + `.json` | SQLite + HNSW binary | Cloud API |
| Scale | ~100K docs (RAM) | ~1M docs on disk | Billions of vectors |
| **Decision** | **Chosen** | Blocked by build tool constraint | Future production path |

**Rationale:** ChromaDB's `chroma-hnswlib` C++ extension has no pre-built wheel for Python 3.13 on Windows, and `MSVC` was not available in the target environment. The `VectorStore` interface is fully abstracted — swapping to ChromaDB or Pinecone requires changing only `vector_store.py`.

### 12.2 Chunking Strategy: Row-per-Document vs. Sliding Window

| Strategy | Pros | Cons |
|---|---|---|
| **Row-per-document** (chosen) | Self-contained, no cross-chunk context loss | Long documents may exceed context |
| Sliding window | Handles very long documents | Chunks lose metadata boundaries |
| Sentence-level | Fine-grained | Loses incident-level context |

**Rationale:** Each CSV row represents one complete incident event. Splitting rows would lose the natural semantic unit. Row-level documents stay well under the 256-token SentenceTransformer limit.

### 12.3 Hybrid Search: Reciprocal Rank Fusion vs. Linear Combination

| Strategy | Pros | Cons |
|---|---|---|
| **RRF** (chosen) | Scale-invariant, no normalization needed | Less tunable |
| Linear combination | Intuitive α weighting | Requires BM25 score normalization |
| Learn-to-rank | Optimal fusion | Requires labeled training data |

**Rationale:** BM25 scores are unbounded (depend on corpus statistics), making direct linear combination unreliable. RRF operates on rank positions only, which are comparable across methods.

### 12.4 Agent Orchestration: ThreadPoolExecutor vs. Async

| Strategy | Pros | Cons |
|---|---|---|
| **ThreadPoolExecutor** (chosen) | Simple, works with sync LLM clients | GIL limits true parallelism |
| asyncio + async clients | True async I/O concurrency | Requires async-aware agent code |
| Celery/task queues | Distributed, fault-tolerant | Operational complexity |

**Rationale:** The OpenAI client is synchronous. `ThreadPoolExecutor` achieves effective parallelism for I/O-bound LLM calls (threads block on network, not CPU), providing the 3x speedup needed without rewriting all agents as async.

### 12.5 LLM Model: GPT-4o-mini via Gateway

| Aspect | Decision |
|---|---|
| Model | `gpt-4o-mini` (configurable via `LLM_MODEL` env var) |
| Gateway | `https://keygateway.arshnivlabs.com/v1` (educational proxy) |
| API key | `learner039` (gateway key, not direct OpenAI) |
| Context window | 128K tokens |
| Function calling | Native OpenAI tool-use format (all agents) |
| Max tokens | **500** — hard gateway limit; configurable via `MAX_TOKENS` |
| SSL | `httpx.Client(verify=False)` injected via `make_openai_client()` — gateway cert not in `certifi` bundle |

**`make_openai_client()` factory** centralises the base_url + SSL logic so no duplication across rag_service, evaluation_service, and all agents.

### 12.6 Embedding: OpenAI API with Sentence-Transformers Fallback

| Aspect | Decision |
|---|---|
| Primary | `text-embedding-3-small` via OpenAI API (1536-dim) |
| Fallback | `all-MiniLM-L6-v2` via sentence-transformers (384-dim, local) |
| Trigger | Gateway `/embeddings` returns 404 or connection error |
| Probe | One test embedding call during `EmbeddingModel.__init__` |
| Dimension guard | `VectorStore` auto-detects model/dim change and rebuilds |

### 12.6 Evaluation: DeepEval + Custom LLM Judge

The dual evaluation approach addresses different failure modes:

| Evaluator | What It Catches |
|---|---|
| DeepEval | Hallucination (faithfulness), irrelevant retrieval (contextual precision) |
| LLM Judge | Action quality, feasibility, completeness, business value |

Both are optional (triggered by `evaluate_quality=true`) to avoid adding latency to standard requests.

---

## 13. Deployment

### 13.1 Local Development

```bash
# 1. Set environment
cp .env.example .env
# Edit: OPENAI_API_KEY=sk-...

# 2. Install
cd backend
pip install -r requirements.txt

# 3. Generate dataset
python -m app.data.generate_sample

# 4. Start server (auto-ingests on first boot)
uvicorn app.main:app --reload --port 8000

# 5. API docs
open http://localhost:8000/docs

# 6. Frontend
open frontend/index.html
```

### 13.2 Docker Deployment

```bash
cp .env.example .env          # set OPENAI_API_KEY
docker-compose up --build     # builds backend, serves frontend via Nginx

# Services:
# Backend API:   http://localhost:8000
# Frontend:      http://localhost:3000
# Swagger UI:    http://localhost:8000/docs
```

**Docker Compose services:**

| Service | Image | Port | Volumes |
|---|---|---|---|
| `backend` | Custom (Python 3.11-slim) | 8000 | `./data:/app/data`, `chroma_data:/app/chroma_db` |
| `frontend` | nginx:alpine | 3000 | `./frontend:/usr/share/nginx/html:ro` |

### 13.3 Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | — | **Yes** | OpenAI API key or gateway learner key |
| `OPENAI_BASE_URL` | `None` | No | Custom gateway URL — SSL verify auto-disabled when set |
| `LLM_MODEL` | `gpt-4o-mini` | No | OpenAI model for chat completions |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | No | OpenAI embedding model (falls back to ST if endpoint unavailable) |
| `MAX_TOKENS` | `500` | No | Max LLM output tokens — set ≤ 500 for educational gateways |
| `CHROMA_PERSIST_DIRECTORY` | `./chroma_db` | No | Numpy vector store persist path |
| `CHROMA_BASE_DIR` | `./chroma_sessions` | No | Session-scoped store root |
| `CHROMA_COLLECTION_NAME` | `supply_chain_incidents` | No | Logical collection name |
| `TOP_K_RESULTS` | `10` | No | Default search top-k |
| `HYBRID_ALPHA` | `0.5` | No | Semantic weight in RRF (0=BM25 only, 1=semantic only) |
| `MAX_CONTEXT_TOKENS` | `8000` | No | RAG context budget (tiktoken-counted) |
| `DATA_PATH` | `./data/supply_chain_data.csv` | No | Dataset CSV path |
| `ANOMALY_CONTAMINATION` | `0.05` | No | IsolationForest expected anomaly fraction |
| `DEBUG` | `false` | No | Enable verbose debug logging |

### 13.4 Running Tests

```bash
cd backend
pytest tests/ -v

# Expected output:
# tests/test_search.py::TestGuardrails::test_valid_query          PASSED
# tests/test_search.py::TestGuardrails::test_blocked_pattern      PASSED
# tests/test_search.py::TestRiskScoring::test_high_risk_scenario  PASSED
# tests/test_agents.py::TestAgentParsing::test_parse_agent_result PASSED
# tests/test_agents.py::TestOrchestrator::test_consolidated_risk  PASSED
# ...
```

---

## 14. Security Considerations

### 14.1 Input Validation

All user inputs pass through three validation layers before any processing:
1. Pydantic field validators (type, length bounds)
2. Regex injection detection (prompt injection, XSS, SQL injection, shell commands)
3. Supply chain relevance scoring (domain check)

### 14.2 API Key Management

- API keys are loaded exclusively from environment variables (`.env` file)
- `.env` is listed in `.gitignore` — never committed
- `.env.example` contains only placeholder values
- Keys are accessed via `settings.OPENAI_API_KEY` (Pydantic BaseSettings), not hardcoded

### 14.3 CORS

The current CORS configuration allows all origins (`allow_origins=["*"]`) for development convenience. For production, restrict to known frontend origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],
    ...
)
```

### 14.4 Data Security

- The synthetic dataset contains no real personal or business data
- ChromaDB is stored locally — not exposed externally
- LLM requests contain only supply chain operational descriptions, not PII

---

## 15. Project File Structure

```
AI-Powered Supply Chain Risk Intelligence Assistant/
│
├── .env.example                           # Environment variable template
├── docker-compose.yml                     # Multi-service Docker orchestration
├── README.md                              # Quick-start guide
├── TECHNICAL_DOCUMENT.md                  # This document
│
├── data/
│   └── supply_chain_data.csv              # Generated: 600 synthetic incidents
│
├── backend/
│   ├── requirements.txt                   # Python dependencies
│   ├── Dockerfile                         # Backend container definition
│   │
│   └── app/
│       ├── main.py                        # FastAPI app + lifespan + routes
│       │
│       ├── core/                          # Infrastructure services
│       │   ├── config.py                  # pydantic-settings configuration
│       │   ├── embeddings.py              # Sentence-Transformers singleton
│       │   ├── vector_store.py            # ChromaDB wrapper
│       │   ├── hybrid_search.py           # BM25 + semantic + RRF + reranker
│       │   └── guardrails.py              # Input validation + safety
│       │
│       ├── models/
│       │   └── schemas.py                 # All Pydantic request/response models
│       │
│       ├── data/                          # Data pipeline
│       │   ├── generate_sample.py         # Synthetic dataset generator
│       │   ├── preprocessing.py           # CSV cleaning + risk enrichment
│       │   ├── chunking.py                # Doc assembly + token counting
│       │   └── ingestion.py               # End-to-end ingestion pipeline
│       │
│       ├── services/                      # Business logic
│       │   ├── rag_service.py             # Search + recommendation generation
│       │   ├── risk_scoring.py            # Multi-dimensional risk assessment
│       │   ├── anomaly_detection.py       # IsolationForest + correlations
│       │   └── evaluation_service.py      # DeepEval + LLM-as-judge
│       │
│       ├── agents/                        # Multi-agent system
│       │   ├── base_agent.py              # Abstract base + OpenAI tool-use loop
│       │   ├── supplier_risk_agent.py     # Supplier performance analysis
│       │   ├── shipment_analysis_agent.py # Route + delay analysis
│       │   ├── inventory_intelligence_agent.py  # Stockout + demand analysis
│       │   ├── recommendation_agent.py    # Cross-agent synthesis
│       │   └── orchestrator.py            # Parallel execution + A2A escalation
│       │
│       ├── api/routes/                    # API endpoint handlers
│       │   ├── search.py                  # /search, /search/hybrid
│       │   ├── recommendations.py         # /recommendations
│       │   ├── analytics.py               # /analytics/dashboard, /anomalies
│       │   └── agents.py                  # /agents/analyze
│       │
│       └── tests/
│           ├── test_search.py             # Guardrails + risk scoring tests
│           └── test_agents.py             # Agent parsing + orchestrator tests
│
└── frontend/
    ├── index.html                         # SPA shell (5 tabs)
    ├── styles.css                         # Dark-mode design system
    └── app.js                             # Tab routing + API calls + rendering
```
