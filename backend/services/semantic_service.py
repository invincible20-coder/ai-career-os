"""
Semantic Generalization Layer — TF-IDF based pattern similarity.

Enables the engine to learn from similar patterns:
  Pattern learned: Python + FastAPI
  Should help: Python + Django
  Because they are semantically related.

Uses TF-IDF vectorizer (zero external dependencies).
Can be upgraded to sentence-transformers for higher quality.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field


@dataclass
class SemanticService:
    """TF-IDF based semantic similarity for antecedent signatures.

    Generalizes beyond exact historical matches so that related patterns
    can transfer learning to new, unseen job contexts.
    """

    _vocabulary: dict[str, int] = field(default_factory=dict)
    _idf: dict[str, float] = field(default_factory=dict)
    _document_count: int = 0

    def encode(self, text: str) -> list[float]:
        """Generate a TF-IDF vector for a text string."""
        tokens = self._tokenize(text)
        if not tokens:
            return []

        tf = Counter(tokens)
        max_tf = max(tf.values()) if tf else 1

        # Build vocabulary on the fly if needed
        for token in tokens:
            if token not in self._vocabulary:
                self._vocabulary[token] = len(self._vocabulary)

        vector = [0.0] * len(self._vocabulary)
        for token, count in tf.items():
            idx = self._vocabulary[token]
            tf_score = 0.5 + 0.5 * (count / max_tf)
            idf_score = self._idf.get(token, 1.0)
            vector[idx] = tf_score * idf_score

        return vector

    def similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if not vec_a or not vec_b:
            return 0.0

        # Pad shorter vector
        max_len = max(len(vec_a), len(vec_b))
        a = vec_a + [0.0] * (max_len - len(vec_a))
        b = vec_b + [0.0] * (max_len - len(vec_b))

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0

        return round(max(0.0, min(1.0, dot / (norm_a * norm_b))), 4)

    def text_similarity(self, text_a: str, text_b: str) -> float:
        """Compute semantic similarity between two text strings."""
        vec_a = self.encode(text_a)
        vec_b = self.encode(text_b)
        return self.similarity(vec_a, vec_b)

    def find_similar_patterns(
        self,
        query_text: str,
        pattern_signatures: list[str],
        *,
        top_k: int = 5,
        min_similarity: float = 0.2,
    ) -> list[tuple[str, float]]:
        """Retrieve semantically related patterns from a list of signatures.

        Returns a list of (signature, similarity_score) tuples.
        """
        query_vec = self.encode(query_text)
        if not query_vec:
            return []

        scored: list[tuple[str, float]] = []
        for signature in pattern_signatures:
            sig_vec = self.encode(signature)
            sim = self.similarity(query_vec, sig_vec)
            if sim >= min_similarity:
                scored.append((signature, sim))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]

    def build_index(self, documents: list[str]) -> None:
        """Build the vocabulary and IDF scores from a corpus of documents."""
        self._vocabulary.clear()
        self._idf.clear()
        self._document_count = len(documents)

        if not documents:
            return

        doc_freq: dict[str, int] = defaultdict(int)
        for doc in documents:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                if token not in self._vocabulary:
                    self._vocabulary[token] = len(self._vocabulary)
                doc_freq[token] += 1

        for token, df in doc_freq.items():
            self._idf[token] = math.log((1 + self._document_count) / (1 + df)) + 1

    def semantic_score_for_job(
        self,
        job_signature: str,
        successful_signatures: list[str],
    ) -> float:
        """Compute how semantically similar a job is to known successful patterns."""
        if not successful_signatures:
            return 0.0

        similar = self.find_similar_patterns(
            job_signature,
            successful_signatures,
            top_k=3,
            min_similarity=0.15,
        )
        if not similar:
            return 0.0

        # Weighted average of top matches
        total_weight = 0.0
        total_score = 0.0
        for _, sim in similar:
            total_score += sim * sim  # Weight by similarity squared
            total_weight += sim

        if total_weight < 1e-9:
            return 0.0

        return round(min(1.0, total_score / total_weight), 4)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text into lowercase terms, filtering stop words."""
        stop_words = {
            "and", "the", "for", "with", "role", "job", "a", "an", "in",
            "of", "to", "is", "are", "or", "on", "at", "by", "it",
        }
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        return [t for t in tokens if t not in stop_words and len(t) > 1]

    @staticmethod
    def build_job_signature(
        job_title: str,
        job_category: str,
        job_location: str,
        job_requirements: list[str],
    ) -> str:
        """Build a canonical signature string for a job."""
        parts = []
        location_lower = job_location.lower()
        if "remote" in location_lower:
            parts.append("remote")
        elif job_location.strip():
            parts.append(job_location.strip().split(",")[0].strip().lower())

        if job_category:
            parts.append(job_category.lower())

        title_tokens = re.findall(r"[a-z0-9]+", job_title.lower())
        stop_words = {"senior", "junior", "lead", "staff", "principal", "engineer", "developer"}
        parts.extend(t for t in title_tokens if t not in stop_words and len(t) > 1)

        for req in job_requirements[:4]:
            parts.append(req.lower().strip())

        return " + ".join(dict.fromkeys(parts))
