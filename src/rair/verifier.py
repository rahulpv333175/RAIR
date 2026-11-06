"""Verification gate between candidate facts and RAIR shared knowledge."""

from dataclasses import dataclass
from copy import deepcopy
from typing import Any

from src.llm.ollama_client import OllamaClient
from src.llm.prompts import (
    RAIR_VERIFIER_SCHEMA,
    RAIR_VERIFIER_SYSTEM_PROMPT,
)
from src.rair.fact_extractor import CandidateFact
from src.rair.state import (
    Gap,
    RAIRState,
    VerifiedFact,
)


class VerificationError(ValueError):
    """Raised when verifier output or promotion is invalid."""


@dataclass(frozen=True)
class VerificationDecision:
    """Independent verification result for one CandidateFact."""

    candidate_id: str
    supported_by_evidence: bool
    relevant_to_gap: bool
    answer_type_ok: bool
    contains_unresolved_placeholder: bool
    resolves_gap: bool
    reason: str

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError(
                "candidate_id cannot be empty."
            )

        if not self.reason.strip():
            raise ValueError(
                "Verification reason cannot be empty."
            )

        if self.resolves_gap and not self.accepted:
            raise ValueError(
                "A rejected candidate cannot resolve the gap."
            )

    @property
    def accepted(self) -> bool:
        """Whether this candidate may enter verified shared knowledge."""
        return (
            self.supported_by_evidence
            and self.relevant_to_gap
            and self.answer_type_ok
            and not self.contains_unresolved_placeholder
        )


