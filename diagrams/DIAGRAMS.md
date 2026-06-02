# AI-Powered Supply Chain Risk Intelligence Assistant
**Current Stack:** Python 3.13 · FastAPI 0.136 · GPT-4o-mini · text-embedding-3-small · Pure-NumPy VectorStore · BM25 · IsolationForest
## Sequence Diagrams & Flowcharts

---

## 1. Sequence Diagram — RAG Search Flow

```mermaid
sequenceDiagram
    actor U as Operations Manager
    participant FE as Frontend (SPA)
    participant API as FastAPI /search
    participant GR as Guardrails
    participant HS as HybridSearchEngine
    participant BM as BM25 Index
    participant VS as VectorStore (Numpy)
    participant EM as EmbeddingModel

    U->>FE: Enter natural language query
    FE->>API: POST /api/v1/search {query, filters, top_k}
    API->>GR: validate_query(query)
    GR-->>API: ✅ valid / ❌ 400 Bad Request

    API->>EM: encode_single(query)
    EM-->>API: query_embedding [1536-dim or 384-dim]

    par Parallel Retrieval
        API->>BM: get_scores(tokenized_query)
        BM-->>API: bm25_scores[]
    and
        API->>VS: query(query_embedding, where_filter)
        VS-->>API: semantic_results[]
    end

    API->>HS: RRF fusion (alpha=0.5, k=60)
    HS-->>API: merged_ranked_results[]

    API->>HS: rerank(query, results, top_k)
    Note over HS: Domain boost for exact<br/>field matches (supplier, severity)
    HS-->>API: reranked_results[]

    API-->>FE: SearchResponse {results, latency_ms, method}
    FE-->>U: Display ranked incident cards
```

---

## 2. Sequence Diagram — Recommendation Generation Flow

```mermaid
sequenceDiagram
    actor U as Operations Manager
    participant FE as Frontend
    participant API as FastAPI /recommendations
    participant GR as Guardrails
    participant RS as RAGService
    participant HS as HybridSearch
    participant TC as TokenOptimizer
    participant RK as RiskScoring
    participant LLM as OpenAI GPT-4o-mini\n(via keygateway, SSL off)
    participant EV as EvaluationService

    U->>FE: Submit disruption query
    FE->>API: POST /recommendations {query, evaluate_quality}
    API->>GR: validate_query() + is_supply_chain_relevant()
    GR-->>API: sanitized query

    API->>HS: hybrid_search(query, top_k=16)
    HS-->>API: top 8 candidate incidents

    API->>TC: truncate_context(docs, max_tokens=8000)
    Note over TC: tiktoken counts each doc<br/>stops when budget exhausted
    TC-->>API: trimmed_docs[]

    API->>RK: compute_risk_score(trimmed_docs)
    Note over RK: supplier 35% + inventory 30%<br/>+ shipment 25% + demand 10%
    RK-->>API: RiskScore {overall, level, factors}

    API->>LLM: chat.completions.create()<br/>system=analyst_prompt + context<br/>user=query + risk_breakdown
    LLM-->>API: raw_text (structured recommendations)

    API->>API: _parse_recommendations(raw_text)
    Note over API: Regex extracts PRIORITY 1-5<br/>Timeline / Owner / Impact

    opt evaluate_quality=true
        API->>EV: llm_judge_recommendations(query, response, context)
        EV->>LLM: Judge prompt (5 dimensions)
        LLM-->>EV: scores + verdict
        EV-->>API: {overall_score, verdict, feedback}
    end

    API-->>FE: RecommendationResponse {risk, recs, summary, judge_score}
    FE-->>U: Display risk bars + mitigation steps
```

---

## 3. Sequence Diagram — Multi-Agent Orchestration with A2A Escalation

