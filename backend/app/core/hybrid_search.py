import logging
from typing import List, Dict, Any, Optional
import numpy as np
from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.core.embeddings import EmbeddingModel
from app.core.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


class HybridSearchEngine:
    def __init__(self):
        self.settings = get_settings()
        self.embedding_model = EmbeddingModel()
        self.vector_store = VectorStore()
        self._bm25: Optional[BM25Okapi] = None
        self._corpus: List[Dict[str, Any]] = []

    def build_bm25_index(self):
        logger.info("Building BM25 index from vector store corpus…")
        self._corpus = self.vector_store.get_all()
        tokenized = [_tokenize(doc["content"]) for doc in self._corpus]
        self._bm25 = BM25Okapi(tokenized)
        logger.info(f"BM25 index built over {len(self._corpus)} documents")

    def _ensure_bm25(self):
        if self._bm25 is None or not self._corpus:
            self.build_bm25_index()

    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        query_embedding = self.embedding_model.encode_single(query)
        results = self.vector_store.query(query_embedding, top_k=top_k, where=where)
        for r in results:
            r["search_type"] = "semantic"
        return results

    def bm25_search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        self._ensure_bm25()
        tokenized_query = _tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                doc = self._corpus[idx].copy()
                doc["bm25_score"] = float(scores[idx])
                doc["search_type"] = "bm25"
                results.append(doc)
        return results

    def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        alpha: Optional[float] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion of BM25 + semantic results.
        alpha controls semantic weight (0=BM25 only, 1=semantic only).
        """
        if alpha is None:
            alpha = self.settings.HYBRID_ALPHA

        fetch_k = min(top_k * 3, 50)
        semantic_results = self.semantic_search(query, top_k=fetch_k, where=where)
        bm25_results = self.bm25_search(query, top_k=fetch_k)

        # Reciprocal Rank Fusion
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, Any]] = {}
        k = 60

        for rank, doc in enumerate(semantic_results):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + alpha * (1.0 / (k + rank + 1))
            doc_map[doc_id] = doc

        for rank, doc in enumerate(bm25_results):
            doc_id = doc["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + (1 - alpha) * (1.0 / (k + rank + 1))
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:top_k]
        results = []
        for rank, doc_id in enumerate(sorted_ids):
            doc = doc_map[doc_id].copy()
            doc["hybrid_score"] = rrf_scores[doc_id]
            doc["score"] = rrf_scores[doc_id]
            doc["rank"] = rank + 1
            doc["search_type"] = "hybrid"
            results.append(doc)

        return results

    def rerank(self, query: str, results: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Logistics-aware reranking: boost results that match query keywords
        in high-signal fields (incident_type, severity, supplier_id).
        """
        query_lower = query.lower()
        for doc in results:
            meta = doc.get("metadata", {})
            boost = 0.0
            for field in ["incident_type", "severity", "warehouse_location", "supplier_id", "product_category"]:
                val = str(meta.get(field, "")).lower()
                if val and val in query_lower:
                    boost += 0.05
            doc["rerank_score"] = doc.get("score", 0.0) + boost

        return sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)[:top_k]
