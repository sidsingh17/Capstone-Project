from fastapi import APIRouter, HTTPException, status
from app.models.schemas import AgentAnalysisRequest, OrchestratorResponse
from app.agents.orchestrator import MultiAgentOrchestrator

router = APIRouter(prefix="/agents", tags=["Multi-Agent"])
_orchestrator: MultiAgentOrchestrator = None


def get_orchestrator() -> MultiAgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MultiAgentOrchestrator()
    return _orchestrator


@router.post(
    "/analyze",
    response_model=OrchestratorResponse,
    summary="Multi-agent supply chain risk analysis",
    description=(
        "Runs parallel Supplier Risk, Shipment Analysis, and Inventory Intelligence agents, "
        "synthesized by the Recommendation Agent. Includes A2A escalation workflow."
    ),
)
def multi_agent_analyze(request: AgentAnalysisRequest):
    orchestrator = get_orchestrator()
    try:
        return orchestrator.analyze(
            query=request.query,
            supplier_id=request.supplier_id,
            warehouse_location=request.warehouse_location,
            include_all_agents=request.include_all_agents,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
