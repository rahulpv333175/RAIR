"""Tests for the RAIR verification gate."""

import unittest

from src.rair.fact_extractor import (
    CandidateFact,
)
from src.rair.state import (
    Evidence,
    Gap,
    RAIRState,
)
from src.rair.verifier import (
    RAIRVerifier,
    VerificationError,
)


def make_evidence() -> Evidence:
    return Evidence(
        document_id="toy:D1",
        title="The Glass Orchard",
        sentence_indices=(0,),
        text=(
            "The Glass Orchard was "
            "written by Mira Solen."
        ),
    )


def make_candidate(
    statement: str = (
        "The author of The Glass Orchard "
        "is Mira Solen."
    ),
) -> CandidateFact:
    return CandidateFact(
        candidate_id="C1",
        statement=statement,
        gap_id="G1",
        evidence=(
            make_evidence(),
        ),
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
                "Identify the author of "
                "The Glass Orchard."
            ),
            priority="high",
        )
    )

    state.add_gap(
        Gap(
            gap_id="G2",
            description=(
                "Identify the birth city "
                "of the author identified "
                "in G1."
            ),
            priority="high",
            depends_on=("G1",),
        )
    )

    return state


def decision_payload(
    *,
    supported: bool = True,
    relevant: bool = True,
    answer_type_ok: bool = True,
    placeholder: bool = False,
    resolves_gap: bool = True,
) -> dict:
    return {
        "decisions": [
            {
                "candidate_id": "C1",
                "supported_by_evidence":
                    supported,
                "relevant_to_gap":
                    relevant,
                "answer_type_ok":
                    answer_type_ok,
                "contains_unresolved_placeholder":
                    placeholder,
                "resolves_gap":
                    resolves_gap,
                "reason":
                    "Synthetic verification reason.",
            }
        ]
    }


class VerifierTests(unittest.TestCase):

    def test_supported_candidate_is_accepted(self):
        candidate = make_candidate()

        decisions = RAIRVerifier.parse_payload(
            decision_payload(),
            candidates=(
                candidate,
            ),
        )

        self.assertTrue(
            decisions[0].accepted
        )

        self.assertTrue(
            decisions[0].resolves_gap
        )

    def test_unsupported_candidate_is_rejected(self):
        candidate = make_candidate()

        decisions = RAIRVerifier.parse_payload(
            decision_payload(
                supported=False,
                resolves_gap=False,
            ),
            candidates=(
                candidate,
            ),
        )

        self.assertFalse(
            decisions[0].accepted
        )

    def test_wrong_answer_type_is_rejected(self):
        candidate = make_candidate()

        decisions = RAIRVerifier.parse_payload(
            decision_payload(
                answer_type_ok=False,
                resolves_gap=False,
            ),
            candidates=(
                candidate,
            ),
        )

        self.assertFalse(
            decisions[0].accepted
        )

    def test_unresolved_placeholder_is_rejected(self):
        candidate = make_candidate()

        decisions = RAIRVerifier.parse_payload(
            decision_payload(
                placeholder=True,
                resolves_gap=False,
            ),
            candidates=(
                candidate,
            ),
        )

        self.assertFalse(
            decisions[0].accepted
        )

    def test_rejected_candidate_cannot_resolve_gap(self):
        candidate = make_candidate()

        with self.assertRaises(
            VerificationError
        ):
            RAIRVerifier.parse_payload(
                decision_payload(
                    supported=False,
                    resolves_gap=True,
                ),
                candidates=(
                    candidate,
                ),
            )

    def test_wrong_candidate_id_rejected(self):
        candidate = make_candidate()

        payload = decision_payload()

        payload["decisions"][0][
            "candidate_id"
        ] = "C99"

        with self.assertRaises(
            VerificationError
        ):
            RAIRVerifier.parse_payload(
                payload,
                candidates=(
                    candidate,
                ),
            )

    def test_missing_decision_rejected(self):
        candidate = make_candidate()

        with self.assertRaises(
            VerificationError
        ):
            RAIRVerifier.parse_payload(
                {
                    "decisions": []
                },
                candidates=(
                    candidate,
                ),
            )

    def test_extra_field_rejected(self):
        candidate = make_candidate()

        payload = decision_payload()

        payload["decisions"][0][
            "confidence"
        ] = 0.99

        with self.assertRaises(
            VerificationError
        ):
            RAIRVerifier.parse_payload(
                payload,
                candidates=(
                    candidate,
                ),
            )

    def test_accepted_fact_is_promoted_and_gap_resolved(self):
        state = make_state()
        candidate = make_candidate()

        decisions = RAIRVerifier.parse_payload(
            decision_payload(),
            candidates=(
                candidate,
            ),
        )

        promoted = RAIRVerifier.commit_decisions(
            state,
            state.get_gap("G1"),
            (
                candidate,
            ),
            decisions,
        )

        self.assertEqual(
            len(promoted),
            1,
        )

        self.assertEqual(
            len(state.verified_facts),
            1,
        )

        self.assertEqual(
            state.verified_facts[0].fact_id,
            "F1",
        )

        self.assertTrue(
            state.get_gap("G1").resolved
        )

        self.assertEqual(
            [
                gap.gap_id
                for gap
                in state.actionable_gaps()
            ],
            ["G2"],
        )

    def test_accepted_nonresolving_fact_does_not_close_gap(self):
        state = make_state()
        candidate = make_candidate()

        decisions = RAIRVerifier.parse_payload(
            decision_payload(
                resolves_gap=False,
            ),
            candidates=(
                candidate,
            ),
        )

        promoted = RAIRVerifier.commit_decisions(
            state,
            state.get_gap("G1"),
            (
                candidate,
            ),
            decisions,
        )

        self.assertEqual(
            len(promoted),
            1,
        )

        self.assertFalse(
            state.get_gap("G1").resolved
        )

    def test_rejected_fact_is_not_promoted(self):
        state = make_state()
        candidate = make_candidate(
            statement=(
                "The author of The Glass "
                "Orchard is Rowan Vale."
            )
        )

        decisions = RAIRVerifier.parse_payload(
            decision_payload(
                supported=False,
                resolves_gap=False,
            ),
            candidates=(
                candidate,
            ),
        )

        promoted = RAIRVerifier.commit_decisions(
            state,
            state.get_gap("G1"),
            (
                candidate,
            ),
            decisions,
        )

        self.assertEqual(
            promoted,
            (),
        )

        self.assertEqual(
            state.verified_facts,
            [],
        )

        self.assertFalse(
            state.get_gap("G1").resolved
        )


if __name__ == "__main__":
    unittest.main()