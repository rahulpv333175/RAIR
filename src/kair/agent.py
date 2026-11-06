"""One KAIR agent's whole-question query/update/check/filter cycle."""

import json
from copy import deepcopy
from dataclasses import asdict
from typing import Any

from src.datasets.hotpotqa import QuestionInput
from src.kair import prompts
from src.kair.state import KAIRFact, KAIRState
from src.llm.ollama_client import OllamaClient
from src.rair.evidence_filter import RAIREvidenceFilter
from src.rair.query_planner import RAIRQueryPlanner
from src.rair.state import Evidence
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.document_store import DocumentStore
from src.progress import publish


def merge_context(store: DocumentStore, *contexts: tuple[Evidence, ...]) -> tuple[Evidence, ...]:
    indices: dict[str, set[int]] = {}
    for context in contexts:
        for item in context:
            indices.setdefault(item.document_id, set()).update(item.sentence_indices)
    return tuple(Evidence(document_id, store.get(document_id).title, tuple(sorted(selected)),
                          "\n".join(store.get(document_id).sentence(i) for i in sorted(selected)))
                 for document_id, selected in indices.items())


def parse_evidence(selections: Any, available: tuple[Evidence, ...],
                   store: DocumentStore, *, combine_documents: bool = False) -> tuple[Evidence, ...]:
    if combine_documents:
        if not isinstance(selections, list) or len(selections) > 6:
            raise ValueError("At most six candidate source selections are allowed.")
        parts = tuple(item for selection in selections
                      for item in parse_evidence([selection], available, store))
        return merge_context(store, parts)
    allowed = {item.document_id: set(item.sentence_indices) for item in available}
    evidence = RAIREvidenceFilter.parse_payload(
        {"selections": selections}, documents={doc_id: store.get(doc_id) for doc_id in allowed}
    )
    for item in evidence:
        if not set(item.sentence_indices) <= allowed[item.document_id]:
            raise ValueError("Selected sentence was not in the available context.")
    return evidence


def context_payload(context: tuple[Evidence, ...], store: DocumentStore) -> list[dict]:
    """Label each original sentence explicitly, including non-contiguous excerpts."""
    return [{"document_id": item.document_id, "title": item.title,
             "sentences": [{"sentence_index": index, "text": store.get(item.document_id).sentence(index)}
                           for index in item.sentence_indices]} for item in context]


def requirements(value: Any) -> list[str]:
    if (not isinstance(value, list) or len(value) > 6
            or any(not isinstance(item, str) or not item.strip() for item in value)):
        raise ValueError("Required must contain at most six nonempty strings.")
    cleaned = [item.strip() for item in value]
    if len(set(cleaned)) != len(cleaned):
        raise ValueError("Duplicate requirements are not allowed.")
    return cleaned


def selected_ids(value: Any, allowed: set[str]) -> set[str]:
    if (not isinstance(value, list) or any(not isinstance(item, str) for item in value)
            or len(set(value)) != len(value) or not set(value) <= allowed):
        raise ValueError("Fact check returned duplicate or unknown fact/candidate IDs.")
    return set(value)


def id_schema(allowed: list[str]) -> dict:
    schema = {"type": "array", "uniqueItems": True, "maxItems": len(allowed),
              "items": {"type": "string"}}
    if allowed:
        schema["items"]["enum"] = allowed
    return schema


def evidence_schema(available: tuple[Evidence, ...]) -> dict:
    """Constrain each generated source reference to its actual available sentences."""
    choices = [{"type": "object", "properties": {
        "document_id": {"const": item.document_id},
        "sentence_indices": {"type": "array", "minItems": 1,
                             "maxItems": len(item.sentence_indices), "uniqueItems": True,
                             "items": {"type": "integer", "enum": list(item.sentence_indices)}}},
        "required": ["document_id", "sentence_indices"], "additionalProperties": False}
        for item in available]
    return {"type": "array", "maxItems": 6 if choices else 0,
            "items": {"anyOf": choices} if choices else {"type": "object"}}


