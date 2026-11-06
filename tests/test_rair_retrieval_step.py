"""Tests for the RAIR planner -> BM25 retrieval connection."""

import unittest

from src.rair.retrieval_step import (
    RAIRRetrievalStep,
    RetrievalStepError,
)
from src.rair.state import (
    Gap,
    RAIRState,
)
from src.retrieval.document_store import (
    Document,
    DocumentStore,
)


class StubPlanner:
    """Minimal deterministic planner used only by unit tests."""

    def __init__(
        self,
        query: str,
    ) -> None:
        self.query = query

    def plan(
        self,
        state: RAIRState,
        gap: Gap,
    ) -> str:
        return self.query


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
                "Mira Solen was born in the city of Nerava.",
            ),
        ),
        Document(
            document_id="toy:D3",
            question_id="toy",
            title="Weather",
            sentences=(
                "Rain and snow are forms of precipitation.",
            ),
        ),
    )

    return DocumentStore(
        "toy",
        documents,
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

    return state


class RetrievalStepTests(unittest.TestCase):

    def test_budget_exhausted_before_planner_is_called(self):
        state = make_state()
        state.current_round = state.max_rounds
        planner = StubPlanner("Glass Orchard author")
        from unittest.mock import Mock
        planner.plan = Mock(side_effect=AssertionError("Planner must not run"))
        with self.assertRaisesRegex(RetrievalStepError, "maximum rounds"):
            RAIRRetrievalStep(planner, top_k=3).run(state, make_store())
        planner.plan.assert_not_called()

    def test_successful_retrieval(self):
        state = make_state()
        store = make_store()

        step = RAIRRetrievalStep(
            StubPlanner(
                "Glass Orchard author"
            ),
            top_k=3,
        )

        result = step.run(
            state,
            store,
        )

        self.assertEqual(
            result.round_number,
            1,
        )

        self.assertGreater(
            len(result.results),
            0,
        )

        self.assertEqual(
            result.results[0].document.document_id,
            "toy:D1",
        )

    def test_query_attempt_recorded(self):
        state = make_state()

        step = RAIRRetrievalStep(
            StubPlanner(
                "Glass Orchard author"
            ),
            top_k=3,
        )

        step.run(
            state,
            make_store(),
        )

        self.assertEqual(
            len(state.query_history),
            1,
        )

        attempt = state.query_history[0]

        self.assertEqual(
            attempt.gap_id,
            "G1",
        )

        self.assertTrue(
            attempt.success
        )

        self.assertEqual(
            attempt.round_number,
            1,
        )

    def test_no_match_records_failure(self):
        state = make_state()

        step = RAIRRetrievalStep(
            StubPlanner(
                "quantum semiconductor transistor"
            ),
            top_k=3,
        )

        result = step.run(
            state,
            make_store(),
        )

        self.assertEqual(
            result.results,
            (),
        )

        self.assertEqual(
            len(state.failed_attempts()),
            1,
        )

        self.assertEqual(
            state.failed_attempts()[0].failure_reason,
            "No positive-score documents.",
        )

    def test_round_increments(self):
        state = make_state()

        step = RAIRRetrievalStep(
            StubPlanner(
                "Glass Orchard author"
            ),
            top_k=3,
        )

        step.run(
            state,
            make_store(),
        )

        self.assertEqual(
            state.current_round,
            1,
        )

    def test_question_mismatch_rejected(self):
        state = make_state()

        wrong_document = Document(
            document_id="other:D1",
            question_id="other",
            title="Other",
            sentences=(
                "Other evidence.",
            ),
        )

        wrong_store = DocumentStore(
            "other",
            (
                wrong_document,
            ),
        )

        step = RAIRRetrievalStep(
            StubPlanner(
                "Glass Orchard author"
            ),
            top_k=3,
        )

        with self.assertRaises(
            RetrievalStepError
        ):
            step.run(
                state,
                wrong_store,
            )

    def test_invalid_top_k_rejected(self):
        with self.assertRaises(
            ValueError
        ):
            RAIRRetrievalStep(
                StubPlanner(
                    "example"
                ),
                top_k=0,
            )


if __name__ == "__main__":
    unittest.main()
