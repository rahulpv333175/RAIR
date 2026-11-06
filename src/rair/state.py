"""Explicit shared state for Role-Aware Iterative Retrieval (RAIR)."""

from dataclasses import asdict, dataclass, field
from typing import Any


VALID_PRIORITIES = {
    "high",
    "medium",
    "low",
}


@dataclass
class Gap:
    """One unresolved piece of information needed for the question."""

    gap_id: str
    description: str
    priority: str = "medium"
    depends_on: tuple[str, ...] = ()
    resolved: bool = False

    def __post_init__(self) -> None:
        if not self.gap_id.strip():
            raise ValueError(
                "gap_id cannot be empty."
            )

        if not self.description.strip():
            raise ValueError(
                "Gap description cannot be empty."
            )

        if self.priority not in VALID_PRIORITIES:
            raise ValueError(
                "Gap priority must be "
                "high, medium, or low."
            )

        if self.gap_id in self.depends_on:
            raise ValueError(
                "A gap cannot depend on itself."
            )


@dataclass(frozen=True)
class Evidence:
    """Exact source material supporting a candidate or verified fact."""

    document_id: str
    title: str
    sentence_indices: tuple[int, ...]
    text: str

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError(
                "document_id cannot be empty."
            )

        if not self.title.strip():
            raise ValueError(
                "Evidence title cannot be empty."
            )

        if not self.text.strip():
            raise ValueError(
                "Evidence text cannot be empty."
            )

        if not self.sentence_indices:
            raise ValueError(
                "Evidence requires at least "
                "one sentence index."
            )

        if any(
            type(index) is not int or index < 0
            for index in self.sentence_indices
        ):
            raise ValueError(
                "Evidence sentence indices "
                "must be non-negative integers."
            )


@dataclass(frozen=True)
class VerifiedFact:
    """A fact admitted to shared knowledge after verification."""

    fact_id: str
    statement: str
    gap_id: str
    evidence: tuple[Evidence, ...]

    def __post_init__(self) -> None:
        if not self.fact_id.strip():
            raise ValueError(
                "fact_id cannot be empty."
            )

        if not self.statement.strip():
            raise ValueError(
                "Fact statement cannot be empty."
            )

        if not self.gap_id.strip():
            raise ValueError(
                "Verified fact requires a gap_id."
            )

        if not self.evidence:
            raise ValueError(
                "Verified facts require evidence."
            )


@dataclass(frozen=True)
class QueryAttempt:
    """One retrieval attempt made by the query planner."""

    round_number: int
    gap_id: str
    query: str
    retrieved_document_ids: tuple[str, ...]
    success: bool
    failure_reason: str | None = None
    evidence_feedback: str | None = None

    def __post_init__(self) -> None:
        if self.round_number < 1:
            raise ValueError(
                "round_number must be at least 1."
            )

        if not self.gap_id.strip():
            raise ValueError(
                "Query attempt requires a gap_id."
            )

        if not self.query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        if self.success and self.failure_reason:
            raise ValueError(
                "Successful attempts cannot "
                "have a failure reason."
            )

        if not self.success and not self.failure_reason:
            raise ValueError(
                "Failed attempts require "
                "a failure reason."
            )


@dataclass
class RAIRState:
    """Mutable state shared by RAIR's specialized roles."""

    question_id: str
    question: str
    max_rounds: int

    gaps: list[Gap] = field(
        default_factory=list
    )

    verified_facts: list[VerifiedFact] = field(
        default_factory=list
    )

    query_history: list[QueryAttempt] = field(
        default_factory=list
    )

    current_round: int = 0

    def __post_init__(self) -> None:
        if not self.question_id.strip():
            raise ValueError(
                "question_id cannot be empty."
            )

        if not self.question.strip():
            raise ValueError(
                "question cannot be empty."
            )

        if self.max_rounds < 1:
            raise ValueError(
                "max_rounds must be at least 1."
            )

    def add_gap(
        self,
        gap: Gap,
    ) -> None:
        if any(
            existing.gap_id == gap.gap_id
            for existing in self.gaps
        ):
            raise ValueError(
                f"Duplicate gap ID: {gap.gap_id}"
            )

        self.gaps.append(gap)

    def get_gap(
        self,
        gap_id: str,
    ) -> Gap:
        for gap in self.gaps:
            if gap.gap_id == gap_id:
                return gap

        raise KeyError(
            f"Unknown gap ID: {gap_id}"
        )

    def unresolved_gaps(
        self,
    ) -> tuple[Gap, ...]:
        return tuple(
            gap
            for gap in self.gaps
            if not gap.resolved
        )

    def actionable_gaps(
        self,
    ) -> tuple[Gap, ...]:
        """Return unresolved gaps whose dependencies are resolved."""
        resolved_ids = {
            gap.gap_id
            for gap in self.gaps
            if gap.resolved
        }

        return tuple(
            gap
            for gap in self.gaps
            if (
                not gap.resolved
                and all(
                    dependency in resolved_ids
                    for dependency in gap.depends_on
                )
            )
        )

    def resolve_gap(
        self,
        gap_id: str,
    ) -> None:
        gap = self.get_gap(gap_id)
        gap.resolved = True

    def add_verified_fact(
        self,
        fact: VerifiedFact,
    ) -> None:
        self.get_gap(fact.gap_id)

        if any(
            existing.fact_id == fact.fact_id
            for existing in self.verified_facts
        ):
            raise ValueError(
                f"Duplicate fact ID: {fact.fact_id}"
            )

        self.verified_facts.append(fact)

    def record_query(
        self,
        attempt: QueryAttempt,
    ) -> None:
        self.get_gap(attempt.gap_id)

        normalized_query = (
            " ".join(
                attempt.query.lower().split()
            )
        )

        for existing in self.query_history:
            existing_normalized = (
                " ".join(
                    existing.query.lower().split()
                )
            )

            if existing_normalized == normalized_query:
                raise ValueError(
                    "Repeated query detected: "
                    f"{attempt.query}"
                )

        self.query_history.append(
            attempt
        )

    def failed_attempts(
        self,
    ) -> tuple[QueryAttempt, ...]:
        return tuple(
            attempt
            for attempt in self.query_history
            if not attempt.success
        )

    def start_next_round(
        self,
    ) -> int:
        if self.current_round >= self.max_rounds:
            raise RuntimeError(
                "RAIR maximum rounds reached."
            )

        self.current_round += 1

        return self.current_round

    def is_complete(
        self,
    ) -> bool:
        return (
            bool(self.gaps)
            and not self.unresolved_gaps()
        )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """JSON-serializable snapshot for experiment logging."""
        return asdict(self)
