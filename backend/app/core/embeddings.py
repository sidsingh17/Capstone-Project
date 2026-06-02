"""
OpenAI Embeddings API wrapper (text-embedding-3-small / text-embedding-3-large).
Replaces sentence-transformers — no local model download required.
"""
import logging
from typing import List
from functools import lru_cache

import numpy as np

from app.core.config import get_settings, make_openai_client

logger = logging.getLogger(__name__)

# Dimensions for known OpenAI embedding models
_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}

_EMBED_BATCH_SIZE = 100   # safe well under the 2048-input API limit


class EmbeddingModel:
    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            settings = get_settings()
            self._model = settings.EMBEDDING_MODEL
            self._client = make_openai_client()
            logger.info(f"EmbeddingModel ready: {self._model} ({self.dimension}-dim) via OpenAI API")

    def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[i: i + _EMBED_BATCH_SIZE]
            # Replace empty strings (OpenAI rejects them)
            batch = [t if t.strip() else " " for t in batch]
            response = self._client.embeddings.create(model=self._model, input=batch)
            # response.data is sorted by index
            batch_embs = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
            all_embeddings.extend(batch_embs)

        if normalize:
            arr = np.array(all_embeddings, dtype=np.float32)
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            all_embeddings = (arr / norms).tolist()

        return all_embeddings

    def encode_single(self, text: str, normalize: bool = True) -> List[float]:
        return self.encode([text], normalize=normalize)[0]

    @property
    def dimension(self) -> int:
        return _DIMENSIONS.get(self._model, 1536)

    @property
    def model_name(self) -> str:
        return self._model


@lru_cache(maxsize=1)
def get_embedding_model() -> EmbeddingModel:
    return EmbeddingModel()
