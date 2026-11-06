"""Dashboard integration tests replace only model transport; HTTP stays local."""

import copy
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from dashboard.server import Dashboard, MAX_BODY, custom_task, make_server
from src.datasets.hotpotqa import parse_hotpotqa_record
from src.experiments.check_rair_pipeline import make_task
from src.llm.ollama_client import OllamaClient, OllamaError
from src.settings import load_settings
from test_rair_controller import ScriptedClient as RAIRClient, full_script
from test_kair import ScriptedClient as KAIRClient, complete_cycle, answer

ENVIRONMENT = {"server": {"version": "test"}, "model": {"digest": "frozen-test-model"}}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.settings = load_settings()
        self.app = Dashboard(self.settings, results=self.directory, examples=[])

    def execute(self, payload=None, *, app=None, rair_script=None, environments=None):
        app = app or self.app
        payload = payload or {"example_id": "demo-complete", "seed": 42}
        ready = OllamaClient(self.settings)
        ready.check_ready = Mock(side_effect=environments or [ENVIRONMENT, ENVIRONMENT])
        ready._request = Mock(return_value={"done": True, "done_reason": "stop", "message": {"content": '{"ready":true}'},
                                           "prompt_eval_count": 10, "eval_count": 4})
        clients = []
        order = ["RAIR", "KAIR"] if payload.get("seed", 42) % 2 == 0 else ["KAIR", "RAIR"]
        def factory(settings):
            if not clients:
                client = ready
            else:
                system = order[len(clients)-1]
                client = RAIRClient(settings, rair_script if rair_script is not None else full_script()) if system == "RAIR" else KAIRClient(settings, complete_cycle() + [answer()])
            clients.append(client)
            return client
        with patch("dashboard.server.OllamaClient", side_effect=factory):
            run_id = app.start(payload)
            app.thread.join(timeout=8)
            self.assertFalse(app.thread.is_alive())
        return app.snapshot(run_id), clients

    def test_both_real_controllers_share_inputs_budgets_and_source_citations(self):
        result, clients = self.execute()
        self.assertEqual(result["status"], "completed")
        self.assertIsNone(result["error"])
        self.assertEqual(set(result["results"]), {"RAIR", "KAIR"})
        for system, output in result["results"].items():
            self.assertEqual(output["question"], make_task().question)
            self.assertEqual(output["prediction"]["answer"], "Nerava")
            self.assertEqual(output["budget"]["max_llm_calls"], 18)
            self.assertEqual(output["budget"]["max_retrieval_calls"], 4)
            self.assertEqual({s["title"] for s in output["sources"]}, {"The Glass Orchard", "Mira Solen"})
        self.assertTrue(all(not c.script for c in clients[1:]))
        self.assertIsNone(self.app.active)
        records = [json.loads(line) for line in (self.directory/result["journal"]).read_text(encoding="utf8").splitlines()]
        self.assertEqual(records[0]["task"]["question_id"], make_task().question_id)
        self.assertEqual(records[-1]["record_type"], "summary")
        self.assertTrue(records[-2]["consistent"])

    def test_odd_seed_reverses_system_order_but_preserves_generation_settings(self):
        result, _ = self.execute({"example_id": "demo-complete", "seed": 43})
        self.assertEqual(result["status"], "completed")
        self.assertEqual(list(result["results"]), ["KAIR", "RAIR"])
        self.assertEqual(result["execution_order"], ["KAIR", "RAIR"])
        self.assertEqual(result["results"]["RAIR"]["llm_calls"][-1]["request"]["options"]["seed"], 43)

    def test_catalog_contains_no_gold_and_labels_are_revealed_only_after_both_runs(self):
        task = make_task()
        example = parse_hotpotqa_record({"_id": task.question_id, "question": task.question, "answer": "__HIDDEN_GOLD__",
                                        "context": [[d.title, list(d.sentences)] for d in task.documents],
                                        "supporting_facts": [["The Glass Orchard", 0], ["Mira Solen", 0]]})
        app = Dashboard(self.settings, results=self.directory, examples=[example])
        self.assertNotIn("__HIDDEN_GOLD__", json.dumps(app.bootstrap()))
        result, clients = self.execute({"example_id": task.question_id}, app=app)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["gold_answer"], "__HIDDEN_GOLD__")
        for client in clients:
            self.assertNotIn("__HIDDEN_GOLD__", json.dumps(client.calls))
        self.assertEqual(result["evaluation"]["RAIR"]["exact_match"], 0)

    def test_one_engine_validation_error_does_not_hide_the_other_result(self):
        script = full_script()[:3]
        script[-1] = (script[-1][0], {"selections": [{"document_id": "unknown", "sentence_indices": [0]}]})
        result, _ = self.execute(rair_script=script)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["results"]["RAIR"]["status"], "error")
        self.assertEqual(result["results"]["KAIR"]["status"], "answered")

    def test_model_identity_change_invalidates_comparison_but_retains_traces(self):
        changed = copy.deepcopy(ENVIRONMENT)
        changed["model"]["digest"] = "changed"
        result, _ = self.execute(environments=[ENVIRONMENT, changed])
        self.assertEqual(result["status"], "failed")
        self.assertIn("identity changed", result["error"])
        self.assertEqual(len(result["results"]), 2)

    def test_completion_is_not_published_before_the_summary_is_saved(self):
        original_open = Path.open
        observed = []
        app = self.app
        directory = self.directory
        class FailingSummary:
            def __init__(self, handle):
                self.handle = handle
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.handle.close()
            def write(self, text):
                if json.loads(text)["record_type"] == "summary":
                    observed.append(app.snapshot(app.active)["status"])
                    raise OSError("simulated disk full")
                return self.handle.write(text)
        def guarded_open(path, mode="r", *args, **kwargs):
            handle = original_open(path, mode, *args, **kwargs)
            return FailingSummary(handle) if mode == "a" and path.parent == directory and path.suffix == ".jsonl" else handle
        with patch.object(Path, "open", new=guarded_open):
            result, _ = self.execute()
        self.assertEqual(observed, ["running"])
        self.assertEqual(result["status"], "failed")
        self.assertIn("simulated disk full", result["error"])
        self.assertEqual(len(result["results"]), 2)

    def test_offline_run_is_explicit_and_preserves_exposure_record(self):
        with patch("dashboard.server.OllamaClient", side_effect=OllamaError("offline")):
            self.assertFalse(self.app.health()["ready"])
            run_id = self.app.start({"example_id": "demo-complete"})
            self.app.thread.join(timeout=3)
        result = self.app.snapshot(run_id)
        self.assertEqual(result["status"], "failed")
        self.assertIn("offline", result["error"])
        self.assertEqual(result["results"], {})
        record = json.loads((self.directory/result["journal"]).read_text().splitlines()[0])
        self.assertEqual(record["question_id"], make_task().question_id)

    def test_only_one_comparison_is_admitted_at_a_time(self):
        release = threading.Event()
        def blocked(run_id, *_):
            release.wait(timeout=3)
        with patch.object(self.app, "_execute", side_effect=blocked):
            first = self.app.start({"example_id": "demo-complete"})
            try:
                self.assertIsNone(self.app.start({"example_id": "demo-missing"}))
                self.assertEqual(len(list(self.directory.glob("*.jsonl"))), 1)
                self.assertEqual(self.app.snapshot(first)["status"], "running")
            finally:
                release.set()
                self.app.thread.join(timeout=3)

    def test_untrusted_fields_invalid_ids_and_seeds_are_rejected_before_inference(self):
        for payload in ([], {"example_id": "missing"}, {"example_id": "demo-complete", "answer": "spoiler"},
                        {"example_id": "demo-complete", "seed": True}, {"example_id": "demo-complete", "seed": -1},
                        {"question": "Who?", "documents": [], "gold": "no"}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.app.start(payload)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_retained_run_limit_evicts_only_memory_and_preserves_saved_journals(self):
        saved = self.directory / "dashboard_old.jsonl"
        saved.write_text('preserve completed journal\n', encoding="utf8")
        self.app.jobs = {f"old{i}": {"status": "completed"} for i in range(20)}
        with patch.object(self.app, "_execute"):
            run_id = self.app.start({"example_id": "demo-complete"})
            self.app.thread.join(timeout=3)
        self.assertEqual(len(self.app.jobs), 20)
        self.assertNotIn("old0", self.app.jobs)
        self.assertIn(run_id, self.app.jobs)
        self.assertEqual(saved.read_text(encoding="utf8"), 'preserve completed journal\n')

    def test_custom_sources_preserve_text_and_never_accept_labels(self):
        payload = {"question": "Who?", "documents": [{"title": "<img src=x>", "sentences": ["  Original sentence.  "]}]}
        task = custom_task(payload, "local")
        self.assertEqual(task.documents[0].sentences[0], "  Original sentence.  ")
        self.assertEqual(task.documents[0].document_id, "local:D1")
        for invalid in ({"question": " ", "documents": payload["documents"]},
                        {"question": "x"*2001, "documents": payload["documents"]},
                        {"question": "Who?", "documents": []},
                        {"question": "Who?", "documents": [{"title": "Source", "sentences": [""]}]},
                        {"question": "Who?", "documents": [{"title": "Source", "sentences": ["x"], "answer": "x"}]}):
            with self.subTest(invalid=str(invalid)[:80]), self.assertRaises(ValueError):
                custom_task(invalid, "local")

    def test_nonfinite_temperature_and_nonlocal_retrieval_are_rejected(self):
        for key, value in (("temperature", float("nan")), ("temperature", float("inf")), ("temperature", True)):
            settings = copy.deepcopy(self.settings)
            settings["evaluation"][key] = value
            with self.assertRaises(ValueError):
                Dashboard(settings, examples=[])
        settings = copy.deepcopy(self.settings)
        settings["retrieval"]["web_enabled"] = True
        with self.assertRaises(ValueError):
            Dashboard(settings, examples=[])


class HTTPTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.app = Dashboard(load_settings(), results=directory.name, examples=[])
        self.server = make_server(self.app, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=3)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_page_assets_and_catalog_are_served_without_exposing_project_files(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Actual benchmark results", body)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        for path in ("/styles.css", "/app.js", "/api/bootstrap"):
            self.assertEqual(self.request("GET", path)[0], 200)
        for path in ("/../config/settings.yaml", "/results/step5_fresh_benchmark.jsonl", "/api/runs/unknown"):
            self.assertEqual(self.request("GET", path)[0], 404)

    def test_cross_origin_and_rebound_host_are_rejected(self):
        self.assertEqual(self.request("GET", "/", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request("POST", "/api/runs", "{}", {"Content-Type": "application/json", "Origin": "https://evil.example"})[0], 403)

    def test_invalid_json_content_type_size_and_payload_return_actionable_errors(self):
        for body, headers, expected in (("{}", {"Content-Type": "text/plain"}, 415),
                                        ("{", {"Content-Type": "application/json"}, 400),
                                        ("[]", {"Content-Type": "application/json"}, 400),
                                        ("", {"Content-Type": "application/json", "Content-Length": str(MAX_BODY+1)}, 413)):
            status, _, data = self.request("POST", "/api/runs", body, headers)
            self.assertEqual(status, expected)
            self.assertIn("error", json.loads(data))

    def test_submission_busy_response_and_download_routes(self):
        payload = {"example_id": "demo-complete", "seed": 42}
        with patch.object(self.app, "start", return_value="accepted") as start:
            status, _, body = self.request("POST", "/api/runs", json.dumps(payload), {"Content-Type": "application/json"})
            self.assertEqual(status, 202)
            self.assertEqual(json.loads(body)["id"], "accepted")
            start.assert_called_once_with(payload)
        self.app.active = "busy"
        with patch.object(self.app, "start", return_value=None):
            self.assertEqual(self.request("POST", "/api/runs", "{}", {"Content-Type": "application/json"})[0], 409)
        with patch.object(self.app, "snapshot", return_value={"id": "saved", "status": "completed"}):
            status, headers, body = self.request("GET", "/api/runs/saved/download")
            self.assertEqual(status, 200)
            self.assertIn("attachment", headers["Content-Disposition"])
            self.assertEqual(json.loads(body)["id"], "saved")


if __name__ == "__main__":
    unittest.main()
