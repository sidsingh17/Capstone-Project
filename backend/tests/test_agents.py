import pytest
from unittest.mock import MagicMock, patch
from app.agents.supplier_risk_agent import _parse_agent_result, _extract_bullets
from app.agents.orchestrator import _compute_consolidated_risk, _merge_recommendations
from app.models.schemas import AgentResult


class TestAgentParsing:
    def test_parse_agent_result_with_full_response(self):
        text = """
RISK_SCORE: 0.72
FINDINGS:
- Supplier S001 has 3 critical delays in past 6 months
- Single-source dependency for electronic components
- On-time delivery rate dropped to 65%
RECOMMENDATIONS:
- Identify alternative suppliers for critical components
- Negotiate improved SLA terms with S001
- Implement dual-sourcing strategy
ESCALATE: YES
"""
        result = _parse_agent_result("SupplierRiskAgent", "supplier_risk", text)
        assert result.risk_score == pytest.approx(0.72)
        assert result.escalated is True
        assert len(result.findings) >= 2
        assert len(result.recommendations) >= 2

    def test_parse_agent_result_no_escalation(self):
        text = "RISK_SCORE: 0.3\nFINDINGS:\n- Minor delays\nRECOMMENDATIONS:\n- Monitor closely\nESCALATE: NO"
        result = _parse_agent_result("TestAgent", "test", text)
        assert result.escalated is False
        assert result.risk_score == pytest.approx(0.3)

    def test_parse_agent_result_missing_score(self):
        text = "Analysis shows some supplier risk. No score provided."
        result = _parse_agent_result("TestAgent", "test", text)
        assert result.risk_score == 0.5

    def test_extract_bullets(self):
        text = "FINDINGS:\n- Item one\n- Item two\n- Item three\nNEXT_SECTION: other"
        items = _extract_bullets(text, "FINDINGS")
        assert len(items) == 3
        assert "Item one" in items


class TestOrchestrator:
    def _make_result(self, agent_type, risk_score, escalated=False):
        return AgentResult(
            agent_name=f"{agent_type}Agent",
            agent_type=agent_type,
            findings=["test finding"],
            risk_score=risk_score,
            recommendations=["test rec"],
            escalated=escalated,
        )

    def test_consolidated_risk_weighted(self):
        results = [
            self._make_result("supplier_risk", 0.8),
            self._make_result("shipment_analysis", 0.5),
            self._make_result("inventory_intelligence", 0.6),
        ]
        score = _compute_consolidated_risk(results)
        assert 0.5 < score < 0.8

    def test_consolidated_risk_empty(self):
        assert _compute_consolidated_risk([]) == 0.0

    def test_merged_recommendations_dedup(self):
        results = [
            self._make_result("supplier_risk", 0.5),
            self._make_result("shipment_analysis", 0.5),
        ]
        results[0].recommendations = ["Contact supplier S001 immediately", "Review SLA terms"]
        results[1].recommendations = ["Contact supplier S001 immediately", "Check route status"]
        merged = _merge_recommendations(results)
        contact_recs = [r for r in merged if "Contact supplier S001" in r]
        assert len(contact_recs) == 1

    def test_merged_recommendations_no_empty(self):
        results = [self._make_result("supplier_risk", 0.5)]
        results[0].recommendations = ["valid recommendation"]
        merged = _merge_recommendations(results)
        assert len(merged) >= 1