```mermaid
sequenceDiagram
    actor U as Operations Manager
    participant FE as Frontend
    participant OR as Orchestrator
    participant GR as Guardrails
    participant HS as HybridSearch
    participant TP as ThreadPoolExecutor
    participant SA as SupplierRiskAgent
    participant SH as ShipmentAnalysisAgent
    participant IN as InventoryIntelAgent
    participant LLM as OpenAI GPT-4o-mini\n(via keygateway, SSL off)
    participant RA as RecommendationAgent

    U->>FE: Submit complex risk query
    FE->>OR: POST /agents/analyze {query, supplier_id}

    OR->>GR: validate + sanitize
    GR-->>OR: clean query

    OR->>HS: hybrid_search(query, top_k=10)
    HS-->>OR: context_docs[]

    OR->>OR: _select_agents(query)
    Note over OR: keyword routing or include_all=true

    OR->>TP: submit all agents (max_workers=3)

    par Parallel Agent Execution
        TP->>SA: analyze(query, context, supplier_id)
        SA->>LLM: Tool-use call<br/>get_supplier_history()
        LLM-->>SA: tool result
        SA->>LLM: Final analysis call
        LLM-->>SA: RISK_SCORE / FINDINGS / RECS
        SA-->>TP: AgentResult {risk=0.78, escalated=true}
    and
        TP->>SH: analyze(query, context)
        SH->>LLM: Tool-use call<br/>get_route_status()
        LLM-->>SH: tool result
        SH->>LLM: Final analysis call
        LLM-->>SH: RISK_SCORE / FINDINGS / RECS
        SH-->>TP: AgentResult {risk=0.55, escalated=false}
    and
        TP->>IN: analyze(query, context)
        IN->>LLM: Tool-use calls<br/>check_inventory + get_forecast()
        LLM-->>IN: tool results
        IN->>LLM: Final analysis call
        LLM-->>IN: RISK_SCORE / FINDINGS / RECS
        IN-->>TP: AgentResult {risk=0.82, escalated=true}
    end

    TP-->>OR: [SA_result, SH_result, IN_result]

    OR->>OR: _handle_escalations()
    Note over OR: A2A: SA → RecommendationAgent<br/>IN → RecommendationAgent<br/>avg_risk > 0.85 → Director

    OR->>RA: analyze(query, context, agent_findings=[SA,SH,IN])
    RA->>LLM: Synthesize all findings + escalations
    LLM-->>RA: Consolidated strategy + proactive alerts
    RA-->>OR: AgentResult {consolidated_recs, alerts}

    OR->>OR: _compute_consolidated_risk() weighted average
    OR-->>FE: OrchestratorResponse {agents, risk, recs, escalation_chain}
    FE-->>U: Display agent cards + escalation chain + proactive alerts
```

---

## 4. Sequence Diagram — Data Ingestion Pipeline

```mermaid
sequenceDiagram
    actor ADM as Admin / Startup
    participant API as FastAPI /ingest
    participant PIP as DataIngestionPipeline
    participant PRE as Preprocessing
    participant CHK as Chunking (tiktoken)
    participant EM as EmbeddingModel
    participant VS as VectorStore
    participant BM as HybridSearch (BM25)

    ADM->>API: POST /ingest {force_rebuild?}
    
    alt force_rebuild = true
        API->>VS: delete_collection()
        VS-->>API: collection cleared
    end

    API->>PIP: ingest(data_path)
    PIP->>PIP: check count() > 0?
    
    alt Already indexed
        PIP-->>API: skip (idempotent)
    else Empty store
        PIP->>PRE: load_and_clean(CSV)
        Note over PRE: type coercion, dedup,<br/>null handling, timestamp parse
        PRE-->>PIP: cleaned DataFrame (600 rows)

        PIP->>PRE: enrich_dataframe(df)
        Note over PRE: compute risk_score,<br/>inventory_turnover, delay_ratio
        PRE-->>PIP: enriched DataFrame

        PIP->>CHK: dataframe_to_documents(df)
        Note over CHK: Row → structured text<br/>+ metadata dict<br/>+ tiktoken count
        CHK-->>PIP: documents[] (600 docs)

        loop Batches of 100
            PIP->>EM: encode(batch_texts, OpenAI API or ST fallback)
            EM-->>PIP: embeddings [100 × 1536 or 384]
            PIP->>VS: add_documents(batch, embeddings)
            VS-->>PIP: upserted to numpy store
        end

        PIP->>VS: save() → documents.json + embeddings.npy
    end

    API->>BM: build_bm25_index()
    Note over BM: BM25Okapi over full corpus<br/>in-memory tokenized index
    BM-->>API: index ready

    API-->>ADM: {status: success, documents_ingested: 600}
```

---

## 5. Flowchart — Complete System Architecture

