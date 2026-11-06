"""Evidence filtering for RAIR using exact source sentence selection."""

from typing import Any

from src.llm.ollama_client import OllamaClient
from src.llm.prompts import (
    RAIR_EVIDENCE_FILTER_SYSTEM_PROMPT,
)
from src.rair.retrieval_step import (
    RetrievalStepResult,
)
from src.rair.state import (
    Evidence,
    Gap,
    RAIRState,
)
from src.retrieval.document_store import (
    Document,
)


class EvidenceFilterError(ValueError):
    """Raised when evidence-filter output is invalid."""


class RAIREvidenceFilter:
    def __init__(
        self,
        client: OllamaClient,
    ) -> None:
        self.client = client

    def filter(
        self,
        state: RAIRState,
        gap: Gap,
        retrieval: RetrievalStepResult,
    ) -> tuple[Evidence, ...]:
        """Select exact source evidence for one retrieval result."""

        if retrieval.gap.gap_id != gap.gap_id:
            raise EvidenceFilterError(
                "Retrieval result belongs to a different gap."
            )

        if gap.resolved:
            raise EvidenceFilterError(
                f"{gap.gap_id} is already resolved."
            )

        # If BM25 found nothing, there is nothing to filter.
        if not retrieval.results:
            return ()

        documents = {
            result.document.document_id:
                result.document
            for result in retrieval.results
        }

        verified_facts = (
            "\n".join(
                f"- {fact.fact_id}: {fact.statement}"
                for fact in state.verified_facts
            )
            or "<none>"
        )

        choices = {f"E{n}": (document, index) for n, (document, index) in enumerate(
            ((result.document, i) for result in retrieval.results
             for i, text in enumerate(result.document.sentences) if text.strip()), start=1)}
        if not choices:
            return ()
        retrieved_text = "\n".join(
            f"{alias} | {document.title} [S{index}]: {document.sentence(index)}"
            for alias, (document, index) in choices.items())

        user_prompt = (
            f"Original question:\n"
            f"{state.question}\n\n"
            f"Current gap:\n"
            f"{gap.gap_id}: "
            f"{gap.description}\n\n"
            f"Verified facts:\n"
            f"{verified_facts}\n\n"
            f"Retrieved documents:\n"
            f"{retrieved_text}\n\n"
            "Select sentence aliases (E1, E2, ...) that support the current gap "
            "or another fact necessary to answer the original question. "
            "Return aliases only; source locations are attached by software."
        )

        response = self.client.chat(
            RAIR_EVIDENCE_FILTER_SYSTEM_PROMPT,
            user_prompt,
            schema={"type": "object", "properties": {"selections": {
                "type": "array", "maxItems": len(choices), "uniqueItems": True,
                "items": {"type": "string", "enum": list(choices)}}},
                "required": ["selections"], "additionalProperties": False},
            temperature=0.0,
        )

        payload = response.json_object()

        if (set(payload) != {"selections"} or not isinstance(payload["selections"], list)
                or any(not isinstance(alias, str) or alias not in choices for alias in payload["selections"])):
            raise EvidenceFilterError("Filter must select only supplied sentence aliases.")
        # Set selection canonicalizes repeats/order without changing any source text.
        selected = {alias for alias in payload["selections"]}
        indices = {}
        for alias, (document, index) in choices.items():
            if alias in selected:
                indices.setdefault(document.document_id, []).append(index)
        return self.parse_payload({"selections": [
            {"document_id": doc_id, "sentence_indices": values} for doc_id, values in indices.items()
        ]}, documents=documents)

    @staticmethod
    def _format_document(
        document: Document,
    ) -> str:
        lines = [
            f"Document ID: {document.document_id}",
            f"Title: {document.title}",
        ]

        for index, sentence in enumerate(
            document.sentences
        ):
            lines.append(
                f"[S{index}] {sentence}"
            )

        return "\n".join(
            lines
        )

    @staticmethod
    def parse_payload(
        payload: dict[str, Any],
        *,
        documents: dict[str, Document],
    ) -> tuple[Evidence, ...]:
        """Validate selections and reconstruct exact source evidence."""

        if set(payload) != {
            "selections"
        }:
            raise EvidenceFilterError(
                "Filter output must contain exactly "
                "the 'selections' field."
            )

        selections = payload[
            "selections"
        ]

        if not isinstance(
            selections,
            list,
        ):
            raise EvidenceFilterError(
                "'selections' must be a list."
            )

        if len(selections) > 6:
            raise EvidenceFilterError(
                "At most 6 evidence selections "
                "are allowed."
            )

        evidence_items: list[
            Evidence
        ] = []

        selected_documents: set[
            str
        ] = set()

        for position, selection in enumerate(
            selections,
            start=1,
        ):
            if not isinstance(
                selection,
                dict,
            ):
                raise EvidenceFilterError(
                    f"Selection {position} "
                    "must be an object."
                )

            if set(selection) != {
                "document_id",
                "sentence_indices",
            }:
                raise EvidenceFilterError(
                    f"Selection {position} "
                    "has invalid fields."
                )

            document_id = selection[
                "document_id"
            ]

            sentence_indices = selection[
                "sentence_indices"
            ]

            if not isinstance(
                document_id,
                str,
            ):
                raise EvidenceFilterError(
                    "document_id must be a string."
                )

            if document_id not in documents:
                raise EvidenceFilterError(
                    "Evidence Filter selected a "
                    "document that was not retrieved: "
                    f"{document_id}"
                )

            if document_id in selected_documents:
                raise EvidenceFilterError(
                    "A document may appear only once "
                    "in selections."
                )

            if not isinstance(
                sentence_indices,
                list,
            ):
                raise EvidenceFilterError(
                    "sentence_indices must be a list."
                )

            if not sentence_indices:
                raise EvidenceFilterError(
                    "Each selection must contain "
                    "at least one sentence index."
                )

            if any(
                type(index) is not int
                for index in sentence_indices
            ):
                raise EvidenceFilterError(
                    "Sentence indices must be integers."
                )

            if len(
                sentence_indices
            ) != len(
                set(sentence_indices)
            ):
                raise EvidenceFilterError(
                    "Duplicate sentence indices "
                    "are not allowed."
                )

            if sentence_indices != sorted(
                sentence_indices
            ):
                raise EvidenceFilterError(
                    "Sentence indices must be "
                    "in ascending source order."
                )

            document = documents[
                document_id
            ]

            for index in sentence_indices:
                if (
                    index < 0
                    or index
                    >= len(
                        document.sentences
                    )
                ):
                    raise EvidenceFilterError(
                        "Sentence index outside "
                        f"source document: "
                        f"{document_id} S{index}"
                    )

                if not document.sentence(
                    index
                ).strip():
                    raise EvidenceFilterError(
                        "Whitespace-only source "
                        "sentences cannot be "
                        "selected as evidence."
                    )

            exact_text = "\n".join(
                document.sentence(
                    index
                )
                for index in sentence_indices
            )

            evidence_items.append(
                Evidence(
                    document_id=document.document_id,
                    title=document.title,
                    sentence_indices=tuple(
                        sentence_indices
                    ),
                    text=exact_text,
                )
            )

            selected_documents.add(
                document_id
            )

        return tuple(
            evidence_items
        )
