"""Local RAIR/KAIR dashboard: one serial comparison at a time."""

import argparse
import copy
import json
import math
import threading
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from dashboard.research import ResearchArchive
from dashboard.ablations import AblationStudy, ConfirmationStudy, RAIRv2Study, RAIRv3Study, RAIRScaleStudy, RAIRTestStudy, GrandSynthesisStudy

from src.datasets.hotpotqa import QuestionInput, load_hotpotqa
from src.evaluation.budget import RunBudget
from src.evaluation.paired import audit_result, score_result, source_hashes
from src.experiments.check_rair_pipeline import make_task
from src.experiments.compare import identity
from src.kair.controller import KAIRController
from src.llm.ollama_client import OllamaClient
from src.rair.controller import RAIRController
from src.retrieval.document_store import Document
from src.settings import PROJECT_ROOT, load_settings

STATIC = Path(__file__).parent / "static"
MAX_BODY = 256_000
CONTROLLERS = {"RAIR": RAIRController, "KAIR": KAIRController}


def custom_task(payload, run_id):
    question = payload.get("question")
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError("Enter a question of 1–2000 characters.")
    documents = payload.get("documents")
    if not isinstance(documents, list) or not 1 <= len(documents) <= 20:
        raise ValueError("Supply between one and twenty source documents.")
    pool = []
    for index, item in enumerate(documents, 1):
        if not isinstance(item, dict) or set(item) != {"title", "sentences"}:
            raise ValueError("Each source needs only a title and a list of sentences.")
        title, sentences = item["title"], item["sentences"]
        if not isinstance(title, str) or not title.strip() or len(title) > 300:
            raise ValueError("Each source needs a title of 1–300 characters.")
        if (not isinstance(sentences, list) or not 1 <= len(sentences) <= 100
                or any(not isinstance(s, str) or not s.strip() for s in sentences)):
            raise ValueError("Each source needs 1–100 nonempty sentence strings.")
        pool.append(Document(f"{run_id}:D{index}", run_id, title, tuple(sentences)))
    if sum(len(d.title) + len(d.text) for d in pool) > 100_000:
        raise ValueError("Sources exceed the 100,000 character limit.")
    return QuestionInput(run_id, question, tuple(pool))