```mermaid
flowchart TD
    U([👤 Operations Manager]) --> FE[Frontend SPA\nindex.html]

    FE --> |Search Tab| S_EP[POST /api/v1/search]
    FE --> |Recommendations Tab| R_EP[POST /api/v1/recommendations]
    FE --> |Multi-Agent Tab| A_EP[POST /api/v1/agents/analyze]
    FE --> |Dashboard Tab| D_EP[GET /api/v1/analytics/dashboard]
    FE --> |Anomalies Tab| AN_EP[GET /api/v1/analytics/anomalies]

    subgraph API["FastAPI Application Layer"]
        S_EP
        R_EP
        A_EP
        D_EP
        AN_EP
    end

    subgraph GUARD["Guardrails"]
        G1[Length Validation]
        G2[Injection Detection]
        G3[Domain Relevance Score]
    end

    subgraph CORE["Core Services"]
        EM[EmbeddingModel\ntext-embedding-3-small 1536d\n(fallback: all-MiniLM 384d)]
        VS[VectorStore\nPure Numpy + JSON\nCosine similarity + meta filter]
        BM[BM25 Index\nBM25Okapi\nIn-Memory]
        HS[HybridSearch\nRRF Fusion α=0.5]
        TC[TokenOptimizer\ntiktoken cl100k_base]
    end

    subgraph BSVC["Business Services"]
        RS[RiskScoring\n4-dimension weighted]
        AD[AnomalyDetection\nIsolationForest]
        RAG[RAGService\nRetrieve+Generate]
        EV[EvaluationService\nDeepEval + LLM Judge]
    end

    subgraph AGENTS["Multi-Agent System"]
        OR[Orchestrator\nThreadPoolExecutor]
        SA[SupplierRiskAgent]
        SH[ShipmentAnalysisAgent]
        IN[InventoryIntelAgent]
        RA[RecommendationAgent]
        A2A{A2A Escalation\nrisk > 0.7?}
    end

    subgraph LLMBOX["OpenAI GPT-4o-mini\n(via keygateway, SSL off)"]
        LLM[chat.completions.create\nFunction Calling\nSystem + User Prompts]
    end

    subgraph DATA["Data Layer"]
        CSV[(supply_chain_data.csv\n600 incidents)]
        NP[(numpy embeddings\n+ JSON documents)]
    end

    S_EP --> GUARD
    R_EP --> GUARD
    A_EP --> GUARD

    GUARD --> CORE
    CORE --> HS
    HS --> VS
    HS --> BM

    HS --> RAG
    RAG --> TC
    TC --> RS
    RS --> LLM
    LLM --> EV

    A_EP --> OR
    OR --> SA & SH & IN
    SA --> LLM
    SH --> LLM
    IN --> LLM
    SA & SH & IN --> A2A
    A2A --> |escalate| RA
    A2A --> |no escalation| RA
    RA --> LLM

    D_EP --> VS
    AN_EP --> AD
    AD --> VS

    VS --> NP
    CSV --> DATA
```

---

## 6. Flowchart — Hybrid Search Decision Flow

```mermaid
flowchart TD
    START([Query Received]) --> GUARD{Guardrails\nPass?}
    GUARD -->|❌ Blocked| ERR[Return 400 Error]
    GUARD -->|✅ Valid| SAN[Sanitize Query]

    SAN --> FILTER[Build Metadata Filter\nsupplier / severity / status / type]

    FILTER --> PARALLEL

    subgraph PARALLEL["Parallel Retrieval (fetch_k = top_k × 3)"]
        direction LR
        BM25[BM25Okapi\nTokenize query\nget_scores over corpus]
        SEM[Semantic Search\nEncode query → 1536-dim (OpenAI) or 384-dim (fallback)\nCosine similarity ANN]
    end

    BM25 --> RRF
    SEM --> RRF

    subgraph RRF["Reciprocal Rank Fusion"]
        direction TB
        R1[Semantic score: α × 1÷(k+rank_sem)]
        R2[BM25 score: (1-α) × 1÷(k+rank_bm25)]
        R3[Sum RRF scores per document]
        R1 --> R3
        R2 --> R3
    end

    RRF --> SORT[Sort by RRF score descending\nSlice top_k results]

    SORT --> RERANK

    subgraph RERANK["Logistics-Aware Reranker"]
        RK1[Check query for exact field matches]
        RK2[+0.05 boost per matching field:\nincident_type, severity,\nwarehouse, supplier, product]
        RK3[Re-sort by rerank_score]
        RK1 --> RK2 --> RK3
    end

    RERANK --> OUT([Ranked Incident Results])
```

