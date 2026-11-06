"""Tests for RAIR query planning and gap selection."""

import unittest

from src.rair.query_planner import (
    QueryPlanningError,
    RAIRQueryPlanner,
    select_next_gap,
)
from src.rair.state import (
    Gap,
    RAIRState,
)


def make_state() -> RAIRState:
    state = RAIRState(
        question_id="toy",
        question="Example multi-hop question?",
        max_rounds=5,
    )

    state.add_gap(
        Gap(
            gap_id="G1",
            description="First information need.",
            priority="high",
        )
    )

    state.add_gap(
        Gap(
            gap_id="G2",
            description="Second information need.",
            priority="medium",
        )
    )

    state.add_gap(
        Gap(
            gap_id="G3",
            description="Dependent information need.",
            priority="high",
            depends_on=("G1",),
        )
    )

    return state


class QueryPlannerTests(unittest.TestCase):

    def test_selects_highest_priority_actionable_gap(self):
        state = make_state()

        selected = select_next_gap(
            state
        )

        self.assertEqual(
            selected.gap_id,
            "G1",
        )

    def test_dependency_blocks_gap(self):
        state = make_state()

        actionable = {
            gap.gap_id
            for gap in state.actionable_gaps()
        }

        self.assertNotIn(
            "G3",
            actionable,
        )

    def test_dependency_becomes_actionable(self):
        state = make_state()

        state.resolve_gap(
            "G1"
        )

        selected = select_next_gap(
            state
        )

        self.assertEqual(
            selected.gap_id,
            "G3",
        )

    def test_valid_query(self):
        query = RAIRQueryPlanner.parse_payload(
            {
                "query":
                    "Mira Solen birthplace"
            }
        )

        self.assertEqual(
            query,
            "Mira Solen birthplace",
        )

    def test_empty_query_rejected(self):
        with self.assertRaises(
            QueryPlanningError
        ):
            RAIRQueryPlanner.parse_payload(
                {
                    "query": "   "
                }
            )

    def test_extra_field_rejected(self):
        with self.assertRaises(
            QueryPlanningError
        ):
            RAIRQueryPlanner.parse_payload(
                {
                    "query": "Mira Solen",
                    "answer": "Nerava",
                }
            )

    def test_multiline_query_rejected(self):
        with self.assertRaises(
            QueryPlanningError
        ):
            RAIRQueryPlanner.parse_payload(
                {
                    "query":
                        "Mira Solen\n"
                        "birthplace"
                }
            )

    def test_repeated_query_rejected_case_insensitively(self):
        with self.assertRaises(
            QueryPlanningError
        ):
            RAIRQueryPlanner.parse_payload(
                {
                    "query":
                        "  MIRA Solen birthplace  "
                },
                previous_queries=[
                    "Mira Solen birthplace"
                ],
            )

    def test_long_query_rejected(self):
        query = " ".join(
            ["term"] * 25
        )

        with self.assertRaises(
            QueryPlanningError
        ):
            RAIRQueryPlanner.parse_payload(
                {
                    "query": query
                }
            )

    def test_no_actionable_gap_rejected(self):
        state = RAIRState(
            question_id="toy",
            question="Example?",
            max_rounds=5,
        )

        with self.assertRaises(
            QueryPlanningError
        ):
            select_next_gap(
                state
            )


if __name__ == "__main__":
    unittest.main()