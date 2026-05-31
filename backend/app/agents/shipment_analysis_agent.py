import re
import logging
from typing import List, Dict, Any

from app.agents.base_agent import BaseSupplyChainAgent
from app.agents.supplier_risk_agent import _parse_agent_result
from app.models.schemas import AgentResult

logger = logging.getLogger(__name__)


class ShipmentAnalysisAgent(BaseSupplyChainAgent):
    agent_name = "ShipmentAnalysisAgent"
    agent_type = "shipment_analysis"

    @property
    def system_prompt(self) -> str:
        return """You are a logistics and shipment analysis specialist focused on transportation
bottlenecks, port congestion, route disruptions, and delivery performance.

Analyze shipment-related incidents and provide:
1. Shipment delay root cause analysis
2. Transportation route risk assessment
3. Port and customs bottleneck identification
4. Carrier performance evaluation

Structure your analysis with:
RISK_SCORE: [0.0-1.0]
FINDINGS: [bullet list of key findings]
RECOMMENDATIONS: [bullet list of actions]
ESCALATE: [YES/NO] — escalate if critical delay patterns detected"""

    @property
    def tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_route_status",
                    "description": "Get current status of a shipping route",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "origin": {"type": "string"},
                            "destination": {"type": "string"},
                            "transport_mode": {"type": "string", "enum": ["air", "sea", "ground", "rail"]},
                        },
                        "required": ["origin", "destination"],
                    },
                },
            }
        ]

    def _handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        if tool_name == "get_route_status":
            return (
                f"Route {tool_input.get('origin','?')} → {tool_input.get('destination','?')}: "
                f"Current status: Active. Average transit time: 4.5 days. "
                f"Recent disruptions: 1 weather event (resolved)."
            )
        return super()._handle_tool_call(tool_name, tool_input)

    def analyze(self, query: str, context: List[Dict[str, Any]], **kwargs) -> AgentResult:
        warehouse = kwargs.get("warehouse_location")
        context_text = self._build_context_summary(context)

        messages = [
            {
                "role": "user",
                "content": f"""Analyze shipment and logistics risks for this situation:

Query: {query}
Warehouse Focus: {warehouse or 'All locations in context'}

Relevant Incidents:
{context_text}

Focus on: delay patterns, route disruptions, port congestion, carrier issues.
Provide root cause analysis and actionable mitigation steps.""",
            }
        ]

        response_text = self._call_llm(messages, tools=self.tools)
        return _parse_agent_result(self.agent_name, self.agent_type, response_text)