---

## 7. Flowchart — Risk Scoring Logic

```mermaid
flowchart TD
    IN([Retrieved Incidents\nList of Documents]) --> EMPTY{Documents\nempty?}
    EMPTY -->|Yes| ZERO[Return zero risk\nLOW level]

    EMPTY -->|No| EXTRACT[Extract features per document:\ndelivery_delay, inventory_level,\ntransportation_cost, shipment_status,\nseverity]

    EXTRACT --> STATS[Compute aggregates:\navg_delay, avg_inventory,\navg_cost, delay_ratio,\ncritical_count, high_count]

    STATS --> SUPPLIER

    subgraph SUPPLIER["Supplier Risk (weight 35%)"]
        S1{avg_delay}
        S1 -->|> 14 days| SR1[0.90]
        S1 -->|> 7 days| SR2[0.65]
        S1 -->|> 3 days| SR3[0.40]
        S1 -->|≤ 3 days| SR4[0.15]
    end

    STATS --> INVENTORY

    subgraph INVENTORY["Inventory Risk (weight 30%)"]
        I1{avg_inventory\nunits}
        I1 -->|< 50| IR1[0.95]
        I1 -->|< 150| IR2[0.70]
        I1 -->|< 300| IR3[0.40]
        I1 -->|≥ 300| IR4[0.15]
    end

    STATS --> SHIPMENT

    subgraph SHIPMENT["Shipment Risk (weight 25%)"]
        SH1{delayed_ratio}
        SH1 -->|> 60%| SHR1[0.85]
        SH1 -->|> 30%| SHR2[0.55]
        SH1 -->|≤ 30%| SHR3[0.20]
    end

    STATS --> DEMAND

    subgraph DEMAND["Demand Risk (weight 10%)"]
        D1{avg_cost USD}
        D1 -->|> $3000| DR1[0.70]
        D1 -->|> $2000| DR2[0.45]
        D1 -->|≤ $2000| DR3[0.20]
    end

    SR1 & IR1 & SHR1 & DR1 --> WEIGHTED
    SR2 & IR2 & SHR2 & DR2 --> WEIGHTED
    SR3 & IR3 & SHR3 & DR3 --> WEIGHTED
    SR4 & IR4 & SHR3 & DR3 --> WEIGHTED

    subgraph WEIGHTED["Weighted Combination"]
        W1["overall = (supplier×0.35 + inventory×0.30\n+ shipment×0.25 + demand×0.10)"]
    end

    WEIGHTED --> MULT{critical_count > 0?}
    MULT -->|Yes| MX1[× 1.2]
    MULT -->|No| MULT2{high_count > 1?}
    MULT2 -->|Yes| MX2[× 1.1]
    MULT2 -->|No| CLAMP

    MX1 --> CLAMP[min(score, 1.0)]
    MX2 --> CLAMP

    CLAMP --> LEVEL{Threshold}
    LEVEL -->|≥ 0.75| C1[🔴 CRITICAL]
    LEVEL -->|≥ 0.50| C2[🟠 HIGH]
    LEVEL -->|≥ 0.25| C3[🟡 MEDIUM]
    LEVEL -->|< 0.25| C4[🟢 LOW]

    C1 & C2 & C3 & C4 --> OUT([RiskScore Object\n+ risk_factors list])
```

---

## 8. Flowchart — Multi-Agent Orchestration & A2A Escalation

