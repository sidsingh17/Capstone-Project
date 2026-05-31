import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.core.config import get_settings
from app.data.preprocessing import load_and_clean, enrich_dataframe
from app.data.chunking import dataframe_to_documents
from app.core.embeddings import EmbeddingModel
from app.core.vector_store import VectorStore

logger = logging.getLogger(__name__)


class DataIngestionPipeline:
    def __init__(self):
        self.settings = get_settings()
        self.embedding_model = EmbeddingModel()
        self.vector_store = VectorStore()

    def ingest(self, data_path: Optional[str] = None, force_rebuild: bool = False) -> int:
        path = data_path or self.settings.DATA_PATH

        if not force_rebuild and self.vector_store.count() > 0:
            logger.info(f"Vector store already populated ({self.vector_store.count()} docs). Skipping ingestion.")
            return self.vector_store.count()

        logger.info(f"Loading data from {path}")
        df = load_and_clean(path)
        df = enrich_dataframe(df)
        logger.info(f"Loaded {len(df)} records after cleaning")

        documents = dataframe_to_documents(df)
        logger.info(f"Created {len(documents)} document chunks")

        batch_size = 100
        total_added = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i: i + batch_size]
            texts = [d["content"] for d in batch]
            embeddings = self.embedding_model.encode(texts)
            self.vector_store.add_documents(batch, embeddings)
            total_added += len(batch)
            logger.info(f"Ingested {total_added}/{len(documents)} documents")

        logger.info(f"Ingestion complete. Total documents: {total_added}")
        return total_added

    def get_all_documents(self) -> List[Dict[str, Any]]:
        return self.vector_store.get_all()

    @property
    def is_ready(self) -> bool:
        return self.vector_store.count() > 0
