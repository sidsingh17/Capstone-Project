import logging
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from functools import lru_cache

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingModel:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._model is None:
            settings = get_settings()
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
            self._model = SentenceTransformer(settings.EMBEDDING_MODEL)
            logger.info("Embedding model loaded")

    def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=False,
            batch_size=64,
        )
        return embeddings.tolist()

    def encode_single(self, text: str, normalize: bool = True) -> List[float]:
        return self.encode([text], normalize=normalize)[0]

    @property
    def dimension(self) -> int:
        return self._model.get_sentence_embedding_dimension()


@lru_cache(maxsize=1)
def get_embedding_model() -> EmbeddingModel:
    return EmbeddingModel()
