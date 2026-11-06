"""Run the archived Step 4 RAIR core in an isolated process with the shared final policy."""

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass

from src.llm.prompts import RAIR_SYNTHESIZER_SCHEMA, RAIR_SYNTHESIZER_SYSTEM_PROMPT
from src.settings import PROJECT_ROOT, project_path


@dataclass
class ReferenceResult:
    value: dict

    def to_dict(self) -> dict:
        return self.value


class ReferenceRAIRController:
    def __init__(self, settings, client):
        self.settings, self.client = settings, client
        config = settings["evaluation"]["reference_rair"]
        self.root = project_path(config["root"]).resolve()
        archive = project_path(config["archive"])
        if hashlib.sha256(archive.read_bytes()).hexdigest() != config["archive_sha256"]:
            raise ValueError("Reference archive changed.")
        actual = {p.relative_to(self.root).as_posix() for p in (self.root / "src").rglob("*.py")}
        actual.add("requirements.txt")
        if actual != set(config["source_sha256"]):
            raise ValueError("Reference source file inventory changed.")
        for name, digest in config["source_sha256"].items():
            path = (self.root / name).resolve()
            if not path.is_relative_to(self.root) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError("Reference source differs from the frozen Step 4 snapshot.")

    @property
    def policy(self):
        rounds = self.settings["rair"]["max_rounds"]
        return {"max_retrieval_calls": rounds, "max_llm_calls": 2 + 4 * rounds,
                "variant": "Step 4 RAIR core; shared current final-answer policy"}

    def run(self, task):
        if self.client.budget is None:
            raise ValueError("The reference control requires an explicit common budget.")
        final_path = PROJECT_ROOT / "src/rair/synthesizer.py"
        payload = {"settings": self.settings, "task": asdict(task),
                   "budget": self.client.budget.to_dict(),
                   "temperature": self.client.generation_temperature,
                   "final_path": str(final_path), "final_prompt": RAIR_SYNTHESIZER_SYSTEM_PROMPT,
                   "final_schema": RAIR_SYNTHESIZER_SCHEMA}
        # A fresh interpreter prevents imports or mutable state leaking between implementations.
        script = '''
import importlib.util,json,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import src
assert Path(src.__file__).resolve().parent == Path.cwd() / 'src'
from src.datasets.hotpotqa import QuestionInput
from src.retrieval.document_store import Document
from src.evaluation.budget import RunBudget
from src.llm.ollama_client import OllamaClient
from src.rair.controller import RAIRController
p=json.load(sys.stdin)
t=p['task']
task=QuestionInput(t['question_id'],t['question'],tuple(Document(d['document_id'],d['question_id'],d['title'],tuple(d['sentences'])) for d in t['documents']))
client=OllamaClient(p['settings'])
client.budget=RunBudget(**p['budget'])
client.generation_temperature=p['temperature']
controller=RAIRController(p['settings'],client)
spec=importlib.util.spec_from_file_location('shared_final',p['final_path'])
shared=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=shared
spec.loader.exec_module(shared)
shared.RAIR_SYNTHESIZER_SYSTEM_PROMPT=p['final_prompt']
shared.RAIR_SYNTHESIZER_SCHEMA=p['final_schema']
controller.synthesizer=shared.RAIRSynthesizer(client)
json.dump(controller.run(task).to_dict(),sys.stdout,ensure_ascii=False)
'''
        completed = subprocess.run([sys.executable, "-X", "utf8", "-B", "-c", script], cwd=self.root,
                                   input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8",
                                   timeout=self.settings["llm"]["timeout_seconds"] * self.client.budget.max_llm_calls + 30)
        if completed.returncode:
            raise ValueError(f"Reference process failed: {completed.stderr[-1500:]}")
        result = json.loads(completed.stdout)
        budget = result["budget"]
        if (budget["max_llm_calls"] != self.client.budget.max_llm_calls
                or budget["max_retrieval_calls"] != self.client.budget.max_retrieval_calls):
            raise ValueError("Reference process changed its resource limits.")
        for name in ("llm_calls", "retrieval_calls", "final_calls", "exhausted_resource"):
            setattr(self.client.budget, name, budget[name])
        self.client.calls = result["llm_calls"]
        result["reference"] = {"archive_sha256": self.settings["evaluation"]["reference_rair"]["archive_sha256"],
                               "shared_final_sha256": hashlib.sha256(final_path.read_bytes()).hexdigest()}
        return ReferenceResult(result)