class RAIRVerifier:
    def __init__(
        self,
        client: OllamaClient,
    ) -> None:
        self.client = client

    def verify(
        self,
        state: RAIRState,
        gap: Gap,
        candidates: tuple[CandidateFact, ...],
    ) -> tuple[VerificationDecision, ...]:
        """Verify candidates without mutating shared knowledge."""

        if gap.resolved:
            raise VerificationError(
                f"{gap.gap_id} is already resolved."
            )

        actionable_ids = {
            item.gap_id
            for item in state.actionable_gaps()
        }

        if gap.gap_id not in actionable_ids:
            raise VerificationError(
                f"{gap.gap_id} is not actionable."
            )

        if not candidates:
            return ()

        for candidate in candidates:
            if candidate.gap_id != gap.gap_id:
                raise VerificationError(
                    f"{candidate.candidate_id} belongs "
                    "to a different gap."
                )

        verified_facts = (
            "\n".join(
                f"- {fact.fact_id}: {fact.statement}"
                for fact in state.verified_facts
            )
            or "<none>"
        )

        candidate_text = "\n\n".join(
            self._format_candidate(
                candidate
            )
            for candidate in candidates
        )

        user_prompt = (
            f"Original question:\n"
            f"{state.question}\n\n"
            f"Current gap:\n"
            f"{gap.gap_id}: "
            f"{gap.description}\n\n"
            f"Previously verified facts:\n"
            f"{verified_facts}\n\n"
            f"Candidate facts and their exact "
            f"source evidence:\n"
            f"{candidate_text}\n\n"
            "Verify every candidate independently. Return a decisions object with exactly "
            + ", ".join(candidate.candidate_id for candidate in candidates)
            + " as keys. Do not invent candidates or omit any decision."
        )

        item_schema = deepcopy(RAIR_VERIFIER_SCHEMA["properties"]["decisions"]["items"])
        del item_schema["properties"]["candidate_id"]
        item_schema["required"].remove("candidate_id")
        item_schema["properties"]["reason"]["minLength"] = 1
        ids = [candidate.candidate_id for candidate in candidates]
        schema = {"type": "object", "$defs": {"decision": item_schema}, "properties": {
            "decisions": {"type": "object", "properties": {
                key: {"$ref": "#/$defs/decision"} for key in ids},
                "required": ids, "additionalProperties": False}},
            "required": ["decisions"], "additionalProperties": False}
        response = self.client.chat(
            RAIR_VERIFIER_SYSTEM_PROMPT,
            user_prompt,
            schema=schema,
            temperature=0.0,
        )

        payload = response.json_object()

        return self.parse_response(
            payload,
            candidates=candidates,
        )

    @staticmethod
    def parse_response(payload: dict, *, candidates: tuple[CandidateFact, ...]) -> tuple[VerificationDecision, ...]:
        ids = [candidate.candidate_id for candidate in candidates]
        if (set(payload) != {"decisions"} or not isinstance(payload["decisions"], dict)
                or set(payload["decisions"]) != set(ids)):
            raise VerificationError("Verifier must return exactly the supplied candidate keys.")
        decisions = []
        guards = ("supported_by_evidence", "relevant_to_gap", "answer_type_ok", "contains_unresolved_placeholder")
        for key in ids:
            raw = payload["decisions"][key]
            if not isinstance(raw, dict) or set(raw) != {*guards, "resolves_gap", "reason"}:
                raise VerificationError("Invalid keyed verifier decision fields.")
            raw = {"candidate_id": key, **raw}
            if all(type(raw[field]) is bool for field in (*guards, "resolves_gap")):
                accepted = all(raw[field] for field in guards[:3]) and not raw[guards[3]]
                if raw["resolves_gap"] and not accepted:
                    # A rejected claim never resolves a gap or discards other valid decisions.
                    raw["resolves_gap"] = False
            decisions.append(raw)
        return RAIRVerifier.parse_payload({"decisions": decisions}, candidates=candidates)

    @staticmethod
    def _format_candidate(
        candidate: CandidateFact,
    ) -> str:
        lines = [
            f"Candidate ID: {candidate.candidate_id}",
            f"Claim: {candidate.statement}",
            "Attached evidence:",
        ]

        for index, evidence in enumerate(
            candidate.evidence,
            start=1,
        ):
            source_indices = ", ".join(
                f"S{sentence_index}"
                for sentence_index
                in evidence.sentence_indices
            )

            lines.extend(
                [
                    f"  Source {index}",
                    f"  Document ID: {evidence.document_id}",
                    f"  Title: {evidence.title}",
                    f"  Sentences: {source_indices}",
                    f"  Exact text: {evidence.text}",
                ]
            )

        return "\n".join(
            lines
        )

    @staticmethod
    def parse_payload(
        payload: dict[str, Any],
        *,
        candidates: tuple[CandidateFact, ...],
    ) -> tuple[VerificationDecision, ...]:
        """Validate verifier output against the supplied candidates."""

        if set(payload) != {
            "decisions"
        }:
            raise VerificationError(
                "Verifier output must contain exactly "
                "the 'decisions' field."
            )

        raw_decisions = payload[
            "decisions"
        ]

        if not isinstance(
            raw_decisions,
            list,
        ):
            raise VerificationError(
                "'decisions' must be a list."
            )

        if len(raw_decisions) != len(
            candidates
        ):
            raise VerificationError(
                "Verifier must return exactly one "
                "decision per candidate."
            )

        expected_fields = {
            "candidate_id",
            "supported_by_evidence",
            "relevant_to_gap",
            "answer_type_ok",
            "contains_unresolved_placeholder",
            "resolves_gap",
            "reason",
        }

        decisions: list[
            VerificationDecision
        ] = []

        for position, (
            raw,
            candidate,
        ) in enumerate(
            zip(
                raw_decisions,
                candidates,
            ),
            start=1,
        ):
            if not isinstance(
                raw,
                dict,
            ):
                raise VerificationError(
                    f"Decision {position} "
                    "must be an object."
                )

            if set(raw) != expected_fields:
                raise VerificationError(
                    f"Decision {position} "
                    "has invalid fields."
                )

            if (
                raw["candidate_id"]
                != candidate.candidate_id
            ):
                raise VerificationError(
                    f"Decision {position} expected "
                    f"{candidate.candidate_id}, got "
                    f"{raw['candidate_id']!r}."
                )

            boolean_fields = (
                "supported_by_evidence",
                "relevant_to_gap",
                "answer_type_ok",
                "contains_unresolved_placeholder",
                "resolves_gap",
            )

            for field_name in boolean_fields:
                if type(
                    raw[field_name]
                ) is not bool:
                    raise VerificationError(
                        f"{field_name} must be boolean."
                    )

            reason = raw[
                "reason"
            ]

            if not isinstance(
                reason,
                str,
            ) or not reason.strip():
                raise VerificationError(
                    "Verification reason must "
                    "be a nonempty string."
                )

            try:
                decision = VerificationDecision(
                    candidate_id=raw[
                        "candidate_id"
                    ],
                    supported_by_evidence=raw[
                        "supported_by_evidence"
                    ],
                    relevant_to_gap=raw[
                        "relevant_to_gap"
                    ],
                    answer_type_ok=raw[
                        "answer_type_ok"
                    ],
                    contains_unresolved_placeholder=raw[
                        "contains_unresolved_placeholder"
                    ],
                    resolves_gap=raw[
                        "resolves_gap"
                    ],
                    reason=reason.strip(),
                )
            except ValueError as exc:
                raise VerificationError(
                    f"Invalid decision for "
                    f"{candidate.candidate_id}: {exc}"
                ) from exc

            decisions.append(
                decision
            )

        return tuple(
            decisions
        )

    @staticmethod
    def _next_fact_id(
        state: RAIRState,
    ) -> str:
        existing = {
            fact.fact_id
            for fact in state.verified_facts
        }

        index = 1

        while f"F{index}" in existing:
            index += 1

        return f"F{index}"

    @staticmethod
    def commit_decisions(
        state: RAIRState,
        gap: Gap,
        candidates: tuple[CandidateFact, ...],
        decisions: tuple[VerificationDecision, ...],
    ) -> tuple[VerifiedFact, ...]:
        """Promote only accepted candidates into shared knowledge."""

        if gap.resolved:
            raise VerificationError(
                f"{gap.gap_id} is already resolved."
            )

        if len(candidates) != len(
            decisions
        ):
            raise VerificationError(
                "Candidate/decision count mismatch."
            )

        promoted: list[
            VerifiedFact
        ] = []

        should_resolve_gap = False

        for candidate, decision in zip(
            candidates,
            decisions,
        ):
            if (
                candidate.candidate_id
                != decision.candidate_id
            ):
                raise VerificationError(
                    "Candidate/decision ID mismatch."
                )

            if (
                candidate.gap_id
                != gap.gap_id
            ):
                raise VerificationError(
                    f"{candidate.candidate_id} belongs "
                    "to a different gap."
                )

            if not decision.accepted:
                continue

            fact = VerifiedFact(
                fact_id=RAIRVerifier._next_fact_id(
                    state
                ),
                statement=candidate.statement,
                gap_id=gap.gap_id,
                evidence=candidate.evidence,
            )

            state.add_verified_fact(
                fact
            )

            promoted.append(
                fact
            )

            if decision.resolves_gap:
                should_resolve_gap = True

        if should_resolve_gap:
            state.resolve_gap(
                gap.gap_id
            )

        return tuple(
            promoted
        )

    def verify_and_commit(
        self,
        state: RAIRState,
        gap: Gap,
        candidates: tuple[CandidateFact, ...],
    ) -> tuple[
        tuple[VerificationDecision, ...],
        tuple[VerifiedFact, ...],
    ]:
        """Verify first, then safely promote accepted candidates."""

        decisions = self.verify(
            state,
            gap,
            candidates,
        )

        promoted = self.commit_decisions(
            state,
            gap,
            candidates,
            decisions,
        )

        return (
            decisions,
            promoted,
        )
