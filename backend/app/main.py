import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.models.schemas import HealthResponse, IngestionRequest
from app.api.routes import search, recommendations, analytics, agents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Supply Chain Risk Intelligence Assistant…")
    try:
        from app.data.ingestion import DataIngestionPipeline
        pipeline = DataIngestionPipeline()
        if not pipeline.is_ready:
            logger.info("Vector store empty — running initial data ingestion…")
            try:
                count = pipeline.ingest()
                logger.info(f"Initial ingestion complete: {count} documents indexed")
            except FileNotFoundError:
                logger.warning(
                    "Dataset file not found. Run 'python -m app.data.generate_sample' first, "
                    "then POST /api/v1/ingest to load data."
                )
        else:
            logger.info(f"Vector store ready with {pipeline.vector_store.count()} documents")

        # Pre-build BM25 index
        from app.core.hybrid_search import HybridSearchEngine
        engine = HybridSearchEngine()
        if pipeline.is_ready:
            engine.build_bm25_index()
            logger.info("BM25 index ready")

    except Exception as e:
        logger.error(f"Startup error: {e}")

    yield
    logger.info("Shutting down…")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-powered supply chain risk intelligence assistant using RAG, "
        "hybrid search, multi-agent analysis, and explainable recommendations."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(search.router, prefix=API_PREFIX)
app.include_router(recommendations.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(agents.router, prefix=API_PREFIX)


@app.get("/", include_in_schema=False)
def root():
    return {"message": "Supply Chain Risk Intelligence Assistant", "docs": "/docs"}


@app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["System"])
def health_check():
    try:
        from app.core.vector_store import VectorStore
        vs = VectorStore()
        count = vs.count()
        llm_ok = bool(settings.OPENAI_API_KEY)
        return HealthResponse(
            status="healthy",
            version=settings.APP_VERSION,
            vector_store_ready=count > 0,
            llm_connected=llm_ok,
            total_documents=count,
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "detail": str(e)},
        )


@app.post(f"{API_PREFIX}/ingest", tags=["System"], summary="Trigger data ingestion")
def trigger_ingestion(request: IngestionRequest = None):
    try:
        from app.data.ingestion import DataIngestionPipeline
        pipeline = DataIngestionPipeline()
        force = request.force_rebuild if request else False
        data_path = (request.data_path if request else None) or settings.DATA_PATH

        if force:
            pipeline.vector_store.delete_collection()

        count = pipeline.ingest(data_path=data_path, force_rebuild=force)

        from app.core.hybrid_search import HybridSearchEngine
        HybridSearchEngine().build_bm25_index()

        return {"status": "success", "documents_ingested": count}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
