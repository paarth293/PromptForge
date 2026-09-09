import json
import logging
import os
import random
from typing import Any, Dict, List, Optional

logger = logging.getLogger("promptforge.services.seed_corpus")

DEFAULT_SEED_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "seed_corpus.json")
)


class SeedCorpusService:
    """
    Manages access to the static seed corpus of known attack patterns
    (OWASP LLM01, jailbreaks, prompt extractions, tool abuse, and multilingual evasion).
    """

    def __init__(self, file_path: str = DEFAULT_SEED_FILE):
        self.file_path = file_path
        self._corpus: List[Dict[str, Any]] = []
        self.load_corpus()

    def load_corpus(self):
        if not os.path.exists(self.file_path):
            logger.warning(f"Seed corpus file not found at {self.file_path}")
            self._corpus = []
            return

        with open(self.file_path, "r", encoding="utf-8") as f:
            self._corpus = json.load(f)
        logger.info(f"Loaded {len(self._corpus)} attack patterns from seed corpus.")

    def get_all_seeds(self) -> List[Dict[str, Any]]:
        return list(self._corpus)

    def get_seeds_by_category(self, category: str) -> List[Dict[str, Any]]:
        cat_lower = category.lower()
        return [s for s in self._corpus if s.get("category", "").lower() == cat_lower]

    def get_seeds_by_difficulty(self, difficulty: str) -> List[Dict[str, Any]]:
        diff_lower = difficulty.lower()
        return [s for s in self._corpus if s.get("difficulty", "").lower() == diff_lower]

    def get_sample_seeds(
        self,
        count: int = 5,
        category: Optional[str] = None,
        difficulty: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        candidates = self._corpus
        if category:
            candidates = [s for s in candidates if s.get("category", "").lower() == category.lower()]
        if difficulty:
            candidates = [s for s in candidates if s.get("difficulty", "").lower() == difficulty.lower()]

        if not candidates:
            return []
        return random.sample(candidates, min(count, len(candidates)))

    def get_category_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for s in self._corpus:
            cat = s.get("category", "unknown")
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def get_difficulty_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for s in self._corpus:
            diff = s.get("difficulty", "unknown")
            counts[diff] = counts.get(diff, 0) + 1
        return counts


_default_seed_service: Optional[SeedCorpusService] = None

def get_seed_corpus_service() -> SeedCorpusService:
    global _default_seed_service
    if _default_seed_service is None:
        _default_seed_service = SeedCorpusService()
    return _default_seed_service
