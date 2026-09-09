import math
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel


class SearchResult(BaseModel):
    id: str
    text: str
    similarity: float
    metadata: Dict[str, Any] = {}

def tokenize(text: str) -> List[str]:
    """Tokenizes string into normalized words and subword n-grams."""
    words = re.findall(r"\w+", text.lower())
    tokens = list(words)
    # Add character 3-grams for semantic fuzzy overlap
    for word in words:
        if len(word) >= 3:
            tokens.extend([word[i:i+3] for i in range(len(word) - 2)])
    return tokens

def compute_local_embedding(text: str, dimension: int = 128) -> List[float]:
    """
    Computes a deterministic feature vector using token hashing with frequency weighting.
    Provides fast, local, zero-dependency embeddings for similarity checks.
    """
    tokens = tokenize(text)
    if not tokens:
        return [0.0] * dimension

    vector = [0.0] * dimension
    for token in tokens:
        # FNV-1a hash variation
        h = 2166136261
        for char in token.encode("utf-8"):
            h = (h ^ char) * 16777619
            h &= 0xFFFFFFFF
        idx = h % dimension
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vector[idx] += sign

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return [0.0] * dimension
    return [x / norm for x in vector]

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two vectors."""
    if len(v1) != len(v2) or not v1 or not v2:
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot_product / (norm_a * norm_b)))

class VectorIndex:
    """
    In-memory vector store for duplicate-attack filtering and consistency checking.
    """

    def __init__(self, dimension: int = 128):
        self.dimension = dimension
        self.items: List[Dict[str, Any]] = []

    def add(self, item_id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        vector = compute_local_embedding(text, dimension=self.dimension)
        self.items.append({
            "id": item_id,
            "text": text,
            "vector": vector,
            "metadata": metadata or {}
        })

    def search(self, query_text: str, top_k: int = 5, min_threshold: float = 0.0) -> List[SearchResult]:
        query_vec = compute_local_embedding(query_text, dimension=self.dimension)
        scored = []
        for item in self.items:
            sim = cosine_similarity(query_vec, item["vector"])
            if sim >= min_threshold:
                scored.append(SearchResult(
                    id=item["id"],
                    text=item["text"],
                    similarity=sim,
                    metadata=item["metadata"]
                ))
        scored.sort(key=lambda x: x.similarity, reverse=True)
        return scored[:top_k]

    def is_duplicate(self, text: str, threshold: float = 0.75) -> Tuple[bool, Optional[SearchResult]]:
        """
        Determines if text is semantically duplicate of an already indexed entry.
        """
        results = self.search(text, top_k=1, min_threshold=threshold)
        if results:
            return True, results[0]
        return False, None

    def clear(self):
        self.items.clear()
