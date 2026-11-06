"""Tests for RAIR decomposition validation."""

import unittest

from src.rair.decomposer import (
    DecompositionError,
    RAIRDecomposer,
)


def valid_payload() -> dict:
    return {
        "gaps": [
            {
                "gap_id": "G1",
                "description": (
                    "Identify the author of "
                    "The Glass Orchard."
                ),
                "priority": "high",
                "depends_on": [],
            },
            {
                "gap_id": "G2",
                "description": (
                    "Identify the birthplace city "
                    "of the entity identified by G1."
                ),
                "priority": "high",
                "depends_on": [
                    "G1",
                ],
            },
        ]
    }


class DecomposerTests(unittest.TestCase):

    def test_valid_decomposition(self):
        gaps = RAIRDecomposer.parse_payload(
            valid_payload()
        )

        self.assertEqual(
            len(gaps),
            2,
        )

        self.assertEqual(
            gaps[0].gap_id,
            "G1",
        )

        self.assertEqual(
            gaps[1].depends_on,
            ("G1",),
        )

    def test_requires_gaps_field(self):
        with self.assertRaises(
            DecompositionError
        ):
            RAIRDecomposer.parse_payload(
                {}
            )

    def test_extra_top_level_field_rejected(self):
        payload = valid_payload()
        payload["answer"] = "Nerava"

        with self.assertRaises(
            DecompositionError
        ):
            RAIRDecomposer.parse_payload(
                payload
            )

    def test_gap_ids_must_be_sequential(self):
        payload = valid_payload()
        payload["gaps"][1][
            "gap_id"
        ] = "G7"

        with self.assertRaises(
            DecompositionError
        ):
            RAIRDecomposer.parse_payload(
                payload
            )

    def test_future_dependency_rejected(self):
        payload = valid_payload()

        payload["gaps"][0][
            "depends_on"
        ] = ["G2"]

        with self.assertRaises(
            DecompositionError
        ):
            RAIRDecomposer.parse_payload(
                payload
            )

    def test_unknown_dependency_rejected(self):
        payload = valid_payload()

        payload["gaps"][1][
            "depends_on"
        ] = ["G99"]

        with self.assertRaises(
            DecompositionError
        ):
            RAIRDecomposer.parse_payload(
                payload
            )

    def test_duplicate_dependency_rejected(self):
        payload = valid_payload()

        payload["gaps"][1][
            "depends_on"
        ] = [
            "G1",
            "G1",
        ]

        with self.assertRaises(
            DecompositionError
        ):
            RAIRDecomposer.parse_payload(
                payload
            )

    def test_invalid_priority_rejected(self):
        payload = valid_payload()

        payload["gaps"][0][
            "priority"
        ] = "urgent"

        with self.assertRaises(
            DecompositionError
        ):
            RAIRDecomposer.parse_payload(
                payload
            )

    def test_empty_description_rejected(self):
        payload = valid_payload()

        payload["gaps"][0][
            "description"
        ] = ""

        with self.assertRaises(
            DecompositionError
        ):
            RAIRDecomposer.parse_payload(
                payload
            )

    def test_more_than_six_gaps_rejected(self):
        payload = {
            "gaps": []
        }

        for index in range(
            1,
            8,
        ):
            payload["gaps"].append(
                {
                    "gap_id": f"G{index}",
                    "description": (
                        f"Information need {index}"
                    ),
                    "priority": "medium",
                    "depends_on": [],
                }
            )

        with self.assertRaises(
            DecompositionError
        ):
            RAIRDecomposer.parse_payload(
                payload
            )


if __name__ == "__main__":
    unittest.main()