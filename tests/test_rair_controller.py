"""Integration tests run every real RAIR role, replacing only Ollama's transport."""

import copy
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

import yaml

from src.experiments.check_rair_pipeline import make_task
from src.experiments import run_rair
from src.llm import prompts
from src.llm.ollama_client import OllamaClient, OllamaError
from src.rair.controller import RAIRController
from src.settings import load_settings


GAPS = {"gaps": [
    {"gap_id": "G1", "description": "Identify the author of The Glass Orchard.",
     "priority": "high", "depends_on": []},
    {"gap_id": "G2", "description": "Identify the birth city of the author identified in G1.",
     "priority": "high", "depends_on": ["G1"]},
]}


def decision(*, accepted=True, resolves=True):
    return {"decisions": [{
        "candidate_id": "C1", "supported_by_evidence": accepted,
        "relevant_to_gap": True, "answer_type_ok": True,
        "contains_unresolved_placeholder": False,
        "resolves_gap": resolves if accepted else False,
        "reason": "Directly supported." if accepted else "Unsupported claim.",
    }]}


def round_script(document_id, query, claim, *, accepted=True, resolves=True):
    return [
        (prompts.RAIR_QUERY_PLANNER_SCHEMA, {"query": query}),
        (prompts.RAIR_EVIDENCE_FILTER_SCHEMA,
         {"selections": [{"document_id": document_id, "sentence_indices": [0]}]}),
        (prompts.RAIR_FACT_EXTRACTOR_SCHEMA,
         {"candidates": [{"candidate_id": "C1", "statement": claim, "evidence_ids": ["E1"]}]}),
        (prompts.RAIR_VERIFIER_SCHEMA, decision(accepted=accepted, resolves=resolves)),
    ]


def full_script():
    return [(prompts.RAIR_DECOMPOSER_SCHEMA, copy.deepcopy(GAPS))] + round_script(
        "pipeline-complete:D1", "Glass Orchard author",
        "The Glass Orchard was written by Mira Solen.",
    ) + round_script(
        "pipeline-complete:D2", "Mira Solen birthplace",
        "Mira Solen was born in the city of Nerava.",
    ) + [(prompts.RAIR_SYNTHESIZER_SCHEMA,
          {"answer": "Nerava", "citations": ["F1", "F2"], "abstain": False})]


def wire_output(expected, actual, output, user_prompt):
    """Keep regression scenarios while adapting their old role payload notation."""
    branch = actual.get("oneOf", [actual])[0]
    if set(branch.get("properties", {})) != set(expected.get("properties", {})):
        raise AssertionError("Roles executed in the wrong order.")
    if isinstance(output, BaseException):
        raise output
    output = copy.deepcopy(output)
    properties = branch.get("properties", {})
    if "selections" in properties and properties["selections"]["items"].get("type") == "string":
        aliases = {(title, int(index)): alias for alias, title, index in re.findall(
            r"^(E\d+) \| (.*?) \[S(\d+)\]:", user_prompt, flags=re.MULTILINE)}
        selections = []
        for source in output["selections"]:
            match = re.fullmatch(r"pipeline-complete:D(\d+)", source["document_id"])
            title = make_task().documents[int(match[1])-1].title if match else "missing"
            selections.extend(aliases.get((title, i), "E999999") for i in source["sentence_indices"])
        output["selections"] = selections
    elif "candidates" in properties and "candidate_id" not in properties["candidates"]["items"]["properties"]:
        for item in output["candidates"]:
            item.pop("candidate_id", None)
    elif "decisions" in properties and properties["decisions"]["type"] == "object":
        output["decisions"] = {item["candidate_id"]: {key: value for key, value in item.items()
                                                       if key != "candidate_id"}
                               for item in output["decisions"]}
    return output


