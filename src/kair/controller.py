"""Serial local adaptation of journal KAIR Algorithm 3's competitive mode."""

import math
import time
from dataclasses import asdict, dataclass
from typing import Any

from src.datasets.hotpotqa import QuestionInput
from src.evaluation.budget import BudgetExhausted
from src.kair.agent import KAIRAgent
from src.kair.state import KAIRState
from src.llm.ollama_client import OllamaClient, OllamaError, summarize_calls
from src.rair.query_planner import RepeatedQueryError
from src.rair.state import Evidence
from src.rair.synthesizer import RAIRSynthesizer, SynthesisResult, resolve_sources
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.document_store import DocumentStore
from src.progress import publish


@dataclass
class KAIRResult:
    question_id: str
    question: str
    status: str
    stop_reason: str
    selected_agent_id: str | None
    prediction: SynthesisResult
    sources: list[dict[str, Any]]
    shared_context: tuple[Evidence, ...]
    agents: list[KAIRState]
    iterations: list[dict[str, Any]]
    llm_calls: list[dict[str, Any]]
    usage: dict[str, Any]
    agent_errors: list[dict[str, Any]]
    error: dict[str, str] | None
    budget: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def select_candidate(states: list[KAIRState]) -> KAIRState | None:
    """Gold-free argmin |R|; supplied execution order breaks ties."""
    eligible = [state for state in states if state.initialized and state.status != "error"]
    return min(eligible, key=lambda state: len(state.required), default=None)


