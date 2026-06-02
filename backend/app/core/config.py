from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Supply Chain Risk Intelligence Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: Optional[str] = None          # custom gateway / proxy

    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "supply_chain_incidents"
    CHROMA_BASE_DIR: str = "./chroma_sessions"      # session-scoped store root

    EMBEDDING_MODEL: str = "text-embedding-3-small"

    TOP_K_RESULTS: int = 10
    HYBRID_ALPHA: float = 0.5

    LLM_MODEL: str = "gpt-4o-mini"
    MAX_TOKENS: int = 500
    MAX_CONTEXT_TOKENS: int = 8000

    DATA_PATH: str = "./data/supply_chain_data.csv"

    RERANKER_TOP_K: int = 5
    ANOMALY_CONTAMINATION: float = 0.05


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def make_openai_client():
    """
    Create an OpenAI client.
    When OPENAI_BASE_URL is set (custom gateway), SSL verification is disabled
    because corporate/educational gateways often use certificates not in certifi.
    """
    from openai import OpenAI
    import httpx
    s = get_settings()
    kwargs: dict = {"api_key": s.OPENAI_API_KEY}
    if s.OPENAI_BASE_URL:
        kwargs["base_url"] = s.OPENAI_BASE_URL
        kwargs["http_client"] = httpx.Client(verify=False)
    return OpenAI(**kwargs)
