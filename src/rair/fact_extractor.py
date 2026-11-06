"""Extract candidate facts from exact source evidence for RAIR."""

from dataclasses import dataclass
from copy import deepcopy
from typing import Any

from src.llm.ollama_client import OllamaClient
from src.llm.prompts import (
    RAIR_FACT_EXTRACTOR_SCHEMA,
    RAIR_FACT_EXTRACTOR_SYSTEM_PROMPT,
)
from src.rair.state import (
    Evidence,
    Gap,
    RAIRState,
)


class FactExtractionError(ValueError):
    """Raised when fact-extractor output is invalid."""


@dataclass(frozen=True)
class CandidateFact:
    """An extracted claim that has NOT yet passed verification."""

    candidate_id: str
    statement: str
    gap_id: str
    evidence: tuple[Evidence, ...]

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError(
                "candidate_id cannot be empty."
            )

        if not self.statement.strip():
            raise ValueError(
                "Candidate statement cannot be empty."
            )

        if not self.gap_id.strip():
            raise ValueError(
                "Candidate fact requires a gap_id."
            )

        if not self.evidence:
            raise ValueError(
                "Candidate fact requires evidence."
            )


class RAIRFactExtractor:
    def __init__(
        self,
        client: OllamaClient,
    ) -> None:
        self.client = client

    def extract(
        self,
        state: RAIRState,
        gap: Gap,
        evidence: tuple[Evidence, ...],
    ) -> tuple[CandidateFact, ...]:
        """Extract candidate claims from filtered evidence."""

        if gap.resolved:
            raise FactExtractionError(
                f"{gap.gap_id} is already resolved."
            )

        actionable_ids = {
            item.gap_id
            for item in state.actionable_gaps()
        }

        if gap.gap_id not in actionable_ids:
            raise FactExtractionError(
                f"{gap.gap_id} is not actionable."
            )

        if not evidence:
            return ()

        evidence_map = {
            f"E{index}": item
            for index, item in enumerate(
                evidence,
                start=1,
            )
        }

        verified_facts = (
            "\n".join(
                f"- {fact.fact_id}: "
                f"{fact.statement}"
                for fact in state.verified_facts
            )
            or "<none>"
        )

        evidence_text = "\n\n".join(
            self._format_evidence(
                evidence_id,
                item,
            )
            for evidence_id, item
            in evidence_map.items()
        )

        user_prompt = (
            f"Original question:\n"
            f"{state.question}\n\n"
            f"Current gap:\n"
            f"{gap.gap_id}: "
            f"{gap.description}\n\n"
            f"Previously verified facts:\n"
            f"{verified_facts}\n\n"
            f"Filtered source evidence:\n"
            f"{evidence_text}\n\n"
            "Extract only candidate factual claims "
            "that are directly supported by the evidence and useful for "
            "the original question, including facts needed by another gap."
        )

        schema = deepcopy(RAIR_FACT_EXTRACTOR_SCHEMA)
        candidate_schema = schema["properties"]["candidates"]["items"]
        del candidate_schema["properties"]["candidate_id"]
        candidate_schema["required"].remove("candidate_id")
        candidate_schema["properties"]["evidence_ids"].update(
            uniqueItems=True, maxItems=len(evidence_map),
            items={"type": "string", "enum": list(evidence_map)})
        response = self.client.chat(
            RAIR_FACT_EXTRACTOR_SYSTEM_PROMPT,
            user_prompt,
            schema=schema,
            temperature=0.0,
        )

        payload = response.json_object()
        if (set(payload) != {"candidates"} or not isinstance(payload["candidates"], list)
                or any(not isinstance(item, dict) or set(item) != {"statement", "evidence_ids"}
                       for item in payload["candidates"])):
            raise FactExtractionError("Extractor must return statements and supplied evidence IDs only.")
        payload = {"candidates": [{"candidate_id": f"C{i}", **item}
                                  for i, item in enumerate(payload["candidates"], start=1)]}

        return self.parse_payload(
            payload,
            gap_id=gap.gap_id,
            evidence_map=evidence_map,
        )

    @staticmethod
    def _format_evidence(
        evidence_id: str,
        evidence: Evidence,
    ) -> str:
        indices = ", ".join(
            f"S{index}"
            for index
            in evidence.sentence_indices
        )

        return (
            f"Evidence ID: {evidence_id}\n"
            f"Document ID: "
            f"{evidence.document_id}\n"
            f"Title: {evidence.title}\n"
            f"Sentences: {indices}\n"
            f"Exact text:\n"
            f"{evidence.text}"
        )

    @staticmethod
    def parse_payload(
        payload: dict[str, Any],
        *,
        gap_id: str,
        evidence_map: dict[str, Evidence],
    ) -> tuple[CandidateFact, ...]:
        """Validate candidate claims and attach exact Evidence objects."""

        if set(payload) != {
            "candidates"
        }:
            raise FactExtractionError(
                "Extractor output must contain "
                "exactly the 'candidates' field."
            )

        raw_candidates = payload[
            "candidates"
        ]

        if not isinstance(
            raw_candidates,
            list,
        ):
            raise FactExtractionError(
                "'candidates' must be a list."
            )

        if len(raw_candidates) > 4:
            raise FactExtractionError(
                "At most 4 candidate facts "
                "are allowed."
            )

        candidates: list[
            CandidateFact
        ] = []

        for position, raw in enumerate(
            raw_candidates,
            start=1,
        ):
            if not isinstance(
                raw,
                dict,
            ):
                raise FactExtractionError(
                    f"Candidate {position} "
                    "must be an object."
                )

            expected_fields = {
                "candidate_id",
                "statement",
                "evidence_ids",
            }

            if set(raw) != expected_fields:
                raise FactExtractionError(
                    f"Candidate {position} "
                    "has invalid fields."
                )

            expected_id = (
                f"C{position}"
            )

            if raw[
                "candidate_id"
            ] != expected_id:
                raise FactExtractionError(
                    f"Expected candidate ID "
                    f"{expected_id}, got "
                    f"{raw['candidate_id']!r}."
                )

            statement = raw[
                "statement"
            ]

            if not isinstance(
                statement,
                str,
            ):
                raise FactExtractionError(
                    "Candidate statement "
                    "must be a string."
                )

            statement = (
                statement.strip()
            )

            if not statement:
                raise FactExtractionError(
                    "Candidate statement "
                    "cannot be empty."
                )

            evidence_ids = raw[
                "evidence_ids"
            ]

            if not isinstance(
                evidence_ids,
                list,
            ):
                raise FactExtractionError(
                    "evidence_ids must "
                    "be a list."
                )

            if not evidence_ids:
                raise FactExtractionError(
                    "Candidate facts require "
                    "at least one evidence ID."
                )

            if any(
                not isinstance(
                    evidence_id,
                    str,
                )
                for evidence_id
                in evidence_ids
            ):
                raise FactExtractionError(
                    "Evidence IDs must "
                    "be strings."
                )

            if len(
                evidence_ids
            ) != len(
                set(evidence_ids)
            ):
                raise FactExtractionError(
                    "Duplicate evidence IDs "
                    "are not allowed."
                )

            unknown_ids = [
                evidence_id
                for evidence_id
                in evidence_ids
                if evidence_id
                not in evidence_map
            ]

            if unknown_ids:
                raise FactExtractionError(
                    "Candidate cited unknown "
                    "evidence IDs: "
                    + ", ".join(
                        unknown_ids
                    )
                )

            candidate_evidence = tuple(
                evidence_map[
                    evidence_id
                ]
                for evidence_id
                in evidence_ids
            )

            try:
                candidate = CandidateFact(
                    candidate_id=expected_id,
                    statement=statement,
                    gap_id=gap_id,
                    evidence=candidate_evidence,
                )
            except ValueError as exc:
                raise FactExtractionError(
                    f"Invalid {expected_id}: "
                    f"{exc}"
                ) from exc

            candidates.append(
                candidate
            )

        return tuple(
            candidates
        )
