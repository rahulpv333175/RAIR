"""Final answer synthesis from verified RAIR knowledge only."""

from dataclasses import dataclass
from copy import deepcopy
from typing import Any

from src.llm.ollama_client import OllamaClient
from src.llm.prompts import (
    RAIR_SYNTHESIZER_SCHEMA,
    RAIR_SYNTHESIZER_SYSTEM_PROMPT,
)
from src.rair.state import RAIRState
from src.retrieval.document_store import DocumentStore


def resolve_sources(facts: list[Any], citations: tuple[str, ...],
                    store: DocumentStore) -> list[dict[str, Any]]:
    """Map cited facts back to deduplicated original source sentences."""
    sources = []
    seen = set()
    for fact in facts:
        if fact.fact_id not in citations:
            continue
        for evidence in fact.evidence:
            for index in evidence.sentence_indices:
                key = (evidence.document_id, index)
                if key not in seen:
                    sources.append({
                        "document_id": evidence.document_id, "title": evidence.title,
                        "sentence_index": index,
                        "text": store.get(evidence.document_id).sentence(index),
                    })
                    seen.add(key)
    return sources


class SynthesisError(ValueError):
    """Raised when synthesizer output is invalid."""


@dataclass(frozen=True)
class SynthesisResult:
    answer: str
    citations: tuple[str, ...]
    abstain: bool


class RAIRSynthesizer:
    def __init__(
        self,
        client: OllamaClient,
    ) -> None:
        self.client = client

    def synthesize(
        self,
        state: RAIRState,
    ) -> SynthesisResult:
        """Generate final answer using verified facts only."""

        return self.synthesize_knowledge(
            state.question,
            {fact.fact_id: fact.statement for fact in state.verified_facts},
            {gap.gap_id: gap.description for gap in state.unresolved_gaps()},
        )

    def synthesize_knowledge(
        self,
        question: str,
        facts: dict[str, str],
        requirements: dict[str, str],
    ) -> SynthesisResult:
        """Common final-answer policy for RAIR and the local KAIR baseline."""
        verified_facts = (
            "\n".join(
                f"- {fact_id}: {statement}"
                for fact_id, statement in facts.items()
            )
            or "<none>"
        )

        unresolved_gaps = (
            "\n".join(
                f"- {gap_id}: {description}"
                for gap_id, description in requirements.items()
            )
            or "<none>"
        )

        user_prompt = (
            f"Original question:\n"
            f"{question}\n\n"
            f"Verified facts:\n"
            f"{verified_facts}\n\n"
            f"Unresolved gaps:\n"
            f"{unresolved_gaps}\n\n"
            "Answer if the verified facts identify the requested entity or provide the answer. "
            "Unresolved gaps are planning hints, not a veto: if a fact answers the question, output the answer. Never fill a missing link."
        )

        abstention = deepcopy(RAIR_SYNTHESIZER_SCHEMA)
        abstention["properties"]["answer"] = {"const": ""}
        abstention["properties"]["citations"].update(maxItems=0)
        abstention["properties"]["abstain"] = {"const": True}
        schema = abstention
        if facts:
            answered = deepcopy(RAIR_SYNTHESIZER_SCHEMA)
            answered["properties"]["answer"]["minLength"] = 1
            answered["properties"]["citations"].update(
                minItems=1, maxItems=len(facts), uniqueItems=True,
                items={"type": "string", "enum": list(facts)})
            answered["properties"]["abstain"] = {"const": False}
            schema = {"oneOf": [abstention, answered]}
        response = self.client.chat(
            RAIR_SYNTHESIZER_SYSTEM_PROMPT,
            user_prompt,
            schema=schema,
            temperature=0.0,
            final_answer=True,
        )

        payload = response.json_object()

        valid_fact_ids = set(facts)

        return self.parse_payload(
            payload,
            valid_fact_ids=valid_fact_ids,
        )

    @staticmethod
    def parse_payload(
        payload: dict[str, Any],
        *,
        valid_fact_ids: set[str],
    ) -> SynthesisResult:
        if set(payload) != {
            "answer",
            "citations",
            "abstain",
        }:
            raise SynthesisError(
                "Synthesizer output must contain exactly "
                "answer, citations, and abstain."
            )

        answer = payload["answer"]
        citations = payload["citations"]
        abstain = payload["abstain"]

        if not isinstance(
            answer,
            str,
        ):
            raise SynthesisError(
                "answer must be a string."
            )

        if not isinstance(
            citations,
            list,
        ):
            raise SynthesisError(
                "citations must be a list."
            )

        if any(
            not isinstance(
                citation,
                str,
            )
            for citation in citations
        ):
            raise SynthesisError(
                "citations must contain strings."
            )

        if type(
            abstain
        ) is not bool:
            raise SynthesisError(
                "abstain must be boolean."
            )

        if len(
            citations
        ) != len(
            set(citations)
        ):
            raise SynthesisError(
                "Duplicate citations are not allowed."
            )

        unknown = [
            citation
            for citation in citations
            if citation not in valid_fact_ids
        ]

        if unknown:
            raise SynthesisError(
                "Synthesizer cited unknown "
                "verified fact IDs: "
                + ", ".join(
                    unknown
                )
            )

        answer = answer.strip()

        if abstain:
            if answer:
                raise SynthesisError(
                    "Abstaining result must have "
                    "an empty answer."
                )

            if citations:
                raise SynthesisError(
                    "Abstaining result must have "
                    "no citations."
                )

        else:
            if not answer:
                raise SynthesisError(
                    "Non-abstaining result requires "
                    "a nonempty answer."
                )

            if not citations:
                raise SynthesisError(
                    "Non-abstaining result requires "
                    "at least one citation."
                )

        return SynthesisResult(
            answer=answer,
            citations=tuple(
                citations
            ),
            abstain=abstain,
        )