```mermaid
flowchart TD
    START([Query + Filters]) --> GUARD[Guardrails\nValidate & Sanitize]
    GUARD --> CTX[Hybrid Search\nRetrieve top 10\ncontext documents]
    CTX --> SELECT{include_all_agents?}

    SELECT -->|true| ALL[Run: Supplier + Shipment + Inventory]
    SELECT -->|false| ROUTE[Keyword Routing]
    ROUTE --> |supplier/vendor/delay| SA_ON[SupplierRiskAgent ✓]
    ROUTE --> |shipment/port/freight| SH_ON[ShipmentAnalysisAgent ✓]
    ROUTE --> |inventory/stock/demand| IN_ON[InventoryIntelAgent ✓]

    ALL --> POOL
    SA_ON & SH_ON & IN_ON --> POOL

    subgraph POOL["ThreadPoolExecutor (max_workers=3)"]
        direction LR
        subgraph SA["SupplierRiskAgent"]
            SA1[Build messages]
            SA2[GPT-4o-mini call\n+ tool_use:\nget_supplier_history]
            SA3[Parse RISK_SCORE\nFINDINGS RECS]
        end
        subgraph SH["ShipmentAnalysisAgent"]
            SH1[Build messages]
            SH2[GPT-4o-mini call\n+ tool_use:\nget_route_status]
            SH3[Parse RISK_SCORE\nFINDINGS RECS]
        end
        subgraph IN["InventoryIntelAgent"]
            IN1[Build messages]
            IN2[GPT-4o-mini call\n+ tool_use:\ncheck_inventory\nget_forecast]
            IN3[Parse RISK_SCORE\nFINDINGS RECS]
        end
    end

    SA3 --> RESULTS
    SH3 --> RESULTS
    IN3 --> RESULTS

    RESULTS[Collect AgentResult objects] --> FAIL{Any agent\nfailed?}
    FAIL -->|Yes| STUB[Insert stub result\nrisk=0.0\nmanual review]
    FAIL -->|No| ESC_CHECK
    STUB --> ESC_CHECK

    ESC_CHECK{Any agent\nescalated?\nrisk > 0.7} 

    ESC_CHECK -->|Yes| A2A

    subgraph A2A["A2A Escalation Chain"]
        E1[Log: AgentName → RecommendationAgent:\nescalation_reason]
        E2{avg_escalated_risk\n> 0.85?}
        E1 --> E2
        E2 -->|Yes| E3[Add: RecommendationAgent →\nOperations Director:\nCritical multi-agent escalation]
        E2 -->|No| E4[Standard escalation]
    end

    ESC_CHECK -->|No| REC_AGENT
    A2A --> REC_AGENT

    subgraph REC_AGENT["RecommendationAgent (synthesis)"]
        RA1[Serialize all agent findings]
        RA2[GPT-4o-mini call: synthesize\nconsolidate risks\nresolve conflicts\nproactive alerts]
        RA3[Extract PROACTIVE_ALERTS]
    end

    REC_AGENT --> CONS[Compute consolidated_risk\nweighted: S=0.35 SH=0.30 I=0.35]
    CONS --> MERGE[Merge recommendations\ndeduplicate by first 60 chars]
    MERGE --> OUT([OrchestratorResponse\nagent_results, risk_score\nescalation_chain, proactive_alerts])
```

---

## 9. Flowchart — Anomaly Detection Pipeline

```mermaid
flowchart TD
    START([GET /analytics/anomalies\ncontamination=0.05]) --> LOAD[Load all documents\nfrom VectorStore]

    LOAD --> CHECK{Count ≥ 10?}
    CHECK -->|No| INSUF[Return: insufficient data]

    CHECK -->|Yes| FEAT[Extract 5 numeric features\nper document:\ndelivery_delay\ninventory_level\ntransportation_cost\norder_quantity\ndemand_forecast]

    FEAT --> SCALE[StandardScaler\nnormalize to zero mean\nunit variance]

    SCALE --> ISO[IsolationForest\nn_estimators=100\ncontamination=configurable\nrandom_state=42]

    ISO --> PRED[fit_predict → labels\nscore_samples → anomaly_scores]

    PRED --> FILTER[Filter: label == -1\nanomalous records]

    FILTER --> ATTR[Feature Attribution\nper anomaly:\ncompute Z-score per feature\nflag if Z > 2.5]

    ATTR --> DESC[Generate description:\nwarehouse + supplier + features]

    DESC --> SORT[Sort by anomaly_score\ndescending]

    SORT --> CORR

    subgraph CORR["Correlation Analysis (whole dataset)"]
        C1[Pearson correlation matrix]
        C2{delay↔cost\n|r| > 0.30?}
        C3{inventory↔delay\n|r| > 0.20?}
        C4{demand↔cost\n|r| > 0.25?}
        C5{high_delay_%\n> 20%?}
        C6{low_inv_%\n> 15%?}
    end

    CORR --> INSIGHTS[Collect correlation insights]
    INSIGHTS --> OUT([AnomalyResponse\ntotal_anomalies\nanomalies top-20\ncorrelation_insights])
```
