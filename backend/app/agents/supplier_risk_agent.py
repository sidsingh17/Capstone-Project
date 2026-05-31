import re
import logging
from typing import List, Dict, Any

from app.agents.base_agent import BaseSupplyChainAgent
from app.models.schemas import AgentResult

logger = logging.getLogger(__name__)


class SupplierRiskAgent(BaseSupplyChainAgent):
    agent_name = "SupplierRiskAgent"
    agent_type = "supplier_risk"

    @property
    def system_prompt(self) -> str:
        return """You are a supplier risk specialist focused on evaluating supplier performance,
delivery reliability, and supply chain dependency risks.

Analyze supplier-related incidents and provide:
1. Supplier performance assessment (delivery reliability, delay patterns)
2. Dependency risk identification (single-source risks, concentration)
3. Specific supplier risk scores with justification
4. Immediate risk mitigation actions

Structure your analysis with:
RISK_SCORE: [0.0-1.0]
FINDINGS: [bullet list of key findings]
RECOMMENDATIONS: [bullet list of actions]
ESCALATE: [YES/NO] — escalate if supplier risk score > 0.7"""

    @property
    def tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_supplier_history",
                    "description": "Retrieve historical performance data for a specific supplier",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "supplier_id": {"type": "string", "description": "Supplier identifier"},
                            "metric": {"type": "string", "enum": ["delay", "cost", "quality", "all"]},
                        },
                        "required": ["supplier_id"],
                    },
                },
            }
        ]

    def _handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        if tool_name == "get_supplier_history":
            supplier_id = tool_input.get("supplier_id", "Unknown")
            return (
                f"Supplier {supplier_id} history: Average delay 5.2 days, "
                f"on-time delivery rate 72%, 3 critical incidents in last 6 months."
            )
        return super()._handle_tool_call(tool_name, tool_input)

    def analyze(self, query: str, context: List[Dict[str, Any]], **kwargs) -> AgentResult:
        supplier_id = kwargs.get("supplier_id")
        context_text = self._build_context_summary(context)

        messages = [
            {
                "role": "user",
                "content": f"""Analyze supplier risk for this supply chain situation:

Query: {query}
Supplier Focus: {supplier_id or 'All suppliers in context'}

Relevant Incidents:
{context_text}

Provide a comprehensive supplier risk assessment.""",
            }
        ]

        response_text = self._call_llm(messages, tools=self.tools)
        return _parse_agent_result(self.agent_name, self.agent_type, response_text)


def _parse_agent_result(agent_name: str, agent_type: str, text: str) -> AgentResult:
    risk_match = re.search(r"RISK_SCORE:\s*([0-9.]+)", text, re.IGNORECASE)
    risk_score = float(risk_match.group(1)) if risk_match else 0.5
    risk_score = max(0.0, min(1.0, risk_score))

    findings = _extract_bullets(text, "FINDINGS")
    recommendations = _extract_bullets(text, "RECOMMENDATIONS")

    escalate_match = re.search(r"ESCALATE:\s*(YES|NO)", text, re.IGNORECASE)
    escalated = escalate_match and escalate_match.group(1).upper() == "YES"
    escalation_reason = "Supplier risk score exceeds threshold (>0.7)" if escalated else None

    return AgentResult(
        agent_name=agent_name,
        agent_type=agent_type,
        findings=findings if findings else [text[:200]],
        risk_score=risk_score,
        recommendations=recommendations if recommendations else ["Review supplier contracts", "Diversify supply base"],
        escalated=escalated,
        escalation_reason=escalation_reason,
    )


def _extract_bullets(text: str, section: str) -> List[str]:
    pattern = re.compile(rf"{section}:(.*?)(?=\n[A-Z_]+:|\Z)", re.DOTALL | re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return []
    block = match.group(1)
    items = re.findall(r"[-•*]\s*(.+)", block)
    return [item.strip() for item in items if item.strip()][:6]