class KAIRAgent:
    def __init__(self, client: OllamaClient, temperature: float, top_k: int, *, on_progress=None) -> None:
        self.on_progress = on_progress
        self.client = client
        self.temperature = temperature
        self.top_k = top_k
        self.stage = "plan"

    def call(self, state: KAIRState, stage: str, prompt: str, data: dict,
             schema: dict, iteration: int) -> dict:
        self.stage = stage
        first = len(self.client.calls)
        try:
            return self.client.chat(
                prompt, json.dumps(data, ensure_ascii=False), schema=schema,
                temperature=self.temperature, seed=state.seed,
            ).json_object()
        finally:
            for call in self.client.calls[first:]:
                call.update(agent_id=state.agent_id, stage=stage, iteration=iteration,
                            retrieval_step=len(state.query_history) + (stage == "plan"))

    def step(self, task: QuestionInput, state: KAIRState, shared: tuple[Evidence, ...],
             retriever: BM25Retriever, iteration: int, trace: dict) -> None:
        store = retriever.store
        if retriever.budget is not None:
            retriever.budget.check_retrieval()
        context = merge_context(store, state.context, shared)
        data = {"question": task.question, "known": [asdict(fact) for fact in state.known],
                "required": state.required, "query_history": state.query_history,
                "context": context_payload(context, store)}
        query = RAIRQueryPlanner.parse_payload(
            self.call(state, "plan", prompts.PLAN_PROMPT, data, prompts.PLAN_SCHEMA, iteration),
            previous_queries=[item["query"] for item in state.query_history],
        )
        self.stage = "retrieve"
        results = retriever.search(query, top_k=self.top_k)
        attempt = {"query": query, "iteration": iteration,
                   "retrieved_document_ids": [item.document.document_id for item in results],
                   "feedback": ""}
        state.query_history.append(attempt)
        trace.update(query=query, retrieved=[asdict(item) for item in results])
        if self.on_progress:
            publish(self.on_progress, 'retrieve', agent_id=state.agent_id, iteration=iteration, query=query,
                    documents=[{'title': r.document.title, 'document_id': r.document.document_id,
                                'score': r.score} for r in results])
        retrieved = tuple(Evidence(
            item.document.document_id, item.document.title,
            tuple(i for i, sentence in enumerate(item.document.sentences) if sentence.strip()),
            "\n".join(sentence for sentence in item.document.sentences if sentence.strip()),
        ) for item in results if any(sentence.strip() for sentence in item.document.sentences))
        available = merge_context(store, context, retrieved)
        data["context"] = context_payload(available, store)
        data["query_history"] = state.query_history
        sources = evidence_schema(available)
        update_schema = deepcopy(prompts.UPDATE_SCHEMA)
        if available:
            update_schema["properties"]["candidates"]["items"]["properties"]["evidence"] = {
                **sources, "minItems": 1}
        else:
            update_schema["properties"]["candidates"]["maxItems"] = 0
        update = self.call(state, "update", prompts.UPDATE_PROMPT, data,
                           update_schema, iteration)
        if set(update) != {"candidates", "required"}:
            raise ValueError("Knowledge update must contain candidates and required only.")
        proposed_required = requirements(update["required"])
        raw_candidates = update["candidates"]
        if not isinstance(raw_candidates, list) or len(raw_candidates) > 4:
            raise ValueError("Knowledge update allows at most four candidates.")
        candidates = []
        for i, raw in enumerate(raw_candidates, start=1):
            if (not isinstance(raw, dict) or set(raw) != {"statement", "evidence"}
                    or not isinstance(raw["statement"], str) or not raw["statement"].strip()):
                raise ValueError("Invalid candidate fields or statement.")
            evidence = parse_evidence(raw["evidence"], available, store, combine_documents=True)
            if not evidence:
                raise ValueError("A candidate requires exact source evidence.")
            candidates.append(KAIRFact(f"C{i}", raw["statement"].strip(), evidence))
        candidate_payloads = [{"candidate_id": item.fact_id, "statement": item.statement,
                               "evidence": [asdict(source) for source in item.evidence]}
                              for item in candidates]
        trace.update(candidates=candidate_payloads, proposed_required=proposed_required)
        if self.on_progress:
            publish(self.on_progress, 'update', agent_id=state.agent_id, iteration=iteration,
                    candidates=candidate_payloads, required=proposed_required)
        check_data = {**data, "candidates": candidate_payloads,
                      "proposed_required": proposed_required}
        check_schema = {**prompts.CHECK_SCHEMA, "properties": {
            **prompts.CHECK_SCHEMA["properties"],
            "keep_fact_ids": id_schema([item.fact_id for item in state.known]),
            "accepted_candidate_ids": id_schema([item.fact_id for item in candidates]),
        }}
        check = self.call(state, "check", prompts.CHECK_PROMPT, check_data,
                          check_schema, iteration)
        if set(check) != {"keep_fact_ids", "accepted_candidate_ids", "required"}:
            raise ValueError("Invalid fact-check fields.")
        keep = selected_ids(check["keep_fact_ids"], {item.fact_id for item in state.known})
        accepted = selected_ids(check["accepted_candidate_ids"], {item.fact_id for item in candidates})
        remaining = requirements(check["required"])
        known = [item for item in state.known if item.fact_id in keep]
        next_number = state.next_fact_number
        for candidate in candidates:
            if candidate.fact_id in accepted:
                known.append(KAIRFact(f"{state.agent_id}:F{next_number}",
                                      candidate.statement, candidate.evidence))
                next_number += 1
        if not known and not remaining:
            raise ValueError("An empty knowledge base cannot resolve the whole question.")
        trace["fact_check"] = check
        if self.on_progress:
            publish(self.on_progress, 'check', agent_id=state.agent_id, iteration=iteration,
                    candidates=candidate_payloads, fact_check=check)
        filter_schema = deepcopy(prompts.FILTER_SCHEMA)
        filter_schema["properties"]["selections"] = sources
        filtered = self.call(state, "filter", prompts.FILTER_PROMPT,
                             {"question": task.question, "known": [asdict(item) for item in known],
                              "required": remaining, "context": context_payload(available, store)},
                             filter_schema, iteration)
        if set(filtered) != {"selections"}:
            raise ValueError("Context filter must contain selections only.")
        refined = parse_evidence(filtered["selections"], available, store, combine_documents=True)
        # Commit K/R/D together only after all response and source checks succeed.
        state.known, state.required, state.context = known, remaining, refined
        state.next_fact_number = next_number
        state.initialized = True
        attempt["feedback"] = f"Accepted {len(accepted)} candidate(s); remaining: {remaining}"
        trace.update(known=[asdict(item) for item in known], required=list(remaining),
                     context=[asdict(item) for item in refined], complete=state.complete)
        if self.on_progress:
            publish(self.on_progress, 'filter', agent_id=state.agent_id, iteration=iteration,
                    known=trace['known'], required=trace['required'], context=trace['context'], complete=state.complete)
