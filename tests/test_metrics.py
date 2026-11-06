"""Unit tests for answer and retrieval metrics."""

import unittest

from src.evaluation.metrics import (
    answer_f1,
    exact_match,
    normalize_answer,
    retrieval_metrics,
)


class AnswerMetricTests(unittest.TestCase):

    def test_normalization(self):
        self.assertEqual(
            normalize_answer(
                "The, University of Oxford!"
            ),
            "university of oxford",
        )

    def test_exact_match_ignores_articles_case_and_punctuation(self):
        self.assertEqual(
            exact_match(
                "The University of Oxford.",
                "university of oxford",
            ),
            1.0,
        )

    def test_exact_match_detects_wrong_answer(self):
        self.assertEqual(
            exact_match(
                "London",
                "Paris",
            ),
            0.0,
        )

    def test_partial_answer_f1(self):
        score = answer_f1(
            "Springfield Illinois",
            "Springfield",
        )

        # precision = 1/2
        # recall = 1
        # F1 = 2/3
        self.assertAlmostEqual(
            score,
            2 / 3,
        )

    def test_repeated_tokens_use_multiset_overlap(self):
        score = answer_f1(
            "red red blue",
            "red blue blue",
        )

        # Common multiset = one "red" + one "blue".
        # precision = 2/3
        # recall = 2/3
        self.assertAlmostEqual(
            score,
            2 / 3,
        )

    def test_no_overlap(self):
        self.assertEqual(
            answer_f1(
                "London",
                "Paris",
            ),
            0.0,
        )

    def test_yes_no_special_handling(self):
        self.assertEqual(
            answer_f1(
                "yes indeed",
                "yes",
            ),
            0.0,
        )

        self.assertEqual(
            answer_f1(
                "YES",
                "yes",
            ),
            1.0,
        )

    def test_empty_answers(self):
        self.assertEqual(
            answer_f1(
                "",
                "",
            ),
            1.0,
        )

        self.assertEqual(
            answer_f1(
                "",
                "Paris",
            ),
            0.0,
        )


class RetrievalMetricTests(unittest.TestCase):

    def test_perfect_retrieval(self):
        metrics = retrieval_metrics(
            ["A", "B"],
            ["A", "B"],
        )

        self.assertEqual(
            metrics.precision,
            1.0,
        )

        self.assertEqual(
            metrics.recall,
            1.0,
        )

        self.assertEqual(
            metrics.f1,
            1.0,
        )

    def test_partial_retrieval(self):
        metrics = retrieval_metrics(
            ["A", "X"],
            ["A", "B"],
        )

        self.assertEqual(
            metrics.precision,
            0.5,
        )

        self.assertEqual(
            metrics.recall,
            0.5,
        )

        self.assertEqual(
            metrics.f1,
            0.5,
        )

    def test_extra_documents_reduce_precision(self):
        metrics = retrieval_metrics(
            ["A", "B", "X", "Y"],
            ["A", "B"],
        )

        self.assertEqual(
            metrics.precision,
            0.5,
        )

        self.assertEqual(
            metrics.recall,
            1.0,
        )

        self.assertAlmostEqual(
            metrics.f1,
            2 / 3,
        )

    def test_duplicate_retrieval_does_not_get_extra_credit(self):
        metrics = retrieval_metrics(
            ["A", "A", "B"],
            ["A", "B"],
        )

        self.assertEqual(
            metrics.precision,
            1.0,
        )

        self.assertEqual(
            metrics.recall,
            1.0,
        )

        self.assertEqual(
            metrics.f1,
            1.0,
        )

    def test_no_retrieval(self):
        metrics = retrieval_metrics(
            [],
            ["A", "B"],
        )

        self.assertEqual(
            metrics.precision,
            0.0,
        )

        self.assertEqual(
            metrics.recall,
            0.0,
        )

        self.assertEqual(
            metrics.f1,
            0.0,
        )


if __name__ == "__main__":
    unittest.main()