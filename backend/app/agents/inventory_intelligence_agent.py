import re
import logging
from typing import List, Dict, Any

from app.agents.base_agent import BaseSupplyChainAgent
from app.agents.supplier_risk_agent import _parse_agent_result
from app.models.schemas import AgentResult

logger = logging.getLogger(__name__)


class InventoryIntelligenceAgent(BaseSupplyChainAgent):
    agent_name = "InventoryIntelligenceAgent"
    agent_type = "inventory_intelligence"

    @property
    def system_prompt(self) -> str:
        return """You are an inventory intelligence specialist focused on stock level optimization,
stockout prediction, demand-supply balance, and inventory risk management.

Analyze inventory-related data and provide:
1. Stockout risk assessment with urgency scoring
2. Inventory level optimization recommendations
3. Demand-supply gap analysis
4. Safety stock and reorder point recommendations

Structure your analysis with:
RISK_SCORE: [0.0-1.0]
FINDINGS: [bullet list of key findings]
RECOMMENDATIONS: [bullet list of actions]
ESCALATE: [YES/NO] — escalate if any warehouse facing critical stockout risk (<50 units)"""

    @property
    def tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_inventory_levels",
                    "description": "Check current inventory levels at a warehouse",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "warehouse_location": {"type": "string"},
                            "product_category": {"type": "string"},
                        },
                        "required": ["warehouse_location"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_demand_forecast",
                    "description": "Retrieve demand forecast for a product category",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "product_category": {"type": "string"},
                            "forecast_horizon_days": {"type": "integer"},
                        },
                        "required": ["product_category"],
                    },
                },
            },
        ]

    def _handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        if tool_name == "check_inventory_levels":
            warehouse = tool_input.get("warehouse_location", "Unknown")
            product = tool_input.get("product_category", "General")
            return (
                f"Warehouse {warehouse} — {product}: Current stock 287 units. "
                f"Safety stock threshold: 150 units. Days of supply: 14.3 days. Status: Adequate."
            )
        if tool_name == "get_demand_forecast":
            product = tool_input.get("product_category", "General")
            horizon = tool_input.get("forecast_horizon_days", 30)
            return (
                f"Demand forecast for {product} over next {horizon} days: "
                f"Expected 420 units. Confidence: 78%. Seasonal factor: +12%."
            )
        return super()._handle_tool_call(tool_name, tool_input)

    def analyze(self, query: str, context: List[Dict[str, Any]], **kwargs) -> AgentResult:
        context_text = self._build_context_summary(context)

        inv_data = []
        for doc in context[:10]:
            meta = doc.get("metadata", {})
            inv = float(meta.get("inventory_level", 0))
            demand = float(meta.get("demand_forecast", 0))
            if inv > 0 or demand > 0:
                inv_data.append(f"  {meta.get('warehouse_location','?')}: {inv:.0f} units vs {demand:.0f} forecast")

        inv_summary = "\n".join(inv_data[:5]) if inv_data else "No inventory data available"

        messages = [
            {
                "role": "user",
                "content": f"""Analyze inventory intelligence and stockout risks:

Query: {query}

Inventory Snapshot:
{inv_summary}

Relevant Incidents:
{context_text}

Assess: stockout risks, demand-supply gaps, safety stock adequacy.
Prioritize locations with critically low inventory.""",
            }
        ]

        response_text = self._call_llm(messages, tools=self.tools)
        return _parse_agent_result(self.agent_name, self.agent_type, response_text)
