"""Unit tests for the lightweight BM25 retriever."""

import unittest

from src.retrieval.bm25 import BM25Retriever, tokenize
from src.retrieval.document_store import Document, DocumentStore


def make_store() -> DocumentStore:
    documents = (
        Document(
            document_id="toy:D1",
            question_id="toy",
            title="The Glass Orchard",
            sentences=(
                "The Glass Orchard was written by Mira Solen.",
            ),
        ),
        Document(
            document_id="toy:D2",
            question_id="toy",
            title="Mira Solen",
            sentences=(
                "Mira Solen was born in Nerava.",
            ),
        ),
        Document(
            document_id="toy:D3",
            question_id="toy",
            title="Weather",
            sentences=(
                "Rain is a form of precipitation.",
            ),
        ),
    )

    return DocumentStore("toy", documents)


class BM25Tests(unittest.TestCase):
    def test_tokenizer(self):
        self.assertEqual(
            tokenize("Mira Solen's birthplace: Nerava!"),
            ["mira", "solen", "s", "birthplace", "nerava"],
        )

    def test_author_query_ranks_book_document_first(self):
        retriever = BM25Retriever(make_store())

        results = retriever.search(
            "Glass Orchard author",
            top_k=3,
        )

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(
            results[0].document.document_id,
            "toy:D1",
        )
        self.assertGreater(results[0].score, 0)

    def test_birthplace_query_ranks_person_document_first(self):
        retriever = BM25Retriever(make_store())

        results = retriever.search(
            "Mira Solen born Nerava",
            top_k=3,
        )

        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(
            results[0].document.document_id,
            "toy:D2",
        )

    def test_irrelevant_query_returns_empty_results(self):
        retriever = BM25Retriever(make_store())

        results = retriever.search(
            "quantum semiconductor transistor",
            top_k=3,
        )

        self.assertEqual(results, [])

    def test_top_k_is_respected(self):
        retriever = BM25Retriever(make_store())

        results = retriever.search(
            "Mira Solen",
            top_k=1,
        )

        self.assertEqual(len(results), 1)

    def test_results_are_sorted_by_score(self):
        retriever = BM25Retriever(make_store())

        results = retriever.search(
            "Mira Solen",
            top_k=3,
        )

        scores = [result.score for result in results]

        self.assertEqual(
            scores,
            sorted(scores, reverse=True),
        )

    def test_ties_preserve_original_pool_order(self):
        documents = (
            Document(
                document_id="tie:D1",
                question_id="tie",
                title="Alpha",
                sentences=("sharedterm",),
            ),
            Document(
                document_id="tie:D2",
                question_id="tie",
                title="Beta",
                sentences=("sharedterm",),
            ),
        )

        retriever = BM25Retriever(
            DocumentStore("tie", documents)
        )

        results = retriever.search(
            "sharedterm",
            top_k=2,
        )

        self.assertEqual(
            [result.document.document_id for result in results],
            ["tie:D1", "tie:D2"],
        )

    def test_invalid_top_k_is_rejected(self):
        retriever = BM25Retriever(make_store())

        with self.assertRaises(ValueError):
            retriever.search("Mira", top_k=0)


if __name__ == "__main__":
    unittest.main()