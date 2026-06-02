"""
Embedding model with auto-fallback:
  1. Try OpenAI Embeddings API (text-embedding-3-small / ada-002)
  2. If gateway does not support /embeddings, fall back to local
     sentence-transformers (all-MiniLM-L6-v2) — no API key needed.

This lets you point OPENAI_BASE_URL at a gateway that only
exposes chat completions and still have working embeddings.
"""
import logging
from typing import List, Optional
from functools import lru_cache

import numpy as np

from app.core.config import get_settings, make_openai_client

logger = logging.getLogger(__name__)

_OPENAI_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}
_FALLBACK_MODEL = "all-MiniLM-L6-v2"
_FALLBACK_DIM   = 384
_BATCH_SIZE     = 100


class EmbeddingModel:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self):
        if self._initialised:
            return
        settings = get_settings()
        self._config_model = settings.EMBEDDING_MODEL
        self._openai_client = None
        self._st_model = None
        self._active_model: str = ""
        self._active_dim: int = 0
        self._probe()
        self._initialised = True

    # ── Probe: try OpenAI, fall back to sentence-transformers ─────────────────

    def _probe(self):
        """Try one embedding call (5s timeout) to see if the API endpoint is reachable."""
        if self._config_model in _OPENAI_DIMS:
            try:
                import httpx
                from openai import OpenAI
                from app.core.config import get_settings
                s = get_settings()
                # Short 5-second timeout for the probe — fail fast, don't block startup
                probe_kwargs: dict = {"api_key": s.OPENAI_API_KEY}
                if s.OPENAI_BASE_URL:
                    probe_kwargs["base_url"] = s.OPENAI_BASE_URL
                    probe_kwargs["http_client"] = httpx.Client(
                        verify=False,
                        timeout=httpx.Timeout(5.0, connect=5.0),
                    )
                    probe_kwargs["max_retries"] = 0
                client = OpenAI(**probe_kwargs)
                client.embeddings.create(model=self._config_model, input=["probe"])
                # success — use OpenAI
                self._openai_client = client
                self._active_model = self._config_model
                self._active_dim   = _OPENAI_DIMS[self._config_model]
                logger.info(f"EmbeddingModel: OpenAI API [{self._active_model}] {self._active_dim}-dim")
                return
            except Exception as e:
                logger.warning(
                    f"OpenAI embeddings not available via gateway ({e}). "
                    f"Falling back to local {_FALLBACK_MODEL}."
                )

        # Local sentence-transformers fallback
        self._load_st(_FALLBACK_MODEL)

    def _load_st(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
            self._st_model     = SentenceTransformer(model_name)
            self._active_model = model_name
            self._active_dim   = self._st_model.get_sentence_embedding_dimension()
            logger.info(f"EmbeddingModel: SentenceTransformers [{self._active_model}] {self._active_dim}-dim")
        except ImportError:
            raise RuntimeError(
                "sentence-transformers is not installed and the OpenAI embedding endpoint "
                "is unreachable. Install sentence-transformers or fix the gateway config."
            )

    # ── Public API ─────────────────────────────────────────────────────────────

    def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        if not texts:
            return []
        if self._openai_client:
            return self._encode_openai(texts, normalize)
        return self._encode_st(texts, normalize)

    def encode_single(self, text: str, normalize: bool = True) -> List[float]:
        return self.encode([text], normalize=normalize)[0]

    @property
    def dimension(self) -> int:
        return self._active_dim

    @property
    def model_name(self) -> str:
        return self._active_model

    # ── Backends ───────────────────────────────────────────────────────────────

    def _encode_openai(self, texts: List[str], normalize: bool) -> List[List[float]]:
        all_embs: List[List[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = [t if t.strip() else " " for t in texts[i: i + _BATCH_SIZE]]
            resp = self._openai_client.embeddings.create(model=self._active_model, input=batch)
            batch_embs = [item.embedding for item in sorted(resp.data, key=lambda x: x.index)]
            all_embs.extend(batch_embs)
        if normalize:
            arr = np.array(all_embs, dtype=np.float32)
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            return (arr / norms).tolist()
        return all_embs

    def _encode_st(self, texts: List[str], normalize: bool) -> List[List[float]]:
        embs = self._st_model.encode(
            texts,
            normalize_embeddings=normalize,
            show_progress_bar=False,
            batch_size=64,
        )
        return embs.tolist()


@lru_cache(maxsize=1)
def get_embedding_model() -> EmbeddingModel:
    return EmbeddingModel()
