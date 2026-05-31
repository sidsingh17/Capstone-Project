import re
import logging
from typing import List, Dict, Any

from app.agents.base_agent import BaseSupplyChainAgent
from app.agents.supplier_risk_agent import _parse_agent_result
from app.models.schemas import AgentResult

logger = logging.getLogger(__name__)


class RecommendationAgent(BaseSupplyChainAgent):
    agent_name = "RecommendationAgent"
    agent_type = "recommendation"

    @property
    def system_prompt(self) -> str:
        return """You are a supply chain resilience strategist specializing in synthesizing
multi-source risk intelligence into cohesive, prioritized mitigation strategies.

Given findings from multiple specialized agents, produce:
1. A consolidated risk narrative
2. Cross-cutting mitigation strategies addressing all identified risks
3. Proactive disruption prevention recommendations
4. Business continuity plan elements

Structure your analysis with:
RISK_SCORE: [0.0-1.0] (consolidated across all agent findings)
FINDINGS: [bullet list of top consolidated insights]
RECOMMENDATIONS: [bullet list of top 5 priority actions, each with owner and timeline]
ESCALATE: [YES/NO] — escalate if consolidated risk > 0.75
PROACTIVE_ALERTS: [bullet list of forward-looking warnings]"""

    @property
    def tools(self) -> List[Dict[str, Any]]:
        return []

    def analyze(self, query: str, context: List[Dict[str, Any]], **kwargs) -> AgentResult:
        agent_findings: List[AgentResult] = kwargs.get("agent_findings", [])

        findings_text = ""
        for af in agent_findings:
            findings_text += f"\n[{af.agent_name}] Risk: {af.risk_score:.2f}\n"
            findings_text += "  Findings: " + "; ".join(af.findings[:3]) + "\n"
            findings_text += "  Recs: " + "; ".join(af.recommendations[:2]) + "\n"
            if af.escalated:
                findings_text += f"  ⚠ ESCALATED: {af.escalation_reason}\n"

        context_text = self._build_context_summary(context, max_items=3)

        messages = [
            {
                "role": "user",
                "content": f"""Synthesize multi-agent supply chain risk analysis:

Original Query: {query}

Agent Analysis Results:
{findings_text}

Supporting Context:
{context_text}

Generate a consolidated, prioritized mitigation strategy that:
1. Addresses all agent-identified risks
2. Resolves any conflicting recommendations
3. Provides proactive disruption prevention measures
4. Specifies clear ownership and timelines""",
            }
        ]

        response_text = self._call_llm(messages, max_tokens=2000)
        result = _parse_agent_result(self.agent_name, self.agent_type, response_text)

        # Extract proactive alerts
        alerts_match = re.search(
            r"PROACTIVE_ALERTS:(.*?)(?=\n[A-Z_]+:|\Z)", response_text, re.DOTALL | re.IGNORECASE
        )
        if alerts_match:
            alert_items = re.findall(r"[-•*]\s*(.+)", alerts_match.group(1))
            result.findings = result.findings + [f"[ALERT] {a.strip()}" for a in alert_items[:3]]

        return result