class Dashboard:
    def __init__(self, settings, *, results=None, examples=None):
        self.settings = copy.deepcopy(settings)
        self.results = Path(results) if results else PROJECT_ROOT / "results"
        self.lock = threading.RLock()
        self.jobs = {}
        self.active = None
        self.thread = None
        self.research = ResearchArchive()
        self.ablations = AblationStudy()
        self.confirmation = ConfirmationStudy()
        self.rair_v2 = RAIRv2Study()
        self.rair_v3 = RAIRv3Study()
        self.rair_scale = RAIRScaleStudy()
        self.rair_test = RAIRTestStudy()
        self.grand_synthesis = GrandSynthesisStudy()
        self.examples = {"demo-complete": (make_task(), None, "Two-hop example · complete evidence"),
                         "demo-missing": (make_task(missing_birthplace=True), None, "Two-hop example · missing evidence")}
        if examples is None:
            path = PROJECT_ROOT / "data/processed/step5_development.json"
            examples = load_hotpotqa(path) if path.exists() else []
        for example in examples:
            self.examples[example.task.question_id] = (example.task, example, example.task.question)
        limits = self.settings["evaluation"]
        budget = RunBudget(limits["max_retrieval_calls"], limits["max_llm_calls"])
        temperature = limits["temperature"]
        if type(temperature) not in (int, float) or not math.isfinite(temperature) or temperature < .7:
            raise ValueError("The common non-final temperature must be at least 0.7.")
        if (self.settings["retrieval"]["method"] != "bm25"
                or self.settings["retrieval"]["corpus_scope"] != "per_question"
                or self.settings["retrieval"]["web_enabled"] is not False):
            raise ValueError("The comparison requires local per-question BM25 retrieval.")
        for controller in CONTROLLERS.values():
            policy = controller(self.settings, OllamaClient(self.settings)).policy
            if budget.max_llm_calls > policy["max_llm_calls"] or budget.max_retrieval_calls > policy["max_retrieval_calls"]:
                raise ValueError("Common limits exceed an engine's native ceiling.")

    def bootstrap(self):
        with self.lock:
            active = self.active
        try:
            data = json.loads((PROJECT_ROOT / "results/step5_fresh_benchmark.summary.json").read_text(encoding="utf8"))
            benchmark = {"available": True, "systems": data["systems"],
                         "questions": data["uncertainty"]["num_questions"],
                         "seeds": data["uncertainty"]["seeds_per_question"],
                         "core": data["RAIR_minus_REFERENCE"]["metrics"],
                         "comparison": data["uncertainty"]["KAIR_minus_RAIR"]}
        except (OSError, ValueError, KeyError, TypeError):
            benchmark = {"available": False, "message": "The recorded Step 5 benchmark is unavailable."}
        return {"api_features": ["live_progress_v1"],
                "model": self.settings["llm"]["model"], "controls": self.settings["evaluation"],
                "seed": self.settings["project"]["seed"], "num_agents": self.settings["kair"]["num_agents"],
                "active_run": active, "examples": [{"id": key, "label": label, "task": asdict(task)}
                    for key, (task, _, label) in self.examples.items()], "benchmark": benchmark}

    def health(self):
        settings = copy.deepcopy(self.settings)
        settings["llm"]["timeout_seconds"] = 3
        try:
            ready = OllamaClient(settings).check_ready()
            return {"ready": True, "model": settings["llm"]["model"], "environment": ready}
        except (OSError, ValueError, RuntimeError) as exc:
            return {"ready": False, "model": settings["llm"]["model"], "message": str(exc)}

    def start(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object.")
        seed = payload.get("seed", self.settings["project"]["seed"])
        if type(seed) is not int or not 0 <= seed <= 2_147_483_645:
            raise ValueError("Seed must be an integer between 0 and 2147483645.")
        run_id = uuid.uuid4().hex
        if "example_id" in payload:
            if set(payload) - {"example_id", "seed"} or not isinstance(payload["example_id"], str):
                raise ValueError("Use an example ID and seed, or a custom question with sources.")
            if payload["example_id"] not in self.examples:
                raise ValueError("Unknown example. Select a question from the menu.")
            task, example, _ = self.examples[payload["example_id"]]
        else:
            if set(payload) - {"question", "documents", "seed"}:
                raise ValueError("Custom runs accept only question, documents and seed.")
            task, example = custom_task(payload, f"dashboard-{run_id}"), None
        with self.lock:
            if self.active:
                return None
            self.results.mkdir(parents=True, exist_ok=True)
            output = self.results / f"dashboard_{run_id}.jsonl"
            record = {"record_type": "metadata", "run_id": run_id,
                      "created_at_utc": datetime.now(timezone.utc).isoformat(),
                      "purpose": "Interactive demonstration, not a prospective benchmark.",
                      "question_id": task.question_id, "task": asdict(task), "seed": seed,
                      "settings": self.settings, "source_sha256": source_hashes(),
                      "execution_order": ["RAIR", "KAIR"] if seed % 2 == 0 else ["KAIR", "RAIR"]}
            # Register exposure before inference, including interrupted runs.
            with output.open("x", encoding="utf8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            while len(self.jobs) >= 20:
                del self.jobs[next(iter(self.jobs))]
            self.jobs[run_id] = {"id": run_id, "status": "running", "stage": "Checking Ollama",
                                 "task": asdict(task), "seed": seed, "example_id": payload.get("example_id"),
                                 "started": time.monotonic(), "started_at_utc": record["created_at_utc"],
                                 "results": {}, "environment": None, "error": None, "_client": None,
                                 "_system": None, "_controller": None, "_output": output, "journal": output.name,
                                 "_events": [],
                                 "source_sha256": record["source_sha256"], "execution_order": record["execution_order"],
                                 "controls": self.settings["evaluation"]}
            self.active = run_id
            self.thread = threading.Thread(target=self._execute, args=(run_id, task, example), daemon=True)
            self.thread.start()
        return run_id

    def snapshot(self, run_id, *, light=False, after=0):
        with self.lock:
            job = self.jobs.get(run_id)
            if job is None:
                return None
            if light:
                if type(after) is not int or not 0 <= after <= len(job['_events']):
                    raise ValueError('Invalid progress cursor.')
                fields = ('id', 'status', 'stage', 'controls', 'error', 'evaluation', 'gold_answer')
                result = {key: copy.deepcopy(job[key]) for key in fields if key in job}
                result['result_statuses'] = {s: r['status'] for s, r in job['results'].items()}
                result['events'] = copy.deepcopy(job['_events'][after:])
                result['cursor'] = len(job['_events'])
            else:
                result = {key: copy.deepcopy(value) for key, value in job.items()
                          if not key.startswith("_") and key != "started"}
            result["elapsed_seconds"] = round(job.get("duration", time.monotonic() - job["started"]), 1)
            client = job["_client"]
            controller = job.get("_controller")
            phase = (getattr(controller, '_stage', '') if job['_system'] == 'RAIR'
                     else getattr(getattr(controller, 'agent', None), 'stage', ''))
            result["progress"] = {"system": job["_system"], "llm_calls": len(client.calls) if client else 0,
                                  "retrieval_calls": client.budget.retrieval_calls if client and client.budget else 0,
                                  "phase": phase}
            return result

    def result(self, run_id, system):
        with self.lock:
            job = self.jobs.get(run_id)
            return copy.deepcopy(job['results'].get(system)) if job else None

    def _publish(self, run_id, system, stage, details):
        with self.lock:
            job = self.jobs[run_id]
            job['_events'].append({'sequence': len(job['_events']) + 1, 'system': system,
                                   'stage': stage, 'elapsed_seconds': round(time.monotonic() - job['started'], 2),
                                   'details': copy.deepcopy(details)})

    def _execute(self, run_id, task, example):
        job = self.jobs[run_id]
        def update(**values):
            with self.lock:
                job.update(values)
        def save(record):
            with job["_output"].open("a", encoding="utf8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        try:
            settings = copy.deepcopy(self.settings)
            settings["project"]["seed"] = job["seed"]
            ready_client = OllamaClient(settings)
            before = ready_client.check_ready()
            update(environment=before, stage="Warming the shared model")
            warmup = ready_client.chat('Return only the JSON object {"ready": true}.',
                                      "Initialize the model for a local comparison.",
                                      schema={"type": "object", "properties": {"ready": {"const": True}},
                                              "required": ["ready"], "additionalProperties": False},
                                      temperature=0.0, num_predict=16)
            if warmup.json_object() != {"ready": True}:
                raise ValueError("The model warm-up did not return the expected response.")
            save({"record_type": "environment", "environment": before, "warmup": asdict(warmup)})
            for system in job["execution_order"]:
                client = OllamaClient(settings)
                config = settings["evaluation"]
                client.budget = RunBudget(config["max_retrieval_calls"], config["max_llm_calls"])
                client.generation_temperature = config["temperature"]
                controller = CONTROLLERS[system](settings, client, on_progress=
                    lambda stage, details, system=system: self._publish(run_id, system, stage, details))
                update(stage=f"Running {system}", _system=system, _client=client, _controller=controller)
                result = controller.run(task).to_dict()
                audit_result(result, task, client.budget, settings, job["seed"], system)
                save({"record_type": "result", "system": system, "question_id": task.question_id, "result": result})
                with self.lock:
                    job["results"][system] = result
            after = ready_client.check_ready()
            consistent = identity(before) == identity(after)
            save({"record_type": "verification", "consistent": consistent, "environment": after})
            if not consistent:
                raise ValueError("Model identity changed during this comparison; inspect the traces before comparing results.")
            # Gold is consulted only after both controllers have returned.
            if example:
                update(evaluation={s: score_result(r, example) for s, r in job["results"].items()},
                       gold_answer=example.gold.answer)
            save({"record_type": "summary", "completed": True, "question_id": task.question_id,
                  "statuses": {s: r["status"] for s, r in job["results"].items()},
                  "evaluation": job.get("evaluation"), "gold_answer": job.get("gold_answer")})
            update(status="completed", stage="Comparison complete")
        except Exception as exc:
            update(status="failed", stage="Comparison stopped", error=f"{type(exc).__name__}: {exc}")
            try:
                save({"record_type": "error", "question_id": task.question_id, "message": job["error"]})
            except OSError:
                pass
        finally:
            with self.lock:
                job["duration"] = time.monotonic() - job["started"]
                job["_client"] = None
                job["_system"] = None
                job["_controller"] = None
                self.active = None


def make_server(app, port=8765):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, value, content_type="application/json; charset=utf-8", *, download=False):
            body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode("utf8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            if download:
                self.send_header("Content-Disposition", 'attachment; filename="rair-kair-comparison.json"')
            self.end_headers()
            self.wfile.write(body)

        def _allowed(self):
            port = self.server.server_address[1]
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            if host not in {f"127.0.0.1:{port}", f"localhost:{port}"} or (origin is not None and origin != f"http://{host}"):
                self._send(403, {"error": "This dashboard accepts same-origin localhost requests only."})
                return False
            return True

        def do_GET(self):
            if not self._allowed():
                return
            path = urlsplit(self.path).path
            assets = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/styles.css": ("styles.css", "text/css; charset=utf-8"),
                      "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                      "/research.js": ("research.js", "text/javascript; charset=utf-8")}
            if path in assets:
                name, mime = assets[path]
                self._send(200, (STATIC / name).read_bytes(), mime)
            elif path == "/api/bootstrap":
                self._send(200, app.bootstrap())
            elif path == "/api/health":
                self._send(200, app.health())
            elif path == '/api/grand_synthesis':
                try:
                    self._send(200, app.grand_synthesis.describe())
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    self._send(503, {'available': False, 'error': 'Grand synthesis unavailable: ' + str(exc)})
            elif path in ('/api/ablations', '/api/confirmation', '/api/rair_v2', '/api/rair_v3', '/api/rair_scale', '/api/rair_test'):
                try:
                    study = (app.ablations if path == '/api/ablations'
                             else app.confirmation if path == '/api/confirmation'
                             else app.rair_v2 if path == '/api/rair_v2'
                             else app.rair_v3 if path == '/api/rair_v3'
                             else app.rair_scale if path == '/api/rair_scale'
                             else app.rair_test)
                    self._send(200, study.describe())
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    self._send(503, {'available':False,'error':'Recorded study unavailable: '+str(exc)})
            elif path in ('/api/confirmation/case', '/api/rair_v2/case', '/api/rair_v3/case', '/api/rair_scale/case', '/api/rair_test/case'):
                params = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                if set(params) != {'question_id','seed'} or any(len(v) != 1 for v in params.values()):
                    self._send(400, {'error':'Supply one question_id and one seed.'})
                    return
                try:
                    seed = int(params['seed'][0])
                except ValueError:
                    self._send(400, {'error':'Seed must be an integer.'})
                    return
                try:
                    study = (app.confirmation if path == '/api/confirmation/case'
                             else app.rair_v2 if path == '/api/rair_v2/case'
                             else app.rair_v3 if path == '/api/rair_v3/case'
                             else app.rair_scale if path == '/api/rair_scale/case'
                             else app.rair_test)
                    self._send(200, study.case(params['question_id'][0], seed))
                except KeyError:
                    self._send(404, {'error':'No completed case for that question and seed.'})
                except (OSError, ValueError, TypeError) as exc:
                    self._send(503, {'error':'Recorded case unavailable: '+str(exc)})
            elif path in ('/api/research', '/api/research/cases', '/api/research/case'):
                params = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                allowed = set() if path == '/api/research' else ({'question_id', 'seed', 'download'} if path.endswith('/case')
                          else {'group', 'search', 'issue', 'seed', 'offset', 'limit'})
                if set(params) - allowed or any(len(v) != 1 for v in params.values()):
                    self._send(400, {'error': 'Unknown or duplicate research query fields.'})
                    return
                values = {k: v[0] for k, v in params.items()}
                try:
                    download = values.pop('download', '')
                    if download not in ('', '1'):
                        raise ValueError('Invalid download value.')
                    if 'seed' in values and values['seed'] != '':
                        values['seed'] = int(values['seed'])
                    for key in ('offset', 'limit'):
                        if key in values:
                            values[key] = int(values[key])
                    if path.endswith('/case') and (not values.get('question_id') or values.get('seed', '') == ''):
                        raise ValueError('Choose a recorded question and seed.')
                except ValueError as exc:
                    self._send(400, {'error': str(exc)})
                    return
                try:
                    if path == '/api/research':
                        value = app.research.describe()
                    elif path.endswith('/cases'):
                        # Filter validation is separate from archive availability.
                        app.research.describe()
                        try:
                            value = app.research.list_cases(**values)
                        except ValueError as exc:
                            self._send(400, {'error': str(exc)})
                            return
                    else:
                        value = app.research.case(**values)
                    self._send(200, value, download=download == '1')
                except KeyError:
                    self._send(404, {'error': 'Recorded question or seed not found.'})
                except (OSError, ValueError, TypeError) as exc:
                    self._send(503, {'available': False, 'error': 'Research archive unavailable: ' + str(exc)})
            elif path.startswith("/api/runs/"):
                parts = path.split("/")
                if len(parts) == 5 and parts[4] == 'progress':
                    params = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                    try:
                        if set(params) - {'after'} or any(len(v) != 1 for v in params.values()):
                            raise ValueError('Use one progress cursor.')
                        after = int(params.get('after', ['0'])[0])
                        value = app.snapshot(parts[3], light=True, after=after)
                        self._send(200, value) if value is not None else self._send(404, {'error': 'Run not retained.'})
                    except ValueError as exc:
                        self._send(400, {'error': str(exc)})
                    return
                if len(parts) == 6 and parts[4] == 'results' and parts[5] in CONTROLLERS:
                    value = app.result(parts[3], parts[5])
                    self._send(200, value) if value is not None else self._send(404, {'error': 'Engine result not available.'})
                    return
                if len(parts) not in (4, 5) or (len(parts) == 5 and parts[4] != "download"):
                    self._send(404, {"error": "Unknown endpoint."})
                    return
                result = app.snapshot(parts[3])
                if result:
                    self._send(200, result, download=len(parts) == 5)
                else:
                    self._send(404, {"error": "Run not retained. Saved journals remain in results/."})
            else:
                self._send(404, {"error": "Unknown endpoint."})

        def do_POST(self):
            if not self._allowed():
                return
            if urlsplit(self.path).path != "/api/runs":
                self._send(404, {"error": "Unknown endpoint."})
                return
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                self._send(415, {"error": "Send application/json."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    self._send(413, {"error": "Request body must be between 1 and 256000 bytes."})
                    return
                self.connection.settimeout(10)
                run_id = app.start(json.loads(self.rfile.read(length).decode("utf8")))
                if run_id is None:
                    self._send(409, {"error": "A comparison is already running. Wait for it to finish.", "active_run": app.active})
                else:
                    self._send(202, {"id": run_id})
            except (ValueError, TypeError, UnicodeError) as exc:
                self._send(400, {"error": str(exc)})
            except OSError:
                self._send(500, {"error": "Could not read the request or save its journal."})

        def log_message(self, fmt, *args):
            print(f"[dashboard] {fmt % args}", flush=True)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--config", default="config/settings.yaml")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535.")
    try:
        app = Dashboard(load_settings(args.config))
        server = make_server(app, args.port)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f"[FAIL] {exc}\n")
    print(f"RAIR vs KAIR dashboard: http://127.0.0.1:{args.port}\nPress Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
