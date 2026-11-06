"""Tests for RAIR exact-source evidence filtering."""

import unittest

from src.rair.evidence_filter import (
    EvidenceFilterError,
    RAIREvidenceFilter,
)
from src.retrieval.document_store import (
    Document,
)


def make_documents() -> dict[str, Document]:
    book = Document(
        document_id="toy:D1",
        question_id="toy",
        title="The Glass Orchard",
        sentences=(
            "The Glass Orchard was written by Mira Solen.",
            "It was published in 1998.",
        ),
    )

    author = Document(
        document_id="toy:D2",
        question_id="toy",
        title="Mira Solen",
        sentences=(
            "Mira Solen was born in Nerava.",
            "",
            "She later became a novelist.",
        ),
    )

    distractor = Document(
        document_id="toy:D3",
        question_id="toy",
        title="Orchards",
        sentences=(
            "An orchard is land planted with fruit trees.",
        ),
    )

    return {
        document.document_id:
            document
        for document in (
            book,
            author,
            distractor,
        )
    }


class EvidenceFilterTests(unittest.TestCase):

    def test_valid_selection_reconstructs_exact_source(self):
        evidence = RAIREvidenceFilter.parse_payload(
            {
                "selections": [
                    {
                        "document_id":
                            "toy:D1",
                        "sentence_indices":
                            [0],
                    }
                ]
            },
            documents=make_documents(),
        )

        self.assertEqual(
            len(evidence),
            1,
        )

        self.assertEqual(
            evidence[0].document_id,
            "toy:D1",
        )

        self.assertEqual(
            evidence[0].sentence_indices,
            (0,),
        )

        self.assertEqual(
            evidence[0].text,
            (
                "The Glass Orchard was "
                "written by Mira Solen."
            ),
        )

    def test_multiple_sentences_preserve_source_text(self):
        evidence = RAIREvidenceFilter.parse_payload(
            {
                "selections": [
                    {
                        "document_id":
                            "toy:D1",
                        "sentence_indices":
                            [0, 1],
                    }
                ]
            },
            documents=make_documents(),
        )

        self.assertEqual(
            evidence[0].text,
            (
                "The Glass Orchard was written "
                "by Mira Solen.\n"
                "It was published in 1998."
            ),
        )

    def test_empty_selection_is_allowed(self):
        evidence = RAIREvidenceFilter.parse_payload(
            {
                "selections": []
            },
            documents=make_documents(),
        )

        self.assertEqual(
            evidence,
            (),
        )

    def test_unknown_document_rejected(self):
        with self.assertRaises(
            EvidenceFilterError
        ):
            RAIREvidenceFilter.parse_payload(
                {
                    "selections": [
                        {
                            "document_id":
                                "toy:D99",
                            "sentence_indices":
                                [0],
                        }
                    ]
                },
                documents=make_documents(),
            )

    def test_invalid_sentence_index_rejected(self):
        with self.assertRaises(
            EvidenceFilterError
        ):
            RAIREvidenceFilter.parse_payload(
                {
                    "selections": [
                        {
                            "document_id":
                                "toy:D1",
                            "sentence_indices":
                                [99],
                        }
                    ]
                },
                documents=make_documents(),
            )

    def test_duplicate_sentence_index_rejected(self):
        with self.assertRaises(
            EvidenceFilterError
        ):
            RAIREvidenceFilter.parse_payload(
                {
                    "selections": [
                        {
                            "document_id":
                                "toy:D1",
                            "sentence_indices":
                                [0, 0],
                        }
                    ]
                },
                documents=make_documents(),
            )

    def test_unsorted_sentence_indices_rejected(self):
        with self.assertRaises(
            EvidenceFilterError
        ):
            RAIREvidenceFilter.parse_payload(
                {
                    "selections": [
                        {
                            "document_id":
                                "toy:D1",
                            "sentence_indices":
                                [1, 0],
                        }
                    ]
                },
                documents=make_documents(),
            )

    def test_empty_source_sentence_rejected(self):
        with self.assertRaises(
            EvidenceFilterError
        ):
            RAIREvidenceFilter.parse_payload(
                {
                    "selections": [
                        {
                            "document_id":
                                "toy:D2",
                            "sentence_indices":
                                [1],
                        }
                    ]
                },
                documents=make_documents(),
            )

    def test_same_document_cannot_be_selected_twice(self):
        with self.assertRaises(
            EvidenceFilterError
        ):
            RAIREvidenceFilter.parse_payload(
                {
                    "selections": [
                        {
                            "document_id":
                                "toy:D1",
                            "sentence_indices":
                                [0],
                        },
                        {
                            "document_id":
                                "toy:D1",
                            "sentence_indices":
                                [1],
                        },
                    ]
                },
                documents=make_documents(),
            )

    def test_extra_fields_rejected(self):
        with self.assertRaises(
            EvidenceFilterError
        ):
            RAIREvidenceFilter.parse_payload(
                {
                    "selections": [
                        {
                            "document_id":
                                "toy:D1",
                            "sentence_indices":
                                [0],
                            "summary":
                                "Mira wrote it.",
                        }
                    ]
                },
                documents=make_documents(),
            )


if __name__ == "__main__":
    unittest.main()