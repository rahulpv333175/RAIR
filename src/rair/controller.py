"""Bounded end-to-end RAIR execution; gold labels never enter this module."""

import time
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Callable

from src.datasets.hotpotqa import QuestionInput
from src.evaluation.budget import BudgetExhausted
from src.llm.ollama_client import OllamaClient, OllamaError, summarize_calls
from src.llm.prompts import RAIR_DECOMPOSER_SCHEMA
from src.rair.decomposer import RAIRDecomposer
from src.rair.evidence_filter import RAIREvidenceFilter
from src.rair.fact_extractor import RAIRFactExtractor
from src.rair.query_planner import RAIRQueryPlanner, RepeatedQueryError, select_next_gap
from src.rair.retrieval_step import RAIRRetrievalStep
from src.rair.state import RAIRState
from src.rair.synthesizer import RAIRSynthesizer, SynthesisResult, resolve_sources
from src.rair.verifier import RAIRVerifier
from src.retrieval.document_store import DocumentStore
from src.progress import publish


@dataclass
class RAIRResult:
    question_id: str
    question: str
    status: str
    stop_reason: str
    prediction: SynthesisResult
    sources: list[dict[str, Any]]
    state: RAIRState
    rounds: list[dict[str, Any]]
    llm_calls: list[dict[str, Any]]
    usage: dict[str, Any]
    error: dict[str, str] | None
    budget: dict[str, Any] | None = None
    planner_stalls: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RAIRController:
    def __init__(self, settings: dict[str, Any], client: OllamaClient, *, on_progress=None) -> None:
        self.on_progress = on_progress
        self.max_rounds = settings["rair"]["max_rounds"]
        if type(self.max_rounds) is not int or self.max_rounds < 1:
            raise ValueError("rair.max_rounds must be a positive integer.")
        self.client = client
        self.decomposer = RAIRDecomposer(client)
        self.retrieval = RAIRRetrievalStep(
            RAIRQueryPlanner(client), top_k=settings["retrieval"]["top_k"]
        )
        self.evidence_filter = RAIREvidenceFilter(client)
        self.extractor = RAIRFactExtractor(client)
        self.verifier = RAIRVerifier(client)
        self.synthesizer = RAIRSynthesizer(client)

    @property
    def policy(self) -> dict[str, Any]:
        # Stalled independent gaps can each spend a planner call without a retrieval.
        extra_plans = RAIR_DECOMPOSER_SCHEMA["properties"]["gaps"]["maxItems"] - 1
        return {"retries": 0, "max_retrieval_calls": self.max_rounds,
                "max_llm_calls": 2 + 4 * self.max_rounds + extra_plans,
                "final_answer": "verified facts only; abstain if insufficient"}

    def _invoke(self, stage: str, function: Callable, *args: Any) -> Any:
        self._stage = stage
        first_call = len(self.client.calls)
        try:
            return function(*args)
        finally:
            for call in self.client.calls[first_call:]:
                call["stage"] = stage

    def run(self, task: QuestionInput) -> RAIRResult:
        """Run sequentially with fresh memory and no automatic LLM retries.

        Native ceilings are max_rounds retrievals and policy['max_llm_calls']
        generations, including stalled planners. An explicit common budget
        can stop earlier. Unrecoverable invalid output or a transport failure
        ends the question with an explicit error and an empty prediction.
        """
        store = DocumentStore(task.question_id, task.documents)
        state = RAIRState(task.question_id, task.question, self.max_rounds)
        # Detach the previous trace so reusing the controller cannot mix runs.
        self.client.calls = []
        rounds: list[dict[str, Any]] = []
        prediction = SynthesisResult("", (), True)
        error = None
        stop_reason = "max_rounds"
        stalled_gaps = set()
        planner_stalls = []
        started = time.perf_counter()

        try:
            self._invoke("decompose", self.decomposer.decompose, state)
            if self.on_progress:
                publish(self.on_progress, 'decompose', gaps=[asdict(g) for g in state.gaps])
            while state.current_round < state.max_rounds and not state.is_complete():
                if self.client.budget is not None:
                    remaining_non_final = (self.client.budget.max_llm_calls - 1) - self.client.budget.llm_calls
                    if remaining_non_final < 4 and state.verified_facts:
                        stop_reason = "budget_exhausted"
                        break
                if not any(g.gap_id not in stalled_gaps for g in state.actionable_gaps()):
                    stop_reason = "repeated_query" if stalled_gaps else "no_actionable_gaps"
                    break
                selected_gap = select_next_gap(state, stalled_gaps)
                try:
                    retrieval = self._invoke("retrieve", self.retrieval.run, state, store, selected_gap)
                except RepeatedQueryError as exc:
                    stalled_gaps.add(selected_gap.gap_id)
                    planner_stalls.append({"gap_id": selected_gap.gap_id, "message": str(exc)})
                    continue
                gap = retrieval.gap
                trace = {
                    "round_number": retrieval.round_number,
                    "gap_id": gap.gap_id,
                    "query": retrieval.query,
                    "query_origin": retrieval.query_origin,
                    "retrieved": [asdict(item) for item in retrieval.results],
                }
                rounds.append(trace)
                if self.on_progress:
                    publish(self.on_progress, 'retrieve', round=trace['round_number'], gap_id=gap.gap_id,
                            query=retrieval.query, documents=[{'title': r.document.title,
                            'document_id': r.document.document_id, 'score': r.score} for r in retrieval.results])
                evidence = self._invoke(
                    "filter", self.evidence_filter.filter, state, gap, retrieval
                )
                trace["evidence"] = [asdict(item) for item in evidence]
                if self.on_progress:
                    publish(self.on_progress, 'filter', round=trace['round_number'], evidence=trace['evidence'])
                candidates = self._invoke("extract", self.extractor.extract, state, gap, evidence)
                trace["candidates"] = [asdict(item) for item in candidates]
                if self.on_progress:
                    publish(self.on_progress, 'extract', round=trace['round_number'], candidates=trace['candidates'])
                decisions, promoted = self._invoke(
                    "verify", self.verifier.verify_and_commit, state, gap, candidates
                )
                trace["decisions"] = [
                    {**asdict(item), "accepted": item.accepted} for item in decisions
                ]
                trace["promoted"] = [asdict(item) for item in promoted]
                trace["gap_resolved"] = gap.resolved
                if self.on_progress:
                    publish(self.on_progress, 'verify', round=trace['round_number'], decisions=trace['decisions'],
                            promoted=trace['promoted'], gaps=[asdict(g) for g in state.gaps])
                if not evidence:
                    feedback = "No relevant source evidence selected."
                elif not candidates:
                    feedback = "No candidate facts extracted from the evidence."
                else:
                    feedback = "; ".join(
                        f"{item.candidate_id}: {item.reason}" for item in decisions
                    )
                state.query_history[-1] = replace(
                    state.query_history[-1], evidence_feedback=feedback
                )
            if state.is_complete():
                stop_reason = "all_gaps_resolved"
        except BudgetExhausted:
            stop_reason = "budget_exhausted"
        except (OllamaError, ValueError, TypeError, KeyError, AttributeError) as exc:
            stop_reason = "error"
            error = {"stage": self._stage, "type": type(exc).__name__, "message": str(exc)}

        if error is None:
            try:
                prediction = self._invoke("synthesize", self.synthesizer.synthesize, state)
            except (BudgetExhausted, OllamaError, ValueError, TypeError, KeyError, AttributeError) as exc:
                stop_reason = "error"
                error = {"stage": "synthesize", "type": type(exc).__name__, "message": str(exc)}

        sources = resolve_sources(state.verified_facts, prediction.citations, store)
        calls = self.client.calls
        usage = {
            **summarize_calls(calls),
            "retrieval_calls": len(state.query_history),
            "elapsed_seconds": time.perf_counter() - started,
        }
        return RAIRResult(
            task.question_id, task.question,
            "error" if error else "abstained" if prediction.abstain else "answered",
            stop_reason, prediction, sources, state, rounds, calls, usage, error,
            self.client.budget.to_dict() if self.client.budget else None,
            planner_stalls,
        )
