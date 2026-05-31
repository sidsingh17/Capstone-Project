"""
Pure-numpy vector store — same interface as the original ChromaDB wrapper.
Persists documents as JSON and embeddings as .npy files.
No C++ compilation required.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class VectorStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ready = False
        return cls._instance

    def __init__(self):
        if self._ready:
            return
        settings = get_settings()
        self._persist_dir = Path(settings.CHROMA_PERSIST_DIRECTORY)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._docs_file = self._persist_dir / "documents.json"
        self._embs_file = self._persist_dir / "embeddings.npy"
        self._documents: List[Dict[str, Any]] = []
        self._embeddings: Optional[np.ndarray] = None
        self._id_to_idx: Dict[str, int] = {}
        self._load()
        self._ready = True
        logger.info(f"VectorStore ready — {len(self._documents)} documents")

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load(self):
        if self._docs_file.exists():
            with open(self._docs_file, encoding="utf-8") as f:
                self._documents = json.load(f)
            self._id_to_idx = {d["id"]: i for i, d in enumerate(self._documents)}
        if self._embs_file.exists() and self._documents:
            self._embeddings = np.load(str(self._embs_file)).astype(np.float32)

    def _save(self):
        with open(self._docs_file, "w", encoding="utf-8") as f:
            json.dump(self._documents, f, ensure_ascii=False)
        if self._embeddings is not None:
            np.save(str(self._embs_file), self._embeddings)

    # ── Write ──────────────────────────────────────────────────────────────────

    def add_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]]):
        if not documents:
            return

        new_docs: List[Dict[str, Any]] = []
        new_embs: List[List[float]] = []

        for doc, emb in zip(documents, embeddings):
            doc_id = doc["id"]
            if doc_id in self._id_to_idx:
                # Upsert: overwrite in-place
                idx = self._id_to_idx[doc_id]
                self._documents[idx] = doc
                if self._embeddings is not None:
                    self._embeddings[idx] = np.array(emb, dtype=np.float32)
            else:
                new_docs.append(doc)
                new_embs.append(emb)

        if new_docs:
            start = len(self._documents)
            self._documents.extend(new_docs)
            for i, d in enumerate(new_docs):
                self._id_to_idx[d["id"]] = start + i

            arr = np.array(new_embs, dtype=np.float32)
            self._embeddings = arr if self._embeddings is None else np.vstack([self._embeddings, arr])

        self._save()

    # ── Read ───────────────────────────────────────────────────────────────────

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        if not self._documents or self._embeddings is None:
            return []

        candidate_indices = self._filter_indices(where)
        if not candidate_indices:
            return []

        q = np.array(query_embedding, dtype=np.float32)
        q_norm = q / (np.linalg.norm(q) + 1e-9)

        embs = self._embeddings[candidate_indices]
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        embs_normed = embs / (norms + 1e-9)
        scores = embs_normed @ q_norm                         # cosine similarity

        top_n = min(top_k, len(candidate_indices))
        top_local = np.argsort(scores)[::-1][:top_n]

        results = []
        for local_idx in top_local:
            global_idx = candidate_indices[local_idx]
            doc = self._documents[global_idx]
            score = float(scores[local_idx])
            results.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc["metadata"],
                "distance": 1.0 - score,
                "score": score,
            })
        return results

    def get_all(self) -> List[Dict[str, Any]]:
        return [{"id": d["id"], "content": d["content"], "metadata": d["metadata"]}
                for d in self._documents]

    def count(self) -> int:
        return len(self._documents)

    # ── Metadata filtering ─────────────────────────────────────────────────────

    def _filter_indices(self, where: Optional[Dict[str, Any]]) -> List[int]:
        if not where:
            return list(range(len(self._documents)))
        return [i for i, d in enumerate(self._documents) if self._matches(d["metadata"], where)]

    def _matches(self, meta: Dict[str, Any], where: Dict[str, Any]) -> bool:
        if "$and" in where:
            return all(self._matches(meta, cond) for cond in where["$and"])
        if "$or" in where:
            return any(self._matches(meta, cond) for cond in where["$or"])
        for key, condition in where.items():
            meta_val = str(meta.get(key, ""))
            if isinstance(condition, dict):
                op, val = next(iter(condition.items()))
                if op == "$eq" and meta_val != str(val):
                    return False
                elif op == "$ne" and meta_val == str(val):
                    return False
            else:
                if meta_val != str(condition):
                    return False
        return True

    # ── Admin ──────────────────────────────────────────────────────────────────

    def delete_collection(self):
        self._documents = []
        self._embeddings = None
        self._id_to_idx = {}
        if self._docs_file.exists():
            self._docs_file.unlink()
        if self._embs_file.exists():
            self._embs_file.unlink()
        logger.info("VectorStore collection cleared")

    def build_where_filter(
        self,
        supplier_id: Optional[str] = None,
        warehouse_location: Optional[str] = None,
        shipment_status: Optional[str] = None,
        severity: Optional[str] = None,
        incident_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        conditions = []
        if supplier_id:
            conditions.append({"supplier_id": {"$eq": supplier_id}})
        if warehouse_location:
            conditions.append({"warehouse_location": {"$eq": warehouse_location}})
        if shipment_status:
            conditions.append({"shipment_status": {"$eq": shipment_status}})
        if severity:
            conditions.append({"severity": {"$eq": severity}})
        if incident_type:
            conditions.append({"incident_type": {"$eq": incident_type}})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}
