"""Lightweight BM25 retrieval over one question's document pool."""

import math
import re
from collections import Counter
from dataclasses import dataclass

from src.retrieval.document_store import Document, DocumentStore
from src.evaluation.budget import RunBudget


_TOKEN_PATTERN = re.compile(r"\b\w+\b", flags=re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Simple deterministic tokenizer shared by indexing and queries."""
    return _TOKEN_PATTERN.findall(text.lower())


@dataclass(frozen=True)
class RetrievalResult:
    rank: int
    document: Document
    score: float


class BM25Retriever:
    """BM25 index for exactly one question's document pool."""

    def __init__(
        self,
        store: DocumentStore,
        *,
        k1: float = 1.5,
        b: float = 0.75,
        budget: RunBudget | None = None,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive.")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1.")

        self.store = store
        self.budget = budget
        self.k1 = float(k1)
        self.b = float(b)

        self._documents = store.all_documents()
        self._tokens: list[list[str]] = []
        self._term_frequencies: list[Counter[str]] = []
        self._document_frequency: Counter[str] = Counter()

        for document in self._documents:
            tokens = tokenize(document.search_text)
            self._tokens.append(tokens)

            frequencies = Counter(tokens)
            self._term_frequencies.append(frequencies)

            for term in frequencies:
                self._document_frequency[term] += 1

        self._document_lengths = [len(tokens) for tokens in self._tokens]

        if self._document_lengths:
            self._average_document_length = (
                sum(self._document_lengths) / len(self._document_lengths)
            )
        else:
            self._average_document_length = 0.0

    @property
    def num_documents(self) -> int:
        return len(self._documents)

    @property
    def average_document_length(self) -> float:
        return self._average_document_length

    def idf(self, term: str) -> float:
        """Return BM25 inverse document frequency for one normalized term."""
        normalized = tokenize(term)

        if len(normalized) != 1:
            raise ValueError("idf() expects exactly one token.")

        token = normalized[0]
        n = self.num_documents
        df = self._document_frequency.get(token, 0)

        return math.log(
            1.0 + (n - df + 0.5) / (df + 0.5)
        )

    def score_document(
        self,
        query: str,
        document_index: int,
    ) -> float:
        """Score one indexed document against a query."""
        if not 0 <= document_index < self.num_documents:
            raise IndexError("document_index is outside the document pool.")

        query_terms = Counter(tokenize(query))

        if not query_terms:
            return 0.0

        frequencies = self._term_frequencies[document_index]
        document_length = self._document_lengths[document_index]

        if self._average_document_length == 0:
            return 0.0

        score = 0.0

        for term, query_frequency in query_terms.items():
            term_frequency = frequencies.get(term, 0)

            if term_frequency == 0:
                continue

            denominator = (
                term_frequency
                + self.k1
                * (
                    1.0
                    - self.b
                    + self.b
                    * document_length
                    / self._average_document_length
                )
            )

            contribution = (
                self.idf(term)
                * term_frequency
                * (self.k1 + 1.0)
                / denominator
            )

            # Preserve repeated query terms deterministically.
            score += query_frequency * contribution

        return score

    def search(
        self,
        query: str,
        *,
        top_k: int = 3,
    ) -> list[RetrievalResult]:
        """Return the highest-scoring documents.

        Ties are resolved by original document-pool order.
        Zero-score documents are not returned.
        """
        if not isinstance(query, str):
            raise TypeError("query must be a string.")
        if type(top_k) is not int or top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        if self.budget is not None:
            self.budget.consume_retrieval()

        scored: list[tuple[int, float]] = []

        for index in range(self.num_documents):
            score = self.score_document(query, index)

            if score > 0:
                scored.append((index, score))

        scored.sort(key=lambda item: (-item[1], item[0]))

        results = []

        for rank, (index, score) in enumerate(scored[:top_k], start=1):
            results.append(
                RetrievalResult(
                    rank=rank,
                    document=self._documents[index],
                    score=score,
                )
            )

        return results
