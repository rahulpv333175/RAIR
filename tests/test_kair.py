"""Competitive integration tests replace only the Ollama HTTP transport."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch

import yaml

from src.experiments import run_kair, run_rair
from src.experiments.check_rair_pipeline import make_task
from src.kair import prompts
from src.kair.agent import merge_context, parse_evidence
from src.kair.controller import KAIRController, select_candidate
from src.kair.state import KAIRState
from src.llm.ollama_client import OllamaClient, OllamaError
from src.llm.prompts import RAIR_SYNTHESIZER_SCHEMA
from src.rair.state import Evidence
from src.retrieval.document_store import DocumentStore
from src.settings import load_settings
from test_rair_controller import wire_output


AUTHOR = "The Glass Orchard was written by Mira Solen."
BIRTH = "Mira Solen was born in the city of Nerava."


def selection(doc, indices=None):
    return {"document_id": f"pipeline-complete:D{doc}", "sentence_indices": indices or [0]}


def cycle(query="Glass Orchard author", claims=None, required=None, keep=None, accept=None, context=None):
    claims = [(AUTHOR, 1)] if claims is None else claims
    required = ["Identify Mira Solen's birth city."] if required is None else required
    candidates = [{"statement": statement, "evidence": [selection(doc)]} for statement, doc in claims]
    return [
        (prompts.PLAN_SCHEMA, {"query": query}),
        (prompts.UPDATE_SCHEMA, {"candidates": candidates, "required": required}),
        (prompts.CHECK_SCHEMA, {"keep_fact_ids": keep or [],
                               "accepted_candidate_ids": [f"C{i}" for i in range(1, len(claims)+1)]
                               if accept is None else accept,
                               "required": required}),
        (prompts.FILTER_SCHEMA, {"selections": context if context is not None else [selection(1)]}),
    ]


def answer(agent="A1"):
    return (RAIR_SYNTHESIZER_SCHEMA, {"answer": "Nerava", "citations": [f"{agent}:F1", f"{agent}:F2"],
                                     "abstain": False})


ABSTAIN = (RAIR_SYNTHESIZER_SCHEMA, {"answer": "", "citations": [], "abstain": True})


def complete_cycle(query="Glass Orchard Mira Solen born"):
    return cycle(query, [(AUTHOR, 1), (BIRTH, 2)], required=[], context=[selection(1), selection(2)])


class ScriptedClient(OllamaClient):
    def __init__(self, settings, script):
        super().__init__(settings)
        self.script = copy.deepcopy(script)
        self.requests = []

    def _request(self, path, payload=None):
        if path != "/api/chat" or not self.script:
            raise AssertionError("Unexpected extra HTTP call.")
        self.requests.append(payload)
        schema, output = self.script.pop(0)
        output = wire_output(schema, payload["format"], output, payload["messages"][1]["content"])
        return {"model": self.model, "done": True, "done_reason": "stop",
                "message": {"content": json.dumps(output)},
                "prompt_eval_count": 100, "eval_count": 20}


class CompetitionTests(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings()
        self.settings["kair"].update(max_iterations=1, steps_per_iteration=1)

    def run_script(self, script, *, task=None):
        client = ScriptedClient(self.settings, script)
        result = KAIRController(self.settings, client).run(task or make_task())
        self.assertLessEqual(result.usage["llm_calls"], KAIRController(self.settings, client).policy["max_llm_calls"])
        return result, client

    def test_first_complete_agent_stops_later_agents_and_resolves_sources(self):
        result, client = self.run_script(complete_cycle() + [answer()])
        self.assertEqual(result.status, "answered")
        self.assertEqual(result.stop_reason, "agent_complete")
        self.assertEqual(result.selected_agent_id, "A1")
        self.assertTrue(result.agents[0].complete)
        self.assertFalse(result.agents[1].initialized)
        self.assertEqual(result.agents[1].query_history, [])
        self.assertEqual({s["title"] for s in result.sources}, {"The Glass Orchard", "Mira Solen"})
        self.assertEqual(result.usage["retrieval_calls"], 1)
        self.assertEqual(result.usage["llm_calls"], 5)
        self.assertEqual(result.usage["prompt_tokens"], 500)
        update = json.loads(client.requests[1]["messages"][1]["content"])
        source = next(d for d in update["context"] if d["document_id"] == "pipeline-complete:D1")
        self.assertEqual(source["sentences"][0], {"sentence_index": 0, "text": AUTHOR})
        check = json.loads(client.requests[2]["messages"][1]["content"])
        self.assertEqual(check["candidates"][0]["candidate_id"], "C1")
        check_schema = client.requests[2]["format"]["properties"]
        self.assertEqual(check_schema["keep_fact_ids"]["maxItems"], 0)
        self.assertEqual(check_schema["accepted_candidate_ids"]["items"]["enum"], ["C1", "C2"])
        self.assertEqual(client.script, [])

    def test_filter_merges_valid_repeated_document_selections(self):
        self.settings['kair']['num_agents'] = 1
        steps = complete_cycle()
        steps[-1][1]['selections'] = [selection(1), selection(1, [1]), selection(2)]
        result, client = self.run_script(steps + [answer()])
        self.assertEqual(result.status, 'answered')
        self.assertEqual(result.agent_errors, [])
        self.assertEqual(result.agents[0].context[0].sentence_indices, (0, 1))
        self.assertEqual(result.agents[0].context[0].text,
                         '\n'.join(make_task().documents[0].sentences))
        self.assertEqual(client.script, [])

    def test_runtime_source_choices_are_bounded_to_each_available_document(self):
        _, client = self.run_script(complete_cycle() + [answer()])
        update_schema = client.requests[1]['format']['properties']['candidates']['items']['properties']['evidence']
        filter_schema = client.requests[3]['format']['properties']['selections']
        for schema in (update_schema, filter_schema):
            branches = schema['items']['anyOf']
            allowed = {branch['properties']['document_id']['const']:
                       branch['properties']['sentence_indices']['items']['enum'] for branch in branches}
            context = json.loads(client.requests[1]['messages'][1]['content'])['context']
            self.assertEqual(allowed, {d['document_id']:[s['sentence_index'] for s in d['sentences']]
                                       for d in context})
            self.assertNotIn('other-question:D1', allowed)

    def test_repeated_source_selection_cannot_add_unavailable_sentence(self):
        task = make_task()
        store = DocumentStore(task.question_id, task.documents)
        source = Evidence(task.documents[0].document_id, task.documents[0].title, (0,), AUTHOR)
        with self.assertRaisesRegex(ValueError, 'available context'):
            parse_evidence([selection(1), selection(1, [1])], (source,), store,
                           combine_documents=True)

    def test_second_agent_can_win_and_first_agent_private_facts_are_not_shared(self):
        result, client = self.run_script(cycle() + complete_cycle() + [answer("A2")])
        self.assertEqual(result.selected_agent_id, "A2")
        self.assertEqual(result.usage["llm_calls"], 9)
        first = client.requests[0]
        second = client.requests[4]
        self.assertEqual(first["messages"], second["messages"])
        self.assertEqual(first["options"]["seed"], 42)
        self.assertEqual(second["options"]["seed"], 43)
        self.assertEqual(first["options"]["temperature"], 0.7)
        self.assertEqual(json.loads(second["messages"][1]["content"])["known"], [])
        self.assertTrue(all(fact_id.startswith("A2:") for fact_id in result.prediction.citations))

    def test_fewest_requirements_selects_only_winners_context_then_rotates_order(self):
        self.settings["kair"].update(max_iterations=2)
        loser = cycle("Mira Solen birthplace", [(BIRTH, 2)],
                      ["Identify the author.", "Connect the author to the book."], context=[selection(2)])
        winner = cycle()
        finish = cycle("Mira Solen born city", [(BIRTH, 2)], [], keep=["A2:F1"],
                       context=[selection(1), selection(2)])
        result, client = self.run_script(loser + winner + finish + [answer("A2")])
        self.assertEqual(result.iterations[0]["selected_agent_id"], "A2")
        self.assertEqual([item["document_id"] for item in result.iterations[0]["shared_context"]],
                         ["pipeline-complete:D1"])
        self.assertEqual(result.iterations[1]["agent_order"], ["A2", "A1"])
        next_plan = json.loads(client.requests[8]["messages"][1]["content"])
        self.assertEqual([fact["fact_id"] for fact in next_plan["known"]], ["A2:F1"])
        self.assertEqual(result.selected_agent_id, "A2")
        self.assertEqual(len(result.agents[0].query_history), 1)

    def test_shared_source_context_can_be_used_but_private_fact_ids_cannot_transfer(self):
        self.settings["kair"].update(max_iterations=2)
        a1 = cycle()
        a2 = cycle("Mira Solen birthplace", [(BIRTH, 2)],
                   ["Find author.", "Link the author to the book."], context=[selection(2)])
        a2_next = cycle("Glass Orchard writer", [(AUTHOR, 1)], [], keep=["A2:F1"],
                        context=[selection(1), selection(2)])
        final = (RAIR_SYNTHESIZER_SCHEMA,
                 {"answer": "Nerava", "citations": ["A2:F1", "A2:F2"], "abstain": False})
        result, client = self.run_script(a1 + a2 + a2_next + [final])
        data = json.loads(client.requests[8]["messages"][1]["content"])
        self.assertEqual([f["fact_id"] for f in data["known"]], ["A2:F1"])
        self.assertEqual({item["document_id"] for item in data["context"]},
                         {"pipeline-complete:D1", "pipeline-complete:D2"})
        self.assertEqual(result.status, "answered")

    def test_incomplete_candidates_use_budget_and_final_abstention(self):
        result, _ = self.run_script(cycle() + cycle("Glass Orchard writer") + [ABSTAIN])
        self.assertEqual(result.status, "abstained")
        self.assertEqual(result.stop_reason, "max_iterations")
        self.assertEqual(result.selected_agent_id, "A1")
        self.assertEqual(result.usage["retrieval_calls"], 2)
        self.assertEqual(len(result.iterations), 1)

    def test_repeated_queries_stop_without_duplicate_retrievals(self):
        self.settings["kair"].update(steps_per_iteration=2, max_iterations=2)
        repeat = [(prompts.PLAN_SCHEMA, {"query": "Glass Orchard author"})]
        result, _ = self.run_script(cycle() + repeat + cycle() + repeat + repeat + repeat + [ABSTAIN])
        self.assertEqual(result.stop_reason, "all_agents_stalled")
        self.assertEqual(result.status, "abstained")
        self.assertEqual(result.usage["retrieval_calls"], 2)
        self.assertEqual(result.usage["llm_calls"], 13)

    def test_stalled_agent_is_relaunched_with_new_winners_context(self):
        self.settings["kair"].update(steps_per_iteration=2, max_iterations=2)
        repeat = [(prompts.PLAN_SCHEMA, {"query": "Glass Orchard author"})]
        # Both launches stall; the selected context is then shared before A2 retries.
        finish = cycle("Mira Solen city of birth", [(BIRTH, 2)], [], keep=["A2:F1"],
                       context=[selection(1), selection(2)])
        result, _ = self.run_script(cycle() + repeat + cycle() + repeat + finish + [answer("A2")])
        self.assertEqual(result.status, "answered")
        self.assertEqual(result.selected_agent_id, "A2")
        self.assertEqual(len(result.iterations), 2)

    def test_one_agent_failure_does_not_block_a_valid_competitor(self):
        result, _ = self.run_script([(prompts.PLAN_SCHEMA, OllamaError("disconnected"))]
                                    + complete_cycle() + [answer("A2")])
        self.assertEqual(result.status, "answered")
        self.assertIsNone(result.error)
        self.assertEqual(len(result.agent_errors), 1)
        self.assertEqual(result.agent_errors[0]["agent_id"], "A1")
        self.assertFalse(result.usage["token_counts_complete"])

    def test_all_agents_failed_is_an_error_and_empty_initial_R_is_not_completion(self):
        result, _ = self.run_script([(prompts.PLAN_SCHEMA, OllamaError("offline"))] * 2)
        self.assertEqual(result.status, "error")
        self.assertEqual(result.stop_reason, "all_agents_failed")
        self.assertEqual(result.usage["llm_calls"], 2)
        self.assertIsNone(result.selected_agent_id)
        self.assertTrue(result.prediction.abstain)

    def test_rejected_claims_reopen_requirements_and_do_not_enter_memory(self):
        bad = cycle(claims=[("The author is Rowan Vale.", 1)], accept=[], context=[])
        result, client = self.run_script(bad + cycle() + [ABSTAIN])
        self.assertEqual(result.agents[0].known, [])
        self.assertFalse(result.agents[0].complete)
        self.assertNotIn("Rowan Vale", client.requests[-1]["messages"][1]["content"])

    def test_existing_unsupported_fact_can_be_removed_before_append(self):
        self.settings["kair"].update(steps_per_iteration=2)
        replace = cycle("Mira Solen born city", [(BIRTH, 2)], ["Identify author."],
                        keep=[], context=[selection(2)])
        result, _ = self.run_script(cycle() + replace + complete_cycle() + [answer("A2")])
        self.assertEqual([f.fact_id for f in result.agents[0].known], ["A1:F2"])
        self.assertEqual(result.agents[0].next_fact_number, 3)

    def test_invalid_filter_does_not_partially_commit_verified_state(self):
        broken = complete_cycle()
        broken[-1] = (prompts.FILTER_SCHEMA,
                      {"selections": [{"document_id": "other-question:D1", "sentence_indices": [0]}]})
        result, _ = self.run_script(broken + complete_cycle() + [answer("A2")])
        self.assertEqual(result.agents[0].known, [])
        self.assertFalse(result.agents[0].initialized)
        self.assertEqual(result.agent_errors[0]["stage"], "filter")
        self.assertEqual(result.selected_agent_id, "A2")
        self.assertEqual(result.usage["retrieval_calls"], 2)

    def test_unknown_fact_ids_cannot_enter_check_or_final_answer(self):
        broken = cycle()
        broken[2] = (prompts.CHECK_SCHEMA,
                     {"keep_fact_ids": ["A2:F1"], "accepted_candidate_ids": ["C1"], "required": []})
        result, _ = self.run_script(broken[:3] + complete_cycle() + [answer("A2")])
        self.assertEqual(result.agent_errors[0]["stage"], "check")
        final = (RAIR_SYNTHESIZER_SCHEMA, {"answer": "Nerava", "citations": ["A2:F1"], "abstain": False})
        result, _ = self.run_script(complete_cycle() + [final])
        self.assertEqual(result.status, "error")
        self.assertEqual(result.prediction.answer, "")
        self.assertEqual(result.error["stage"], "synthesize")

    def test_empty_evidence_cannot_support_a_candidate_or_complete_empty_knowledge(self):
        bad = complete_cycle()
        bad[1][1]["candidates"][0]["evidence"] = []
        result, _ = self.run_script(bad[:2] + complete_cycle() + [answer("A2")])
        self.assertEqual(result.agent_errors[0]["stage"], "update")
        empty = cycle(claims=[], required=[], context=[])
        result, _ = self.run_script(empty[:3] + complete_cycle() + [answer("A2")])
        self.assertEqual(result.agent_errors[0]["stage"], "check")

    def test_no_results_leave_missing_information_and_still_allow_other_agent(self):
        no_results = cycle("qqqqnonexistent", [], ["Find evidence."], context=[])
        result, client = self.run_script(no_results + complete_cycle() + [answer("A2")])
        self.assertEqual(result.agents[0].query_history[0]["retrieved_document_ids"], [])
        self.assertFalse(result.agents[0].complete)
        self.assertEqual(result.selected_agent_id, "A2")
        self.assertEqual(client.requests[1]['format']['properties']['candidates']['maxItems'], 0)
        self.assertEqual(client.requests[3]['format']['properties']['selections']['maxItems'], 0)

    def test_new_questions_start_with_fresh_memory_and_detached_traces(self):
        client = ScriptedClient(self.settings, complete_cycle() + [answer()]
                                + complete_cycle() + [answer()])
        controller = KAIRController(self.settings, client)
        first = controller.run(make_task())
        second = controller.run(make_task())
        self.assertEqual(len(first.llm_calls), 5)
        self.assertEqual(len(second.llm_calls), 5)
        self.assertIsNot(first.llm_calls, second.llm_calls)
        self.assertIsNot(first.agents[0].known, second.agents[0].known)
        self.assertEqual(len(second.agents[0].known), 2)

    def test_only_initialized_healthy_candidates_participate_in_selection(self):
        empty = KAIRState("A0", 1)
        first = KAIRState("A1", 2, required=["x"], initialized=True)
        second = KAIRState("A2", 3, required=["x"], initialized=True)
        self.assertFalse(empty.complete)
        self.assertIs(select_candidate([empty, first, second]), first)
        first.status = "error"
        self.assertIs(select_candidate([empty, first, second]), second)

    def test_invalid_budgets_sampling_and_cross_question_inputs_are_rejected(self):
        for field in ("num_agents", "max_iterations", "steps_per_iteration"):
            for value in (0, -1, True, 1.5):
                config = copy.deepcopy(self.settings)
                config["kair"][field] = value
                with self.assertRaises(ValueError):
                    KAIRController(config, ScriptedClient(config, []))
        for value in (0.0, True, float("nan"), float("inf")):
            config = copy.deepcopy(self.settings)
            config["kair"]["temperature"] = value
            with self.assertRaises(ValueError):
                KAIRController(config, ScriptedClient(config, []))
        task = make_task()
        with self.assertRaisesRegex(ValueError, "Cannot mix"):
            self.run_script([], task=type(task)("other", task.question, task.documents))

    def test_pruned_source_sentences_cannot_be_selected_from_document_by_id(self):
        task = make_task()
        store = DocumentStore(task.question_id, task.documents)
        available = (Evidence("pipeline-complete:D1", "The Glass Orchard", (0,), AUTHOR),)
        with self.assertRaisesRegex(ValueError, "not in the available context"):
            parse_evidence([selection(1, [1])], available, store)
        other = Evidence("pipeline-complete:D1", "The Glass Orchard", (1,), task.documents[0].sentences[1])
        merged = merge_context(store, available, (other,))
        self.assertEqual(merged[0].sentence_indices, (0, 1))
        self.assertEqual(merged[0].text, "\n".join(task.documents[0].sentences))

    def test_multiple_candidate_citations_to_one_document_preserve_exact_sentences(self):
        task = make_task()
        store = DocumentStore(task.question_id, task.documents)
        available = (Evidence("pipeline-complete:D1", "The Glass Orchard", (0, 1),
                              "\n".join(task.documents[0].sentences)),)
        evidence = parse_evidence([selection(1, [0]), selection(1, [1])], available, store,
                                  combine_documents=True)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].sentence_indices, (0, 1))
        self.assertEqual(evidence[0].text, "\n".join(task.documents[0].sentences))


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        task = make_task()
        self.row = {"_id": task.question_id, "question": task.question, "answer": "Nerava",
                    "context": [[d.title, list(d.sentences)] for d in task.documents],
                    "supporting_facts": [["The Glass Orchard", 0], ["Mira Solen", 0]]}
        self.settings = load_settings()
        self.settings["dataset"]["path"] = str(self.root / "dataset.json")
        self.config = self.root / "settings.yaml"
        self.config.write_text(yaml.safe_dump(self.settings), encoding="utf-8")

    def run_cli(self, rows, script, name="output.jsonl", limit=None):
        (self.root / "dataset.json").write_text(json.dumps(rows), encoding="utf-8")
        client = ScriptedClient(self.settings, script)
        with patch.object(run_rair, "OllamaClient", return_value=client), patch.object(
            client, "check_ready", return_value={"model": {"digest": "test"}}
        ), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = run_kair.main(["--config", str(self.config), "--output", str(self.root / name),
                                  "--limit", str(limit or len(rows))])
        return code, client

    def records(self, name="output.jsonl"):
        return [json.loads(line) for line in (self.root / name).read_text(encoding="utf-8").splitlines()]

    def test_kair_cli_writes_policy_agents_and_scores_including_failed_questions(self):
        bad = {**self.row, "_id": "second"}
        code, _ = self.run_cli([self.row, bad], complete_cycle() + [answer()]
                               + [(prompts.PLAN_SCHEMA, OllamaError("offline"))] * 2)
        self.assertEqual(code, 1)
        metadata, first, second, summary = self.records()
        self.assertEqual(metadata["system"], "KAIR")
        self.assertEqual(metadata["policy"]["agent_seeds"], [42, 43])
        self.assertEqual(metadata["policy"]["max_retrieval_calls"], 8)
        self.assertEqual(first["selected_agent_id"], "A1")
        self.assertEqual(len(first["agents"]), 2)
        self.assertEqual(second["status"], "error")
        self.assertEqual(summary["exact_match"], 0.5)
        self.assertEqual(summary["error"], 1)
        self.assertEqual(summary["agent_error_count"], 2)

    def test_gold_mutation_cannot_change_inference_or_competitive_selection(self):
        code, first = self.run_cli([self.row], complete_cycle() + [answer()], "first.jsonl")
        self.assertEqual(code, 0)
        changed = {**self.row, "answer": "__SECRET_GOLD__",
                   "supporting_facts": [["__SECRET_SUPPORT__", 999]]}
        code, second = self.run_cli([changed], complete_cycle() + [answer()], "second.jsonl")
        self.assertEqual(code, 0)
        self.assertEqual(first.requests, second.requests)
        self.assertNotIn("__SECRET_", json.dumps(second.requests))
        self.assertEqual(self.records("first.jsonl")[1]["selected_agent_id"],
                         self.records("second.jsonl")[1]["selected_agent_id"])

    def test_existing_output_and_out_of_range_selection_do_not_generate(self):
        (self.root / "output.jsonl").write_text("keep", encoding="utf-8")
        code, client = self.run_cli([self.row], [])
        self.assertEqual(code, 1)
        self.assertEqual((self.root / "output.jsonl").read_text(encoding="utf-8"), "keep")
        self.assertEqual(client.calls, [])
        code, client = self.run_cli([self.row], [], "range.jsonl", limit=2)
        self.assertEqual(code, 1)
        self.assertEqual(client.calls, [])

    def test_interruption_preserves_completed_record(self):
        code, _ = self.run_cli([self.row, {**self.row, "_id": "second"}],
                               complete_cycle() + [answer()]
                               + [(prompts.PLAN_SCHEMA, KeyboardInterrupt())])
        self.assertEqual(code, 130)
        self.assertEqual(len(self.records()), 2)
        self.assertEqual(self.records()[1]["status"], "answered")


if __name__ == "__main__":
    unittest.main()
