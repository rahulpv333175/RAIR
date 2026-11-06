"""Tests for RAIR's explicit shared state."""

import unittest

from src.rair.state import (
    Evidence,
    Gap,
    QueryAttempt,
    RAIRState,
    VerifiedFact,
)


def make_state() -> RAIRState:
    state = RAIRState(
        question_id="toy",
        question=(
            "In which city was the author "
            "of The Glass Orchard born?"
        ),
        max_rounds=5,
    )

    state.add_gap(
        Gap(
            gap_id="G1",
            description=(
                "Find the author of "
                "The Glass Orchard."
            ),
            priority="high",
        )
    )

    state.add_gap(
        Gap(
            gap_id="G2",
            description=(
                "Find where that author "
                "was born."
            ),
            priority="high",
            depends_on=("G1",),
        )
    )

    return state


class RAIRStateTests(unittest.TestCase):

    def test_dependency_controls_actionability(self):
        state = make_state()

        self.assertEqual(
            [
                gap.gap_id
                for gap in state.actionable_gaps()
            ],
            ["G1"],
        )

        state.resolve_gap("G1")

        self.assertEqual(
            [
                gap.gap_id
                for gap in state.actionable_gaps()
            ],
            ["G2"],
        )

    def test_verified_fact_requires_evidence(self):
        with self.assertRaises(ValueError):
            VerifiedFact(
                fact_id="F1",
                statement="Mira Solen is the author.",
                gap_id="G1",
                evidence=(),
            )

    def test_add_verified_fact(self):
        state = make_state()

        evidence = Evidence(
            document_id="toy:D1",
            title="The Glass Orchard",
            sentence_indices=(0,),
            text=(
                "The Glass Orchard was "
                "written by Mira Solen."
            ),
        )

        fact = VerifiedFact(
            fact_id="F1",
            statement=(
                "The author of The Glass "
                "Orchard is Mira Solen."
            ),
            gap_id="G1",
            evidence=(evidence,),
        )

        state.add_verified_fact(fact)

        self.assertEqual(
            len(state.verified_facts),
            1,
        )

        self.assertEqual(
            state.verified_facts[0].fact_id,
            "F1",
        )

    def test_unknown_gap_rejected_for_fact(self):
        state = make_state()

        evidence = Evidence(
            document_id="toy:D1",
            title="Example",
            sentence_indices=(0,),
            text="Example evidence.",
        )

        fact = VerifiedFact(
            fact_id="F1",
            statement="Example fact.",
            gap_id="UNKNOWN",
            evidence=(evidence,),
        )

        with self.assertRaises(KeyError):
            state.add_verified_fact(fact)

    def test_failed_query_is_recorded(self):
        state = make_state()

        state.record_query(
            QueryAttempt(
                round_number=1,
                gap_id="G1",
                query=(
                    "Glass Orchard writer"
                ),
                retrieved_document_ids=(),
                success=False,
                failure_reason=(
                    "No positive-score "
                    "documents."
                ),
            )
        )

        self.assertEqual(
            len(state.failed_attempts()),
            1,
        )

    def test_repeated_query_is_rejected(self):
        state = make_state()

        state.record_query(
            QueryAttempt(
                round_number=1,
                gap_id="G1",
                query=(
                    "Glass Orchard author"
                ),
                retrieved_document_ids=(
                    "toy:D1",
                ),
                success=True,
            )
        )

        with self.assertRaises(ValueError):
            state.record_query(
                QueryAttempt(
                    round_number=2,
                    gap_id="G1",
                    query=(
                        "  GLASS orchard AUTHOR  "
                    ),
                    retrieved_document_ids=(
                        "toy:D1",
                    ),
                    success=True,
                )
            )

    def test_round_limit(self):
        state = RAIRState(
            question_id="toy",
            question="Example?",
            max_rounds=2,
        )

        self.assertEqual(
            state.start_next_round(),
            1,
        )

        self.assertEqual(
            state.start_next_round(),
            2,
        )

        with self.assertRaises(RuntimeError):
            state.start_next_round()

    def test_complete_only_when_all_gaps_resolved(self):
        state = make_state()

        self.assertFalse(
            state.is_complete()
        )

        state.resolve_gap("G1")

        self.assertFalse(
            state.is_complete()
        )

        state.resolve_gap("G2")

        self.assertTrue(
            state.is_complete()
        )

    def test_duplicate_gap_rejected(self):
        state = make_state()

        with self.assertRaises(ValueError):
            state.add_gap(
                Gap(
                    gap_id="G1",
                    description="Duplicate.",
                )
            )

    def test_successful_attempt_cannot_have_failure_reason(self):
        with self.assertRaises(ValueError):
            QueryAttempt(
                round_number=1,
                gap_id="G1",
                query="example",
                retrieved_document_ids=(),
                success=True,
                failure_reason="Should not exist.",
            )

    def test_state_serializes(self):
        state = make_state()

        snapshot = state.to_dict()

        self.assertEqual(
            snapshot["question_id"],
            "toy",
        )

        self.assertEqual(
            len(snapshot["gaps"]),
            2,
        )


if __name__ == "__main__":
    unittest.main()