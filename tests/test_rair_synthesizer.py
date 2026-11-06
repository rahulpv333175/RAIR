"""Tests for RAIR final answer synthesis validation."""

import unittest

from src.rair.synthesizer import (
    RAIRSynthesizer,
    SynthesisError,
)


class SynthesizerTests(unittest.TestCase):

    def test_valid_answer(self):
        result = RAIRSynthesizer.parse_payload(
            {
                "answer": "Nerava",
                "citations": [
                    "F1",
                    "F2",
                ],
                "abstain": False,
            },
            valid_fact_ids={
                "F1",
                "F2",
            },
        )

        self.assertEqual(
            result.answer,
            "Nerava",
        )

        self.assertEqual(
            result.citations,
            (
                "F1",
                "F2",
            ),
        )

        self.assertFalse(
            result.abstain
        )

    def test_valid_abstention(self):
        result = RAIRSynthesizer.parse_payload(
            {
                "answer": "",
                "citations": [],
                "abstain": True,
            },
            valid_fact_ids={
                "F1",
            },
        )

        self.assertTrue(
            result.abstain
        )

    def test_unknown_citation_rejected(self):
        with self.assertRaises(
            SynthesisError
        ):
            RAIRSynthesizer.parse_payload(
                {
                    "answer": "Nerava",
                    "citations": [
                        "F99",
                    ],
                    "abstain": False,
                },
                valid_fact_ids={
                    "F1",
                    "F2",
                },
            )

    def test_answer_requires_citation(self):
        with self.assertRaises(
            SynthesisError
        ):
            RAIRSynthesizer.parse_payload(
                {
                    "answer": "Nerava",
                    "citations": [],
                    "abstain": False,
                },
                valid_fact_ids={
                    "F1",
                    "F2",
                },
            )

    def test_abstention_requires_empty_answer(self):
        with self.assertRaises(
            SynthesisError
        ):
            RAIRSynthesizer.parse_payload(
                {
                    "answer": "Nerava",
                    "citations": [],
                    "abstain": True,
                },
                valid_fact_ids={
                    "F1",
                },
            )

    def test_abstention_requires_no_citations(self):
        with self.assertRaises(
            SynthesisError
        ):
            RAIRSynthesizer.parse_payload(
                {
                    "answer": "",
                    "citations": [
                        "F1",
                    ],
                    "abstain": True,
                },
                valid_fact_ids={
                    "F1",
                },
            )

    def test_duplicate_citations_rejected(self):
        with self.assertRaises(
            SynthesisError
        ):
            RAIRSynthesizer.parse_payload(
                {
                    "answer": "Nerava",
                    "citations": [
                        "F1",
                        "F1",
                    ],
                    "abstain": False,
                },
                valid_fact_ids={
                    "F1",
                },
            )

    def test_extra_field_rejected(self):
        with self.assertRaises(
            SynthesisError
        ):
            RAIRSynthesizer.parse_payload(
                {
                    "answer": "Nerava",
                    "citations": [
                        "F1",
                    ],
                    "abstain": False,
                    "confidence": 0.9,
                },
                valid_fact_ids={
                    "F1",
                },
            )


if __name__ == "__main__":
    unittest.main()