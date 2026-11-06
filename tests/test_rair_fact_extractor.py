"""Tests for RAIR candidate fact extraction."""

import unittest

from src.rair.fact_extractor import (
    CandidateFact,
    FactExtractionError,
    RAIRFactExtractor,
)
from src.rair.state import (
    Evidence,
)


def make_evidence() -> dict[str, Evidence]:
    return {
        "E1": Evidence(
            document_id="toy:D1",
            title="The Glass Orchard",
            sentence_indices=(0,),
            text=(
                "The Glass Orchard was "
                "written by Mira Solen."
            ),
        ),
        "E2": Evidence(
            document_id="toy:D1",
            title="The Glass Orchard",
            sentence_indices=(1,),
            text=(
                "The novel was published "
                "in 1998."
            ),
        ),
    }


class FactExtractorTests(unittest.TestCase):

    def test_valid_candidate(self):
        candidates = (
            RAIRFactExtractor.parse_payload(
                {
                    "candidates": [
                        {
                            "candidate_id":
                                "C1",
                            "statement":
                                (
                                    "The author of "
                                    "The Glass Orchard "
                                    "is Mira Solen."
                                ),
                            "evidence_ids":
                                ["E1"],
                        }
                    ]
                },
                gap_id="G1",
                evidence_map=make_evidence(),
            )
        )

        self.assertEqual(
            len(candidates),
            1,
        )

        self.assertEqual(
            candidates[0].candidate_id,
            "C1",
        )

        self.assertEqual(
            candidates[0].gap_id,
            "G1",
        )

        self.assertEqual(
            candidates[0]
            .evidence[0]
            .document_id,
            "toy:D1",
        )

    def test_empty_candidates_allowed(self):
        candidates = (
            RAIRFactExtractor.parse_payload(
                {
                    "candidates": []
                },
                gap_id="G1",
                evidence_map=make_evidence(),
            )
        )

        self.assertEqual(
            candidates,
            (),
        )

    def test_candidate_requires_evidence(self):
        with self.assertRaises(
            FactExtractionError
        ):
            RAIRFactExtractor.parse_payload(
                {
                    "candidates": [
                        {
                            "candidate_id":
                                "C1",
                            "statement":
                                "Example claim.",
                            "evidence_ids":
                                [],
                        }
                    ]
                },
                gap_id="G1",
                evidence_map=make_evidence(),
            )

    def test_unknown_evidence_rejected(self):
        with self.assertRaises(
            FactExtractionError
        ):
            RAIRFactExtractor.parse_payload(
                {
                    "candidates": [
                        {
                            "candidate_id":
                                "C1",
                            "statement":
                                "Example claim.",
                            "evidence_ids":
                                ["E99"],
                        }
                    ]
                },
                gap_id="G1",
                evidence_map=make_evidence(),
            )

    def test_duplicate_evidence_rejected(self):
        with self.assertRaises(
            FactExtractionError
        ):
            RAIRFactExtractor.parse_payload(
                {
                    "candidates": [
                        {
                            "candidate_id":
                                "C1",
                            "statement":
                                "Example claim.",
                            "evidence_ids":
                                [
                                    "E1",
                                    "E1",
                                ],
                        }
                    ]
                },
                gap_id="G1",
                evidence_map=make_evidence(),
            )

    def test_candidate_ids_must_be_sequential(self):
        with self.assertRaises(
            FactExtractionError
        ):
            RAIRFactExtractor.parse_payload(
                {
                    "candidates": [
                        {
                            "candidate_id":
                                "C4",
                            "statement":
                                "Example claim.",
                            "evidence_ids":
                                ["E1"],
                        }
                    ]
                },
                gap_id="G1",
                evidence_map=make_evidence(),
            )

    def test_empty_statement_rejected(self):
        with self.assertRaises(
            FactExtractionError
        ):
            RAIRFactExtractor.parse_payload(
                {
                    "candidates": [
                        {
                            "candidate_id":
                                "C1",
                            "statement":
                                "   ",
                            "evidence_ids":
                                ["E1"],
                        }
                    ]
                },
                gap_id="G1",
                evidence_map=make_evidence(),
            )

    def test_extra_field_rejected(self):
        with self.assertRaises(
            FactExtractionError
        ):
            RAIRFactExtractor.parse_payload(
                {
                    "candidates": [
                        {
                            "candidate_id":
                                "C1",
                            "statement":
                                "Example claim.",
                            "evidence_ids":
                                ["E1"],
                            "verified":
                                True,
                        }
                    ]
                },
                gap_id="G1",
                evidence_map=make_evidence(),
            )

    def test_multiple_evidence_items_can_support_claim(self):
        candidates = (
            RAIRFactExtractor.parse_payload(
                {
                    "candidates": [
                        {
                            "candidate_id":
                                "C1",
                            "statement":
                                "Example combined fact.",
                            "evidence_ids":
                                [
                                    "E1",
                                    "E2",
                                ],
                        }
                    ]
                },
                gap_id="G1",
                evidence_map=make_evidence(),
            )
        )

        self.assertEqual(
            len(
                candidates[0].evidence
            ),
            2,
        )

    def test_candidate_fact_direct_validation(self):
        with self.assertRaises(
            ValueError
        ):
            CandidateFact(
                candidate_id="C1",
                statement="",
                gap_id="G1",
                evidence=(
                    make_evidence()["E1"],
                ),
            )


if __name__ == "__main__":
    unittest.main()