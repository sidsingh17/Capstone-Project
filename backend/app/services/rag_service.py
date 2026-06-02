import logging
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI

from app.core.config import get_settings, make_openai_client
from app.core.hybrid_search import HybridSearchEngine
from app.core.guardrails import validate_query, sanitize_query
from app.data.chunking import truncate_context
from app.models.schemas import (
    SearchQuery, SearchResponse, IncidentDocument,
    RecommendationRequest, RecommendationResponse, MitigationStep,
)
from app.services.risk_scoring import compute_risk_score

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert supply chain risk intelligence analyst. Your role is to:
1. Analyze supply chain incidents and operational data
2. Identify risk patterns, root causes, and cascading effects
3. Provide clear, actionable mitigation recommendations
4. Be concise, specific, and data-driven in your responses

Always structure recommendations with: Priority, Action, Timeline, Owner, and Expected Impact.
Focus on practical, immediately actionable guidance."""


class RAGService:
    def __init__(self):
        self.settings = get_settings()
        self.search_engine = HybridSearchEngine()
        self._client: Optional[OpenAI] = None

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            self._client = make_openai_client()
        return self._client

    def search(self, request: SearchQuery) -> SearchResponse:
        t0 = time.perf_counter()

        is_valid, err = validate_query(request.query)
        if not is_valid:
            raise ValueError(err)

        clean_query = sanitize_query(request.query)

        where = self.search_engine.vector_store.build_where_filter(
            supplier_id=request.supplier_id,
            warehouse_location=request.warehouse_location,
            shipment_status=request.shipment_status.value if request.shipment_status else None,
            severity=request.severity.value if request.severity else None,
            incident_type=request.incident_type.value if request.incident_type else None,
        )

        if request.use_hybrid:
            raw_results = self.search_engine.hybrid_search(clean_query, top_k=request.top_k * 2, where=where)
        else:
            raw_results = self.search_engine.semantic_search(clean_query, top_k=request.top_k * 2, where=where)

        reranked = self.search_engine.rerank(clean_query, raw_results, top_k=request.top_k)

        incidents = [_doc_to_incident(d, rank + 1) for rank, d in enumerate(reranked)]

        latency = (time.perf_counter() - t0) * 1000
        return SearchResponse(
            query=clean_query,
            results=incidents,
            total_found=len(incidents),
            search_method="hybrid" if request.use_hybrid else "semantic",
            latency_ms=round(latency, 2),
        )

    def generate_recommendations(self, request: RecommendationRequest) -> RecommendationResponse:
        t0 = time.perf_counter()

        is_valid, err = validate_query(request.query)
        if not is_valid:
            raise ValueError(err)

        clean_query = sanitize_query(request.query)

        search_request = SearchQuery(
            query=clean_query,
            top_k=8,
            supplier_id=request.supplier_id,
            severity=request.severity,
            use_hybrid=True,
        )
        search_response = self.search(search_request)
        retrieved_docs = [_incident_to_doc(i) for i in search_response.results]

        trimmed_docs = truncate_context(retrieved_docs, max_tokens=self.settings.MAX_CONTEXT_TOKENS)
        risk_score = compute_risk_score(trimmed_docs)

        context_text = _build_context(trimmed_docs)
        user_message = _build_recommendation_prompt(clean_query, context_text, risk_score)

        response = self.client.chat.completions.create(
            model=self.settings.LLM_MODEL,
            max_tokens=self.settings.MAX_TOKENS,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )

        raw_text = response.choices[0].message.content or ""
        recommendations = _parse_recommendations(raw_text)
        summary = _extract_summary(raw_text)
        confidence = _estimate_confidence(risk_score.overall_score, len(trimmed_docs))

        latency = (time.perf_counter() - t0) * 1000
        return RecommendationResponse(
            query=clean_query,
            risk_assessment=risk_score,
            recommendations=recommendations,
            summary=summary,
            confidence_score=confidence,
            latency_ms=round(latency, 2),
        )


def _doc_to_incident(doc: Dict[str, Any], rank: int) -> IncidentDocument:
    meta = doc.get("metadata", {})
    return IncidentDocument(
        id=doc["id"],
        content=doc["content"],
        supplier_id=meta.get("supplier_id"),
        warehouse_location=meta.get("warehouse_location"),
        shipment_status=meta.get("shipment_status"),
        severity=meta.get("severity"),
        incident_type=meta.get("incident_type"),
        delivery_delay=meta.get("delivery_delay"),
        transportation_cost=meta.get("transportation_cost"),
        inventory_level=meta.get("inventory_level"),
        timestamp=meta.get("timestamp"),
        region=meta.get("region"),
        score=round(float(doc.get("score", doc.get("hybrid_score", 0))), 4),
        rank=rank,
    )


def _incident_to_doc(incident: IncidentDocument) -> Dict[str, Any]:
    return {
        "id": incident.id,
        "content": incident.content,
        "metadata": {
            "supplier_id": incident.supplier_id or "",
            "warehouse_location": incident.warehouse_location or "",
            "shipment_status": incident.shipment_status or "",
            "severity": incident.severity or "",
            "incident_type": incident.incident_type or "",
            "delivery_delay": incident.delivery_delay or 0.0,
            "transportation_cost": incident.transportation_cost or 0.0,
            "inventory_level": incident.inventory_level or 0.0,
            "timestamp": incident.timestamp or "",
            "token_count": len(incident.content.split()) * 2,
        },
    }


def _build_context(docs: List[Dict[str, Any]]) -> str:
    parts = []
    for i, doc in enumerate(docs, 1):
        meta = doc.get("metadata", {})
        parts.append(
            f"[Incident {i}] {doc['content']}\n"
            f"  Severity: {meta.get('severity', 'N/A')} | "
            f"Type: {meta.get('incident_type', 'N/A')} | "
            f"Delay: {meta.get('delivery_delay', 0):.0f} days | "
            f"Inventory: {meta.get('inventory_level', 0):.0f} units"
        )
    return "\n\n".join(parts)


def _build_recommendation_prompt(query: str, context: str, risk_score) -> str:
    return f"""Supply Chain Risk Analysis Request