class KAIRController:
    def __init__(self, settings: dict[str, Any], client: OllamaClient, *, on_progress=None) -> None:
        self.on_progress = on_progress
        config = settings["kair"]
        if config["variant"] != "competitive_local":
            raise ValueError("Only the competitive_local KAIR variant is implemented.")
        self.num_agents = config["num_agents"]
        self.max_iterations = config["max_iterations"]
        self.steps_per_iteration = config["steps_per_iteration"]
        for value in (self.num_agents, self.max_iterations, self.steps_per_iteration):
            if type(value) is not int or value < 1:
                raise ValueError("KAIR agent count and iteration/step budgets must be positive integers.")
        temperature = config["temperature"]
        if (type(temperature) not in (int, float) or not math.isfinite(temperature)
                or temperature < 0.7):
            raise ValueError("KAIR competition requires a finite temperature >= 0.7.")
        self.temperature = float(temperature)
        top_k = settings["retrieval"]["top_k"]
        if type(top_k) is not int or top_k < 1:
            raise ValueError("retrieval.top_k must be a positive integer.")
        self.client = client
        self.seed = int(settings["project"]["seed"])
        self.agent = KAIRAgent(client, self.temperature, top_k, on_progress=on_progress)
        self.synthesizer = RAIRSynthesizer(client)

    @property
    def policy(self) -> dict[str, Any]:
        maximum = self.num_agents * self.max_iterations * self.steps_per_iteration
        return {
            "retries": 0, "max_retrieval_calls": maximum, "max_llm_calls": 4 * maximum + 1,
            "scheduler": "serial; rotate starting agent each competition iteration",
            "selection": "fewest unresolved requirements; execution order breaks ties",
            "max_iterations": self.max_iterations, "steps_per_iteration": self.steps_per_iteration,
            "agent_seeds": [self.seed + i for i in range(self.num_agents)],
            "agent_temperature": self.temperature,
            "final_answer": "verified facts only; abstain if insufficient",
        }

    def run(self, task: QuestionInput) -> KAIRResult:
        store = DocumentStore(task.question_id, task.documents)
        retriever = BM25Retriever(store, budget=self.client.budget)
        states = [KAIRState(f"A{i + 1}", self.seed + i) for i in range(self.num_agents)]
        self.client.calls = []
        shared: tuple[Evidence, ...] = ()
        iterations = []
        agent_errors = []
        selected = None
        prediction = SynthesisResult("", (), True)
        error = None
        stop_reason = "max_iterations"
        started = time.perf_counter()

        for iteration in range(1, self.max_iterations + 1):
            # Same frozen shared context for every candidate in this competition.
            incoming = shared
            offset = (iteration - 1) % self.num_agents
            order = states[offset:] + states[:offset]
            record = {"iteration": iteration, "agent_order": [s.agent_id for s in order],
                      "incoming_context": [asdict(item) for item in incoming], "steps": []}
            iterations.append(record)
            completed = None
            budget_stop = False
            for state in order:
                if state.status == "stalled":
                    # A new competition's shared source context may unlock another query.
                    state.status = "active"
                if state.status != "active":
                    continue
                for _ in range(self.steps_per_iteration):
                    trace = {"agent_id": state.agent_id}
                    record["steps"].append(trace)
                    try:
                        self.agent.step(task, state, incoming, retriever, iteration, trace)
                    except BudgetExhausted as exc:
                        trace.update(stop_reason="budget_exhausted", resource=exc.resource)
                        budget_stop = True
                        break
                    except RepeatedQueryError as exc:
                        state.status = "stalled"
                        trace.update(stop_reason="repeated_query", message=str(exc))
                        break
                    except (OllamaError, ValueError, TypeError, KeyError, AttributeError) as exc:
                        state.status = "error"
                        detail = {"agent_id": state.agent_id, "iteration": iteration,
                                  "stage": self.agent.stage, "type": type(exc).__name__,
                                  "message": str(exc)}
                        trace["error"] = detail
                        agent_errors.append(detail)
                        break
                    if state.complete:
                        state.status = "complete"
                        completed = state
                        break
                if completed is not None or budget_stop:
                    # Serial equivalent of immediate cancellation: later agents do not run.
                    break
            selected = completed or select_candidate(order)
            if budget_stop:
                stop_reason = "budget_exhausted"
                if selected is not None:
                    shared = selected.context
                record.update(selected_agent_id=selected.agent_id if selected else None,
                              shared_context=[asdict(item) for item in shared])
                if self.on_progress:
                    publish(self.on_progress, 'selection', iteration=iteration,
                            selected_agent_id=record['selected_agent_id'], context=record['shared_context'],
                            reason='Budget exhausted; retain the eligible proposal with fewest unresolved requirements.')
                break
            if selected is None:
                stop_reason = "all_agents_failed"
                error = {"stage": "competition", "type": "NoValidProposal",
                         "message": "No initialized, non-failing agent proposal is available."}
                break
            shared = selected.context
            record.update(selected_agent_id=selected.agent_id,
                          proposal_requirements={s.agent_id: len(s.required) for s in states
                                                 if s.initialized and s.status != "error"},
                          shared_context=[asdict(item) for item in shared])
            if self.on_progress:
                publish(self.on_progress, 'selection', iteration=iteration, selected_agent_id=selected.agent_id,
                        proposal_requirements=record['proposal_requirements'], context=record['shared_context'],
                        reason='Valid complete proposal.' if completed is not None else
                        'Fewest unresolved requirements; execution order breaks ties.')
            if completed is not None:
                stop_reason = "agent_complete"
                break
            if all(state.status != "active" for state in states) and shared == incoming:
                stop_reason = ("all_agents_stalled" if all(s.status == "stalled" for s in states)
                               else "no_active_agents")
                break

        if error is None:
            self.agent.stage = 'synthesize'
            first_call = len(self.client.calls)
            try:
                prediction = self.synthesizer.synthesize_knowledge(
                    task.question, {fact.fact_id: fact.statement for fact in selected.known} if selected else {},
                    {f"R{i}": text for i, text in enumerate(selected.required, start=1)}
                    if selected else {"R1": task.question},
                )
            except (BudgetExhausted, OllamaError, ValueError, TypeError, KeyError) as exc:
                error = {"stage": "synthesize", "type": type(exc).__name__, "message": str(exc)}
                stop_reason = "error"
            finally:
                for call in self.client.calls[first_call:]:
                    call.update(agent_id=selected.agent_id if selected else None, stage="synthesize")
        sources = resolve_sources(selected.known, prediction.citations, store) if selected else []
        usage = {**summarize_calls(self.client.calls),
                 "retrieval_calls": sum(len(state.query_history) for state in states),
                 "elapsed_seconds": time.perf_counter() - started}
        return KAIRResult(
            task.question_id, task.question,
            "error" if error else "abstained" if prediction.abstain else "answered",
            stop_reason, selected.agent_id if selected else None, prediction, sources, shared,
            states, iterations, self.client.calls, usage, agent_errors, error,
            self.client.budget.to_dict() if self.client.budget else None,
        )
