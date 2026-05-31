from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Supply Chain Risk Intelligence Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    OPENAI_API_KEY: str = ""

    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"
    CHROMA_COLLECTION_NAME: str = "supply_chain_incidents"

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    TOP_K_RESULTS: int = 10
    HYBRID_ALPHA: float = 0.5

    LLM_MODEL: str = "gpt-4o"
    MAX_TOKENS: int = 4096
    MAX_CONTEXT_TOKENS: int = 8000

    DATA_PATH: str = "./data/supply_chain_data.csv"

    RERANKER_TOP_K: int = 5
    ANOMALY_CONTAMINATION: float = 0.05


@lru_cache()
def get_settings() -> Settings:
    return Settings()
