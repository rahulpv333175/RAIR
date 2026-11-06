"""RAIR query planning for one actionable information gap."""

from typing import Any

from src.llm.ollama_client import OllamaClient
from src.llm.prompts import (
    RAIR_QUERY_PLANNER_SCHEMA,
    RAIR_QUERY_PLANNER_SYSTEM_PROMPT,
)
from src.rair.state import (
    Gap,
    RAIRState,
)


class QueryPlanningError(ValueError):
    """Raised when a planned retrieval query is invalid."""


class RepeatedQueryError(QueryPlanningError):
    """The planner has stalled on a query that was already executed."""


_PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


def select_next_gap(
    state: RAIRState,
    excluded_gap_ids: set[str] | None = None,
) -> Gap:
    """Try every actionable gap before repeatedly spending on one gap.

    Original decomposition order breaks ties.
    """
    actionable = [gap for gap in state.actionable_gaps() if gap.gap_id not in (excluded_gap_ids or ())]

    if not actionable:
        raise QueryPlanningError(
            "No actionable gaps are available."
        )

    order = {
        gap.gap_id: index
        for index, gap in enumerate(
            state.gaps
        )
    }

    actionable.sort(
        key=lambda gap: (
            sum(attempt.gap_id == gap.gap_id for attempt in state.query_history),
            _PRIORITY_ORDER[gap.priority],
            order[gap.gap_id],
        )
    )

    return actionable[0]


class RAIRQueryPlanner:
    def __init__(
        self,
        client: OllamaClient,
    ) -> None:
        self.client = client

    def plan(
        self,
        state: RAIRState,
        gap: Gap,
    ) -> str:
        """Generate one validated retrieval query."""

        if gap.resolved:
            raise QueryPlanningError(
                f"{gap.gap_id} is already resolved."
            )

        actionable_ids = {
            item.gap_id
            for item in state.actionable_gaps()
        }

        if gap.gap_id not in actionable_ids:
            raise QueryPlanningError(
                f"{gap.gap_id} is not actionable."
            )

        verified_facts = (
            "\n".join(
                f"- {fact.fact_id}: "
                f"{fact.statement}"
                for fact in state.verified_facts
            )
            or "<none>"
        )

        query_history = (
            "\n".join(
                self._format_attempt(
                    attempt
                )
                for attempt in state.query_history
            )
            or "<none>"
        )

        previous_queries = [
            attempt.query
            for attempt in state.query_history
        ]

        forbidden_section = ""
        if previous_queries:
            forbidden_list = "\n".join(f"- {q}" for q in sorted(set(previous_queries)))
            forbidden_section = f"Forbidden queries (DO NOT repeat these or close variations):\n{forbidden_list}\n\n"

        user_prompt = (
            f"Original question:\n"
            f"{state.question}\n\n"
            f"Current gap:\n"
            f"{gap.gap_id}: "
            f"{gap.description}\n\n"
            f"Verified facts:\n"
            f"{verified_facts}\n\n"
            f"Previous query attempts:\n"
            f"{query_history}\n\n"
            f"{forbidden_section}"
            "Generate exactly one new BM25 "
            "search query for the current gap."
        )

        response = self.client.chat(
            RAIR_QUERY_PLANNER_SYSTEM_PROMPT,
            user_prompt,
            schema=RAIR_QUERY_PLANNER_SCHEMA,
            temperature=0.0,
        )

        payload = response.json_object()

        return self.parse_payload(
            payload,
            previous_queries=previous_queries,
        )

    @staticmethod
    def _format_attempt(
        attempt: Any,
    ) -> str:
        status = (
            "success"
            if attempt.success
            else "failed"
        )

        text = (
            f"- round {attempt.round_number}, "
            f"{attempt.gap_id}, "
            f"{status}: {attempt.query}"
        )

        if attempt.failure_reason:
            text += (
                f" | reason: "
                f"{attempt.failure_reason}"
            )

        if attempt.evidence_feedback:
            text += f" | evidence outcome: {attempt.evidence_feedback}"

        return text

    @staticmethod
    def normalize_query(
        query: str,
    ) -> str:
        return " ".join(
            query.lower().split()
        )

    @classmethod
    def parse_payload(
        cls,
        payload: dict[str, Any],
        *,
        previous_queries: list[str]
        | tuple[str, ...] = (),
    ) -> str:
        """Validate query-planner output."""

        if set(payload) != {"query"}:
            raise QueryPlanningError(
                "Planner output must contain "
                "exactly the 'query' field."
            )

        query = payload["query"]

        if not isinstance(
            query,
            str,
        ):
            raise QueryPlanningError(
                "query must be a string."
            )

        query = query.strip()

        if not query:
            raise QueryPlanningError(
                "query cannot be empty."
            )

        if "\n" in query or "\r" in query:
            raise QueryPlanningError(
                "query must be one line."
            )

        if len(query) > 200:
            raise QueryPlanningError(
                "query is too long."
            )

        if len(query.split()) > 24:
            raise QueryPlanningError(
                "query should contain at most "
                "24 whitespace-separated terms."
            )

        normalized = cls.normalize_query(
            query
        )

        prior = {
            cls.normalize_query(
                previous
            )
            for previous in previous_queries
        }

        if normalized in prior:
            raise RepeatedQueryError(
                "Planner repeated a previous query: "
                f"{query}"
            )

        return query
