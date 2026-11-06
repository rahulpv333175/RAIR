"""Common protocol tests use real controllers and replace only Ollama transport."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from src.datasets.hotpotqa import load_hotpotqa
from src.evaluation.budget import BudgetExhausted, RunBudget
from src.evaluation.paired import (
    aggregate, audit_result, fingerprint, load_manifest_examples, prepare_manifest,
    schedule, score_result,
)
from src.experiments import compare
from src.experiments.check_rair_pipeline import make_task
from src.kair.controller import KAIRController
from src.llm.ollama_client import OllamaClient, OllamaError
from src.rair.controller import RAIRController
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.document_store import DocumentStore
from src.settings import load_settings
from test_kair import ABSTAIN, ScriptedClient as KAIRClient, answer, complete_cycle, cycle
from test_rair_controller import ScriptedClient as RAIRClient, full_script


class BudgetTests(unittest.TestCase):
    def test_reserved_final_call_and_no_calls_after_final(self):
        budget = RunBudget(1, 2)
        budget.consume_llm(final_answer=False)
        with self.assertRaises(BudgetExhausted):
            budget.consume_llm(final_answer=False)
        self.assertEqual(budget.llm_calls, 1)
        budget.consume_llm(final_answer=True)
        for final in (True, False):
            with self.assertRaises(BudgetExhausted):
                budget.consume_llm(final_answer=final)
        self.assertEqual((budget.llm_calls, budget.final_calls), (2, 1))

    def test_invalid_budgets(self):
        for retrievals, calls in ((0, 2), (True, 2), (1, 1), (1, 2.5)):
            with self.assertRaises(ValueError):
                RunBudget(retrievals, calls)

    def test_bm25_blocks_before_an_extra_search(self):
        budget = RunBudget(1, 2)
        retriever = BM25Retriever(DocumentStore(make_task().question_id, make_task().documents), budget=budget)
        retriever.search("Glass Orchard", top_k=3)
        with self.assertRaises(BudgetExhausted):
            retriever.search("Mira Solen", top_k=3)
        self.assertEqual(budget.retrieval_calls, 1)

    def test_failed_transport_consumes_one_call_and_blocked_call_is_not_logged(self):
        client = RAIRClient(load_settings(), [({}, OllamaError("offline"))])
        client.budget = RunBudget(1, 2)
        with self.assertRaises(OllamaError):
            client.chat("system", "user", schema={})
        with self.assertRaises(BudgetExhausted):
            client.chat("system", "user")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.budget.llm_calls, 1)

    def run_controller(self, system, script, retrievals=1, calls=18):
        settings = load_settings()
        client = (RAIRClient if system == "RAIR" else KAIRClient)(settings, script)
        client.budget = RunBudget(retrievals, calls)
        client.generation_temperature = settings["evaluation"]["temperature"]
        controller = RAIRController if system == "RAIR" else KAIRController
        result = controller(settings, client).run(make_task()).to_dict()
        audit_result(result, make_task(), client.budget, settings, 42, system)
        self.assertEqual(result["stop_reason"], "budget_exhausted")
        self.assertEqual(result["status"], "abstained")
        self.assertIsNone(result["error"])
        self.assertEqual(client.script, [])
        self.assertEqual(client.budget.final_calls, 1)
        return result

    def test_rair_retrieval_cap_stops_before_planner_and_preserves_partial_facts(self):
        result = self.run_controller("RAIR", full_script()[:5] + [ABSTAIN])
        self.assertEqual(result["usage"]["llm_calls"], 6)
        self.assertEqual(len(result["state"]["verified_facts"]), 1)

    def test_kair_retrieval_cap_stops_before_planner_and_preserves_partial_facts(self):
        result = self.run_controller("KAIR", cycle() + [ABSTAIN])
        self.assertEqual(result["usage"]["llm_calls"], 5)
        self.assertEqual(len(result["agents"][0]["known"]), 1)
        self.assertEqual(result["agent_errors"], [])

    def test_both_systems_can_finalize_with_no_committed_facts_at_llm_limit(self):
        for system, script in (("RAIR", full_script()[:1]), ("KAIR", cycle()[:1])):
            with self.subTest(system=system):
                result = self.run_controller(system, script + [ABSTAIN], calls=2)
                self.assertEqual(result["usage"]["llm_calls"], 2)


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.path = self.root / "paired.jsonl"
        self.dataset = self.root / "data.json"
        task = make_task()
        self.row = {"_id": task.question_id, "question": task.question, "answer": "Nerava",
                    "context": [[d.title, list(d.sentences)] for d in task.documents],
                    "supporting_facts": [["The Glass Orchard", 0], ["Mira Solen", 0]]}
        self.write_data()
        self.settings = load_settings()
        self.settings["dataset"]["path"] = str(self.dataset)
        self.settings["evaluation"].update(sample_size=1, exclude_first_n=1)
        self.manifest = prepare_manifest(self.settings)

    def write_data(self):
        self.dataset.write_text(json.dumps([{**self.row, "_id": "development"}, self.row]), encoding="utf-8")

    def execute(self, scripts=None, *, resume=False, path=None):
        scripts = list(scripts if scripts is not None else [
            ("RAIR", full_script()), ("KAIR", complete_cycle() + [answer()]),
            ("KAIR", complete_cycle() + [answer()]), ("RAIR", full_script()),
        ])
        clients = []
        ready = OllamaClient(self.settings)
        raw = {"done": True, "message": {"content": '{"ready": true}'},
               "prompt_eval_count": 10, "eval_count": 4}
        def factory(settings):
            if not clients:
                client = ready
            else:
                system, script = scripts.pop(0)
                client = (RAIRClient if system == "RAIR" else KAIRClient)(settings, script)
            clients.append(client)
            return client
        environment = {"model": {"digest": "frozen-model"}, "server": {"version": "test"}}
        with patch.object(compare, "OllamaClient", side_effect=factory), patch.object(
            ready, "_request", return_value=raw
        ), patch.object(ready, "check_ready", return_value=environment), redirect_stdout(io.StringIO()):
            summary = compare.run(self.manifest, path or self.path, resume=resume)
        self.assertEqual(scripts, [])
        return summary, clients

    def records(self):
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]

    def test_manifest_excludes_development_and_schedule_balances_order(self):
        self.assertEqual(self.manifest["excluded_question_ids"], ["development"])
        self.assertEqual(self.manifest["questions"][0]["question_id"], self.row["_id"])
        again = prepare_manifest(self.settings)
        self.assertEqual(again["questions"], self.manifest["questions"])
        planned = schedule(self.manifest["questions"], [42, 43])
        self.assertEqual([r["system"] for r in planned], ["RAIR", "KAIR", "KAIR", "RAIR"])
        self.assertEqual(len(load_manifest_examples(self.manifest)), 1)

    def test_invalid_control_settings_and_native_limits(self):
        for name, value in (("temperature", 0), ("seeds", [42, 42]), ("sample_size", 2),
                            ("max_retrieval_calls", 6), ("max_llm_calls", 28)):
            settings = copy.deepcopy(self.settings)
            settings["evaluation"][name] = value
            with self.subTest(name=name), self.assertRaises(ValueError):
                prepare_manifest(settings)

    def test_changed_code_data_and_manifest_are_rejected(self):
        with patch("src.evaluation.paired.source_hashes", return_value={}):
            with self.assertRaisesRegex(ValueError, "source changed"):
                load_manifest_examples(self.manifest)
        changed = copy.deepcopy(self.manifest)
        changed["sampling_policy"]["final_temperature"] = 1
        with self.assertRaisesRegex(ValueError, "sampling and control"):
            load_manifest_examples(changed)
        self.dataset.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Dataset changed"):
            load_manifest_examples(self.manifest)

    def test_paired_runner_executes_real_controllers_and_writes_verified_reports(self):
        summary, clients = self.execute()
        self.assertEqual(summary["num_pairs"], 2)
        for system, calls in (("RAIR", 10), ("KAIR", 5)):
            self.assertEqual(summary["systems"][system]["metrics"]["exact_match"], 1)
            self.assertEqual(summary["systems"][system]["mean_usage"]["llm_calls"], calls)
            self.assertEqual(summary["systems"][system]["error"], 0)
        self.assertEqual(self.records()[-2]["consistent"], True)
        self.assertTrue(self.path.with_suffix(".md").exists())
        self.assertEqual(len(clients), 5)
        self.assertEqual(self.records()[2]["result"]["llm_calls"][0]["request"]["options"]["temperature"], 0.7)
        with patch.object(compare, "OllamaClient", side_effect=AssertionError("No inference on completed resume")):
            self.assertEqual(fingerprint(compare.run(self.manifest, self.path, resume=True)), fingerprint(summary))

    def test_gold_changes_do_not_change_selection_or_any_model_request(self):
        first, left = self.execute()
        selected = self.manifest["questions"]
        self.row["answer"] = "__SECRET_GOLD__"
        self.row["supporting_facts"] = [["__SECRET_SUPPORT__", 999]]
        self.write_data()
        self.manifest = prepare_manifest(self.settings)
        second, right = self.execute(path=self.root / "changed.jsonl")
        self.assertEqual(self.manifest["questions"], selected)
        self.assertEqual([c.requests for c in left[1:]], [c.requests for c in right[1:]])
        self.assertNotIn("__SECRET_", json.dumps([c.requests for c in right[1:]]))
        self.assertEqual(first["systems"]["RAIR"]["metrics"]["exact_match"], 1)
        self.assertEqual(second["systems"]["RAIR"]["metrics"]["exact_match"], 0)
        self.assertEqual(second["systems"]["RAIR"]["metric_denominators"]["citation_f1"], 0)
        self.assertEqual(second["systems"]["RAIR"]["metric_denominators"]["answer_f1"], 2)

    def test_interruption_resume_keeps_completed_errors_in_denominator(self):
        with self.assertRaises(KeyboardInterrupt):
            self.execute([
                ("RAIR", [(full_script()[0][0], OllamaError("offline"))]),
                ("KAIR", [(cycle()[0][0], KeyboardInterrupt())]),
            ])
        self.assertEqual(len([r for r in self.records() if r["record_type"] == "result"]), 1)
        with self.assertRaisesRegex(ValueError, "exactly one result"):
            aggregate(self.manifest, [self.records()[-1]])
        summary, clients = self.execute([
            ("KAIR", complete_cycle() + [answer()]),
            ("KAIR", complete_cycle() + [answer()]), ("RAIR", full_script()),
        ], resume=True)
        self.assertEqual(len(clients), 4)
        self.assertEqual(summary["systems"]["RAIR"]["error"], 1)
        self.assertEqual(summary["systems"]["RAIR"]["metrics"]["exact_match"], 0.5)
        self.assertEqual(summary["systems"]["RAIR"]["coverage"], 0.5)
        self.assertEqual(summary["systems"]["RAIR"]["runs_with_incomplete_token_counts"], 1)

    def test_existing_output_is_never_overwritten(self):
        self.path.write_text("preserve", encoding="utf-8")
        with patch.object(compare, "OllamaClient", side_effect=AssertionError("No model calls")):
            with self.assertRaises(FileExistsError):
                compare.run(self.manifest, self.path)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "preserve")

    def test_resume_rejects_reordered_corrupt_or_mismatched_journal(self):
        self.execute()
        original = self.path.read_text(encoding="utf-8")
        entries = self.records()
        for content in (original.rstrip(), original + "{\n", json.dumps({**entries[0], "manifest_sha256": "bad"}) + "\n",
                        "\n".join(json.dumps(r) for r in [entries[0], entries[3], entries[2]]) + "\n"):
            self.path.write_text(content, encoding="utf-8")
            with self.assertRaises(ValueError):
                compare.read_journal(self.path, self.manifest)

    def test_resume_rejects_changed_model_identity(self):
        self.execute()
        entries = self.records()[:3]
        entries[0]["environment"]["model"]["digest"] = "different-model"
        self.path.write_text("\n".join(json.dumps(r) for r in entries) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "digest or Ollama version changed"):
            self.execute([], resume=True)

    def test_resume_reaudits_saved_settings_and_scores(self):
        self.execute()
        original = self.records()
        for field in ("score", "request"):
            entries = copy.deepcopy(original[:3])
            if field == "score":
                entries[2]["evaluation"]["exact_match"] = 0
            else:
                entries[2]["result"]["llm_calls"][0]["request"]["options"]["temperature"] = 0
            self.path.write_text("\n".join(json.dumps(r) for r in entries) + "\n", encoding="utf-8")
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.execute([], resume=True)

    def test_scoring_counts_losing_agent_retrievals_and_invalid_sources(self):
        example = load_hotpotqa(self.dataset)[1]
        result = {"status": "answered", "prediction": {"answer": "Nerava"},
                  "sources": [{"document_id": example.task.documents[0].document_id,
                               "title": "The Glass Orchard", "sentence_index": 0,
                               "text": "fabricated"}],
                  "agents": [{"query_history": [{"retrieved_document_ids": [example.task.documents[i].document_id]}]}
                             for i in (0, 1)]}
        scores = score_result(result, example)
        self.assertEqual(scores["retrieval_recall"], 1)
        self.assertEqual(scores["invalid_citations"], 1)
        self.assertEqual(scores["citation_precision"], 0)
        result["status"] = "abstained"
        self.assertEqual(score_result(result, example)["exact_match"], 0)


if __name__ == "__main__":
    unittest.main()