Query: {query}

Risk Assessment:
- Overall Risk Score: {risk_score.overall_score:.2%}
- Risk Level: {risk_score.risk_level.value.upper()}
- Supplier Risk: {risk_score.supplier_risk:.2%}
- Inventory Risk: {risk_score.inventory_risk:.2%}
- Shipment Risk: {risk_score.shipment_risk:.2%}
- Key Risk Factors: {', '.join(risk_score.risk_factors[:3]) if risk_score.risk_factors else 'None identified'}

Historical Context (Similar Incidents):
{context}

Please provide:
1. A brief summary of the risk situation (2-3 sentences)
2. Exactly 5 prioritized mitigation recommendations, each formatted as:
   PRIORITY [1-5]: [Action]
   Timeline: [Immediate/24h/Week/Month]
   Owner: [Role/Team]
   Expected Impact: [Specific outcome]

Be specific, actionable, and reference the historical data where relevant."""


def _parse_recommendations(text: str) -> List[MitigationStep]:
    import re
    steps = []
    pattern = re.compile(
        r"PRIORITY\s*\[?(\d)\]?\s*:?\s*(.+?)(?=PRIORITY|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        priority = int(match.group(1))
        block = match.group(2).strip()

        action_match = re.search(r"^([^\n]+)", block)
        timeline_match = re.search(r"Timeline:\s*([^\n]+)", block, re.IGNORECASE)
        owner_match = re.search(r"Owner:\s*([^\n]+)", block, re.IGNORECASE)
        impact_match = re.search(r"Expected Impact:\s*([^\n]+)", block, re.IGNORECASE)

        steps.append(MitigationStep(
            priority=priority,
            action=action_match.group(1).strip() if action_match else block[:100],
            timeline=timeline_match.group(1).strip() if timeline_match else "To be determined",
            owner=owner_match.group(1).strip() if owner_match else "Operations Team",
            expected_impact=impact_match.group(1).strip() if impact_match else "Risk reduction",
        ))

    if not steps:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        for i, line in enumerate(lines[:5], 1):
            steps.append(MitigationStep(
                priority=i,
                action=line[:200],
                timeline="To be determined",
                owner="Operations Team",
                expected_impact="Risk mitigation",
            ))

    return steps[:5]


def _extract_summary(text: str) -> str:
    lines = text.strip().split("\n")
    summary_lines = []
    for line in lines:
        if "PRIORITY" in line.upper():
            break
        if line.strip():
            summary_lines.append(line.strip())
        if len(summary_lines) >= 3:
            break
    return " ".join(summary_lines) if summary_lines else text[:300]


def _estimate_confidence(risk_score: float, num_docs: int) -> float:
    doc_factor = min(num_docs / 5.0, 1.0)
    return round(0.5 + 0.3 * doc_factor + 0.2 * (1 - abs(risk_score - 0.5)), 3)