class ScriptedClient(OllamaClient):
    def __init__(self, settings, script):
        super().__init__(settings)
        self.script = list(script)
        self.requests = []

    def _request(self, path, payload=None):
        if path != "/api/chat":
            raise AssertionError(f"Unexpected endpoint: {path}")
        self.requests.append(payload)
        if not self.script:
            raise AssertionError("Unexpected extra LLM call.")
        schema, output = self.script.pop(0)
        output = wire_output(schema, payload["format"], output, payload["messages"][1]["content"])
        raw = {"done": True, "done_reason": "stop", "model": self.model,
               "message": {"content": json.dumps(output)},
               "prompt_eval_count": 100, "eval_count": 20}
        return raw


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings()

    def run_script(self, script, *, rounds=5, task=None):
        self.settings["rair"]["max_rounds"] = rounds
        client = ScriptedClient(self.settings, script)
        result = RAIRController(self.settings, client).run(task or make_task())
        return result, client

    def test_complete_two_hop_chain_and_exact_source_citations(self):
        result, client = self.run_script(full_script())
        self.assertEqual(result.status, "answered")
        self.assertEqual(result.stop_reason, "all_gaps_resolved")
        self.assertEqual(result.prediction.answer, "Nerava")
        self.assertTrue(result.state.is_complete())
        self.assertEqual([item["gap_id"] for item in result.rounds], ["G1", "G2"])
        self.assertEqual([source["sentence_index"] for source in result.sources], [0, 0])
        self.assertEqual(result.sources[1]["text"], make_task().documents[1].sentences[0])
        self.assertEqual(result.usage["llm_calls"], 10)
        self.assertEqual(result.usage["retrieval_calls"], 2)
        self.assertEqual(result.usage["prompt_tokens"], 1000)
        self.assertEqual(result.usage["completion_tokens"], 200)
        self.assertTrue(result.usage["token_counts_complete"])
        self.assertEqual(client.script, [])
        self.assertIn("Mira Solen", client.requests[5]["messages"][1]["content"])
        self.assertEqual(len(json.loads(json.dumps(result.to_dict()))["rounds"]), 2)

    def test_round_limit_synthesizes_partial_knowledge_and_abstains(self):
        script = full_script()[:5] + [(prompts.RAIR_SYNTHESIZER_SCHEMA,
            {"answer": "", "citations": [], "abstain": True})]
        result, client = self.run_script(script, rounds=1)
        self.assertEqual(result.status, "abstained")
        self.assertEqual(result.stop_reason, "max_rounds")
        self.assertEqual(result.state.current_round, 1)
        self.assertEqual(result.usage["llm_calls"], 6)
        self.assertEqual(result.sources, [])
        self.assertEqual(client.script, [])

    def test_no_retrieval_skips_other_roles_and_reformulates_with_feedback(self):
        script = [(prompts.RAIR_DECOMPOSER_SCHEMA, GAPS),
                  (prompts.RAIR_QUERY_PLANNER_SCHEMA, {"query": "zzzznonexistent"}),
                  (prompts.RAIR_QUERY_PLANNER_SCHEMA, {"query": "yyyyynonexistent"}),
                  (prompts.RAIR_SYNTHESIZER_SCHEMA,
                   {"answer": "", "citations": [], "abstain": True})]
        result, client = self.run_script(script, rounds=2)
        self.assertEqual(result.status, "abstained")
        self.assertEqual(result.usage["llm_calls"], 4)
        self.assertEqual(result.state.verified_facts, [])
        self.assertIn("No relevant source evidence", client.requests[2]["messages"][1]["content"])
        self.assertEqual(result.rounds[0]["candidates"], [])

    def test_filter_can_reject_all_retrieved_documents(self):
        script = [(prompts.RAIR_DECOMPOSER_SCHEMA, GAPS),
                  (prompts.RAIR_QUERY_PLANNER_SCHEMA, {"query": "Glass Orchard author"}),
                  (prompts.RAIR_EVIDENCE_FILTER_SCHEMA, {"selections": []}),
                  (prompts.RAIR_SYNTHESIZER_SCHEMA,
                   {"answer": "", "citations": [], "abstain": True})]
        result, _ = self.run_script(script, rounds=1)
        self.assertEqual(result.status, "abstained")
        self.assertTrue(result.state.query_history[0].success)
        self.assertIn("No relevant", result.state.query_history[0].evidence_feedback)
        self.assertEqual(result.usage["llm_calls"], 4)

    def test_rejected_candidate_never_enters_shared_memory(self):
        script = [(prompts.RAIR_DECOMPOSER_SCHEMA, GAPS)] + round_script(
            "pipeline-complete:D1", "Glass Orchard author", "The author is Rowan Vale.",
            accepted=False,
        ) + [(prompts.RAIR_SYNTHESIZER_SCHEMA,
              {"answer": "", "citations": [], "abstain": True})]
        result, client = self.run_script(script, rounds=1)
        self.assertEqual(result.status, "abstained")
        self.assertEqual(result.state.verified_facts, [])
        self.assertEqual([g.gap_id for g in result.state.actionable_gaps()], ["G1"])
        self.assertNotIn("Rowan Vale", client.requests[-1]["messages"][1]["content"])

    def test_accepted_but_nonresolving_claim_does_not_unlock_dependency(self):
        script = full_script()[:5]
        script[-1] = (prompts.RAIR_VERIFIER_SCHEMA, decision(resolves=False))
        script += [(prompts.RAIR_SYNTHESIZER_SCHEMA,
                    {"answer": "", "citations": [], "abstain": True})]
        result, _ = self.run_script(script, rounds=1)
        self.assertEqual(len(result.state.verified_facts), 1)
        self.assertEqual([g.gap_id for g in result.state.actionable_gaps()], ["G1"])

    def test_repeated_query_uses_bounded_question_fallback_and_abstains_without_facts(self):
        script = [(prompts.RAIR_DECOMPOSER_SCHEMA, GAPS),
                  (prompts.RAIR_QUERY_PLANNER_SCHEMA, {"query": "zzzznonexistent"}),
                  (prompts.RAIR_QUERY_PLANNER_SCHEMA, {"query": " ZZZZnonexistent "}),
                  (prompts.RAIR_EVIDENCE_FILTER_SCHEMA, {"selections": []}),
                  (prompts.RAIR_SYNTHESIZER_SCHEMA,
                   {"answer": "", "citations": [], "abstain": True})]
        result, _ = self.run_script(script, rounds=2)
        self.assertEqual(result.status, "abstained")
        self.assertEqual(result.stop_reason, "max_rounds")
        self.assertIsNone(result.error)
        self.assertEqual(result.usage["retrieval_calls"], 2)
        self.assertEqual(result.usage["llm_calls"], 5)
        self.assertEqual(result.rounds[-1]["query_origin"], "original_question_fallback")
        self.assertTrue(result.prediction.abstain)

    def test_transport_error_is_preserved_and_token_counts_are_incomplete(self):
        result, _ = self.run_script([
            (prompts.RAIR_DECOMPOSER_SCHEMA, OllamaError("server unavailable"))])
        self.assertEqual(result.status, "error")
        self.assertEqual(result.error["stage"], "decompose")
        self.assertEqual(result.usage["llm_calls"], 1)
        self.assertFalse(result.usage["token_counts_complete"])
        self.assertEqual(result.llm_calls[0]["error"], "server unavailable")

    def test_invalid_decomposition_fails_closed(self):
        result, _ = self.run_script([(prompts.RAIR_DECOMPOSER_SCHEMA, {"gaps": []})])
        self.assertEqual(result.status, "error")
        self.assertEqual(result.error["stage"], "decompose")
        self.assertEqual(result.state.gaps, [])

    def test_unknown_final_citation_is_an_error_not_an_answer(self):
        script = full_script()
        script[-1] = (prompts.RAIR_SYNTHESIZER_SCHEMA,
                      {"answer": "Nerava", "citations": ["F99"], "abstain": False})
        result, _ = self.run_script(script)
        self.assertEqual(result.status, "error")
        self.assertEqual(result.error["stage"], "synthesize")
        self.assertEqual(result.prediction.answer, "")
        self.assertEqual(result.sources, [])

    def test_invalid_evidence_keeps_partial_trace_without_admitting_claim(self):
        script = full_script()[:3]
        script[-1] = (prompts.RAIR_EVIDENCE_FILTER_SCHEMA,
                      {"selections": [{"document_id": "not-retrieved", "sentence_indices": [0]}]})
        result, _ = self.run_script(script)
        self.assertEqual(result.error["stage"], "filter")
        self.assertEqual(len(result.rounds), 1)
        self.assertEqual(result.state.verified_facts, [])

    def test_empty_extraction_skips_verifier(self):
        script = full_script()[:4]
        script[-1] = (prompts.RAIR_FACT_EXTRACTOR_SCHEMA, {"candidates": []})
        script += [(prompts.RAIR_SYNTHESIZER_SCHEMA,
                    {"answer": "", "citations": [], "abstain": True})]
        result, client = self.run_script(script, rounds=1)
        self.assertEqual(result.status, "abstained")
        self.assertEqual(result.usage["llm_calls"], 5)
        self.assertEqual(client.script, [])

    def test_reusing_controller_keeps_traces_and_memory_separate(self):
        client = ScriptedClient(self.settings, full_script() + full_script())
        controller = RAIRController(self.settings, client)
        first = controller.run(make_task())
        second = controller.run(make_task())
        self.assertEqual(len(first.llm_calls), 10)
        self.assertEqual(len(second.llm_calls), 10)
        self.assertIsNot(first.llm_calls, second.llm_calls)
        self.assertEqual(len(second.state.verified_facts), 2)

    def test_invalid_budget_and_cross_question_documents_are_rejected(self):
        for invalid in (0, -1, True, 1.5):
            self.settings["rair"]["max_rounds"] = invalid
            with self.assertRaises(ValueError):
                RAIRController(self.settings, ScriptedClient(self.settings, []))
        self.settings["rair"]["max_rounds"] = 5
        task = make_task()
        task = type(task)("other", task.question, task.documents)
        with self.assertRaisesRegex(ValueError, "Cannot mix"):
            self.run_script([], task=task)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        task = make_task()
        self.record = {
            "_id": task.question_id, "question": task.question, "answer": "Nerava",
            "context": [[doc.title, list(doc.sentences)] for doc in task.documents],
            "supporting_facts": [["The Glass Orchard", 0], ["Mira Solen", 0]],
        }
        self.dataset = self.root / "dataset.json"
        self.settings = load_settings()
        self.settings["dataset"]["path"] = str(self.dataset)
        self.config = self.root / "settings.yaml"
        self.config.write_text(yaml.safe_dump(self.settings), encoding="utf-8")

    def run_cli(self, records, script, name="result.jsonl", limit=None):
        self.dataset.write_text(json.dumps(records), encoding="utf-8")
        client = ScriptedClient(self.settings, script)
        with patch.object(run_rair, "OllamaClient", return_value=client), patch.object(
            client, "check_ready", return_value={"model": {"digest": "test-model"}}
        ), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = run_rair.main([
                "--config", str(self.config), "--limit", str(limit or len(records)),
                "--output", str(self.root / name),
            ])
        return code, client

    def read_output(self, name="result.jsonl"):
        return [json.loads(line) for line in (self.root / name).read_text(encoding="utf-8").splitlines()]

    def test_full_cli_persists_failures_and_scores_all_questions(self):
        bad = {**self.record, "_id": "second"}
        code, _ = self.run_cli([self.record, bad], full_script() + [
            (prompts.RAIR_DECOMPOSER_SCHEMA, OllamaError("server failed"))])
        self.assertEqual(code, 1)
        metadata, first, second, summary = self.read_output()
        self.assertEqual(metadata["record_type"], "metadata")
        self.assertEqual(first["prediction"]["answer"], "Nerava")
        self.assertEqual(second["status"], "error")
        self.assertEqual(second["usage"]["llm_calls"], 1)
        self.assertEqual(summary["num_questions"], 2)
        self.assertEqual(summary["exact_match"], 0.5)
        self.assertEqual(summary["answer_coverage"], 0.5)
        self.assertEqual(summary["error"], 1)
        self.assertEqual(summary["stop_reasons"], {"all_gaps_resolved": 1, "error": 1})

    def test_changing_gold_does_not_change_any_inference_request(self):
        code, first = self.run_cli([self.record], full_script(), "first.jsonl")
        self.assertEqual(code, 0)
        changed = {**self.record, "answer": "__SECRET_GOLD__",
                   "supporting_facts": [["__SECRET_SUPPORT__", 999]]}
        code, second = self.run_cli([changed], full_script(), "second.jsonl")
        self.assertEqual(code, 0)
        self.assertEqual(first.requests, second.requests)
        self.assertNotIn("__SECRET_", json.dumps(second.requests))
        self.assertEqual(self.read_output("second.jsonl")[-1]["exact_match"], 0.0)

    def test_existing_output_is_preserved_without_generation_calls(self):
        target = self.root / "result.jsonl"
        target.write_text("keep this", encoding="utf-8")
        code, client = self.run_cli([self.record], [])
        self.assertEqual(code, 1)
        self.assertEqual(target.read_text(encoding="utf-8"), "keep this")
        self.assertEqual(client.calls, [])

    def test_out_of_range_selection_does_not_call_model(self):
        code, client = self.run_cli([self.record], [], limit=2)
        self.assertEqual(code, 1)
        self.assertEqual(client.calls, [])
        self.assertFalse((self.root / "result.jsonl").exists())

    def test_interrupted_batch_keeps_already_completed_question(self):
        bad = {**self.record, "_id": "second"}
        code, _ = self.run_cli([self.record, bad], full_script() + [
            (prompts.RAIR_DECOMPOSER_SCHEMA, KeyboardInterrupt())])
        self.assertEqual(code, 130)
        records = self.read_output()
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["status"], "answered")
        self.assertNotIn("summary", [item["record_type"] for item in records])


class ClientTraceTests(unittest.TestCase):
    def test_truncated_generation_records_tokens_and_error(self):
        client = OllamaClient(load_settings())
        raw = {"done": True, "done_reason": "length", "prompt_eval_count": 80,
               "eval_count": 512, "message": {"content": '{"gaps":'}}
        with patch.object(client, "_request", return_value=raw):
            result = RAIRController(load_settings(), client).run(make_task())
        self.assertEqual(result.status, "error")
        self.assertEqual(result.usage["completion_tokens"], 512)
        self.assertIn("token limit", result.llm_calls[0]["error"])

    def test_non_json_generation_is_recorded_but_never_accepted(self):
        client = OllamaClient(load_settings())
        raw = {"done": True, "message": {"content": "not JSON"},
               "prompt_eval_count": 80, "eval_count": 3}
        with patch.object(client, "_request", return_value=raw):
            result = RAIRController(load_settings(), client).run(make_task())
        self.assertEqual(result.status, "error")
        self.assertIn("not valid JSON", result.error["message"])
        self.assertEqual(result.llm_calls[0]["raw"]["message"]["content"], "not JSON")


if __name__ == "__main__":
    unittest.main()
