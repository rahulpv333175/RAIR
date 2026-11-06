"""Connect RAIR query planning to the shared BM25 retriever."""

from dataclasses import dataclass

from src.rair.query_planner import (
    RAIRQueryPlanner,
    RepeatedQueryError,
    select_next_gap,
)
from src.rair.state import (
    Gap,
    QueryAttempt,
    RAIRState,
)
from src.retrieval.bm25 import (
    BM25Retriever,
    RetrievalResult,
)
from src.retrieval.document_store import (
    DocumentStore,
)


class RetrievalStepError(ValueError):
    """Raised when a RAIR retrieval step cannot run safely."""


@dataclass(frozen=True)
class RetrievalStepResult:
    """Output passed later to the Evidence Filter."""

    round_number: int
    gap: Gap
    query: str
    results: tuple[RetrievalResult, ...]
    query_origin: str = "planner"


class RAIRRetrievalStep:
    """Plan one query and execute it against one question's BM25 pool."""

    def __init__(
        self,
        planner: RAIRQueryPlanner,
        *,
        top_k: int,
    ) -> None:
        if type(top_k) is not int or top_k <= 0:
            raise ValueError(
                "top_k must be a positive integer."
            )

        self.planner = planner
        self.top_k = top_k

    def run(
        self,
        state: RAIRState,
        store: DocumentStore,
        gap: Gap | None = None,
    ) -> RetrievalStepResult:
        """Execute one RAIR retrieval round.

        A 'successful' QueryAttempt means BM25 returned at least one
        positive-score document. It does NOT mean the gap is resolved.
        """

        if store.question_id != state.question_id:
            raise RetrievalStepError(
                "DocumentStore question_id does not match RAIRState."
            )

        if state.is_complete():
            raise RetrievalStepError(
                "Cannot retrieve after RAIR state is complete."
            )

        if state.current_round >= state.max_rounds:
            raise RetrievalStepError("RAIR maximum rounds reached.")

        budget = getattr(getattr(self.planner, "client", None), "budget", None)
        if budget is not None:
            budget.check_retrieval()

        # Choose one actionable information gap.
        gap = gap or select_next_gap(state)
        if gap not in state.actionable_gaps():
            raise RetrievalStepError("Selected gap is not actionable.")

        # Generate the query before consuming a retrieval round.
        query_origin = "planner"
        try:
            query = self.planner.plan(state, gap)
        except RepeatedQueryError:
            # One source-free escape uses only question terms and no extra LLM call.
            fallback = " ".join(state.question.split()[:24])[:200].rstrip()
            query = RAIRQueryPlanner.parse_payload(
                {"query": fallback}, previous_queries=[attempt.query for attempt in state.query_history])
            query_origin = "original_question_fallback"

        # A round corresponds to one actual retrieval attempt.
        round_number = state.start_next_round()

        retriever = BM25Retriever(
            store, budget=budget
        )

        results = retriever.search(
            query,
            top_k=self.top_k,
        )

        success = bool(results)

        failure_reason = (
            None
            if success
            else "No positive-score documents."
        )

        attempt = QueryAttempt(
            round_number=round_number,
            gap_id=gap.gap_id,
            query=query,
            retrieved_document_ids=tuple(
                result.document.document_id
                for result in results
            ),
            success=success,
            failure_reason=failure_reason,
        )

        state.record_query(
            attempt
        )

        return RetrievalStepResult(
            round_number=round_number,
            gap=gap,
            query=query,
            results=tuple(results),
            query_origin=query_origin,
        )
