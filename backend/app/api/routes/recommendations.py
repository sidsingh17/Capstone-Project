from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import RecommendationRequest, RecommendationResponse, SearchQuery
from app.services.rag_service import RAGService
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
_rag_service: RAGService = None
_eval_service: EvaluationService = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def get_eval_service() -> EvaluationService:
    global _eval_service
    if _eval_service is None:
        _eval_service = EvaluationService()
    return _eval_service


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="Generate risk mitigation recommendations",
    description="Generate AI-powered supply chain risk recommendations with optional quality evaluation.",
)
def generate_recommendations(
    request: RecommendationRequest,
    rag: RAGService = Depends(get_rag_service),
    evaluator: EvaluationService = Depends(get_eval_service),
):
    try:
        response = rag.generate_recommendations(request)

        if request.evaluate_quality:
            context_texts = [r.content for r in
                             rag.search(SearchQuery(query=request.query, top_k=5)).results]
            judge_result = evaluator.llm_judge_recommendations(
                request.query,
                response,
                [{"content": t} for t in context_texts],
            )
            response.evaluation_score = judge_result.get("overall_score")
            response.llm_judge_verdict = judge_result.get("verdict")

        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
