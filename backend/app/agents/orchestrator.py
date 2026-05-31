"""
Multi-Agent Orchestrator with A2A escalation workflow.
Coordinates Supplier Risk, Shipment Analysis, Inventory Intelligence,
and Recommendation agents in parallel, then synthesizes results.
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from app.agents.supplier_risk_agent import SupplierRiskAgent
from app.agents.shipment_analysis_agent import ShipmentAnalysisAgent
from app.agents.inventory_intelligence_agent import InventoryIntelligenceAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.core.hybrid_search import HybridSearchEngine
from app.core.guardrails import validate_query, sanitize_query
from app.models.schemas import AgentResult, OrchestratorResponse

logger = logging.getLogger(__name__)

_ESCALATION_THRESHOLD = 0.7
_MAX_WORKERS = 3


class MultiAgentOrchestrator:
    def __init__(self):
        self.supplier_agent = SupplierRiskAgent()
        self.shipment_agent = ShipmentAnalysisAgent()
        self.inventory_agent = InventoryIntelligenceAgent()
        self.recommendation_agent = RecommendationAgent()
        self.search_engine = HybridSearchEngine()

    def analyze(
        self,
        query: str,
        supplier_id: Optional[str] = None,
        warehouse_location: Optional[str] = None,
        include_all_agents: bool = True,
    ) -> OrchestratorResponse:
        t0 = time.perf_counter()

        is_valid, err = validate_query(query)
        if not is_valid:
            raise ValueError(err)
        query = sanitize_query(query)

        # Retrieve relevant context
        where = self.search_engine.vector_store.build_where_filter(
            supplier_id=supplier_id,
            warehouse_location=warehouse_location,
        )
        context_docs = self.search_engine.hybrid_search(query, top_k=10, where=where)

        # Determine which agents to invoke
        agents_to_run = self._select_agents(query, include_all_agents)

        # Run specialized agents in parallel (A2A parallel phase)
        agent_kwargs = {
            "supplier_id": supplier_id,
            "warehouse_location": warehouse_location,
        }
        specialist_results = self._run_agents_parallel(
            query, context_docs, agents_to_run, agent_kwargs
        )

        # A2A Escalation: if any agent escalates, trigger escalation workflow
        escalation_chain = self._handle_escalations(specialist_results, query, context_docs)

        # Recommendation agent synthesizes all findings
        final_recommendation = self.recommendation_agent.analyze(
            query, context_docs, agent_findings=specialist_results
        )
        specialist_results.append(final_recommendation)

        consolidated_risk = _compute_consolidated_risk(specialist_results[:-1])
        proactive_alerts = _extract_proactive_alerts(final_recommendation)
        consolidated_recs = _merge_recommendations(specialist_results)

        latency = (time.perf_counter() - t0) * 1000
        return OrchestratorResponse(
            query=query,
            agents_invoked=[r.agent_name for r in specialist_results],
            agent_results=specialist_results,
            consolidated_risk_score=consolidated_risk,
            consolidated_recommendations=consolidated_recs[:7],
            proactive_alerts=proactive_alerts,
            escalation_chain=escalation_chain,
            summary=final_recommendation.findings[0] if final_recommendation.findings else "Analysis complete",
            latency_ms=round(latency, 2),
        )

    def _select_agents(self, query: str, include_all: bool) -> List[str]:
        if include_all:
            return ["supplier", "shipment", "inventory"]

        query_lower = query.lower()
        selected = []
        if any(kw in query_lower for kw in ["supplier", "vendor", "delivery", "delay"]):
            selected.append("supplier")
        if any(kw in query_lower for kw in ["shipment", "port", "transport", "route", "freight"]):
            selected.append("shipment")
        if any(kw in query_lower for kw in ["inventory", "stock", "warehouse", "stockout", "demand"]):
            selected.append("inventory")
        return selected or ["supplier", "shipment", "inventory"]

    def _run_agents_parallel(
        self,
        query: str,
        context: List[Dict[str, Any]],
        agent_types: List[str],
        kwargs: Dict[str, Any],
    ) -> List[AgentResult]:
        agent_map = {
            "supplier": self.supplier_agent,
            "shipment": self.shipment_agent,
            "inventory": self.inventory_agent,
        }

        results: List[AgentResult] = []
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = {
                executor.submit(agent_map[a].analyze, query, context, **kwargs): a
                for a in agent_types
                if a in agent_map
            }
            for future in as_completed(futures):
                agent_type = futures[future]
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                    logger.info(f"{agent_type} agent completed. Risk: {result.risk_score:.2f}")
                except Exception as e:
                    logger.error(f"{agent_type} agent failed: {e}")
                    results.append(AgentResult(
                        agent_name=agent_map[agent_type].agent_name,
                        agent_type=agent_type,
                        findings=[f"Analysis failed: {str(e)[:100]}"],
                        risk_score=0.0,
                        recommendations=["Manual review required"],
                        escalated=False,
                    ))
        return results

    def _handle_escalations(
        self,
        results: List[AgentResult],
        query: str,
        context: List[Dict[str, Any]],
    ) -> List[str]:
        escalation_chain: List[str] = []
        escalated_agents = [r for r in results if r.escalated]

        if not escalated_agents:
            return escalation_chain

        # A2A: escalated agents notify recommendation agent and log chain
        for agent_result in escalated_agents:
            chain_entry = (
                f"{agent_result.agent_name} → RecommendationAgent: "
                f"{agent_result.escalation_reason}"
            )
            escalation_chain.append(chain_entry)
            logger.warning(f"A2A Escalation: {chain_entry}")

        avg_escalated_risk = sum(r.risk_score for r in escalated_agents) / len(escalated_agents)
        if avg_escalated_risk > 0.85:
            escalation_chain.append(
                "RecommendationAgent → Operations Director: Critical multi-agent escalation — "
                "risk score exceeds 0.85 threshold. Immediate intervention required."
            )

        return escalation_chain


def _compute_consolidated_risk(results: List[AgentResult]) -> float:
    if not results:
        return 0.0
    weights = {"supplier_risk": 0.35, "shipment_analysis": 0.30, "inventory_intelligence": 0.35}
    weighted_sum = 0.0
    total_weight = 0.0
    for r in results:
        w = weights.get(r.agent_type, 0.33)
        weighted_sum += r.risk_score * w
        total_weight += w
    return round(min(weighted_sum / total_weight if total_weight > 0 else 0.0, 1.0), 3)


def _extract_proactive_alerts(result: AgentResult) -> List[str]:
    return [f for f in result.findings if "[ALERT]" in f]


def _merge_recommendations(results: List[AgentResult]) -> List[str]:
    seen = set()
    merged = []
    for r in results:
        for rec in r.recommendations:
            rec_key = rec[:60].lower().strip()
            if rec_key not in seen:
                seen.add(rec_key)
                merged.append(rec)
    return merged
