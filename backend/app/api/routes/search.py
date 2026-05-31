from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import SearchQuery, SearchResponse, ErrorResponse
from app.services.rag_service import RAGService

router = APIRouter(prefix="/search", tags=["Search"])
_rag_service: RAGService = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


@router.post(
    "",
    response_model=SearchResponse,
    summary="Semantic supply chain incident search",
    description="Search historical supply chain incidents using natural language.",
)
def search_incidents(
    request: SearchQuery,
    service: RAGService = Depends(get_rag_service),
):
    try:
        return service.search(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/hybrid",
    response_model=SearchResponse,
    summary="Hybrid BM25 + semantic search",
    description="Hybrid keyword and semantic search for supply chain incidents.",
)
def hybrid_search(
    request: SearchQuery,
    service: RAGService = Depends(get_rag_service),
):
    request.use_hybrid = True
    try:
        return service.search(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
