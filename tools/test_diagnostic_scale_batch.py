import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.datasets.hotpotqa import parse_hotpotqa_record
from src.evaluation.budget import RunBudget
from src.evaluation.paired import score_result
from src.llm.ollama_client import OllamaClient
from src.rair.controller import RAIRController
from src.settings import load_settings

raw_path = ROOT / "data/raw/hotpot_dev_distractor_v1.json"
with open(raw_path, "r", encoding="utf-8") as f:
    raw_data = {q["_id"]: q for q in json.load(f)}

settings = load_settings("config/rair_scale_settings.json")

test_cases = [
    ("5a7e05635542995f4f40238f", "January 2016"),
    ("5ade66f055429939a52fe8a0", "Humberside Airport"),
    ("5a7ca98f55429935c91b5288", "Christian"),
    ("5add596f5542994c65e8869a", "Captain Hans Geering"),
]

for qid, expected_gold in test_cases:
    example = parse_hotpotqa_record(raw_data[qid])
    client = OllamaClient(settings)
    budget = RunBudget(max_retrieval_calls=4, max_llm_calls=18)
    client.budget = budget
    controller = RAIRController(settings, client)
    
    print(f"\n=======================================================")
    print(f"RUNNING: {qid}")
    print(f"Question: {example.task.question}")
    print(f"Expected Gold: {expected_gold}")
    
    result = controller.run(example.task)
    eval_score = score_result(result.to_dict(), example)
    
    print(f"Status: {result.status} (stop: {result.stop_reason})")
    print(f"Prediction: {result.prediction.answer!r}")
    print(f"Exact Match: {eval_score['exact_match']}")
    print(f"Answer F1: {eval_score['answer_f1']:.4f}")
    print(f"Calls: {budget.llm_calls}, Retrievals: {budget.retrieval_calls}")
    print("Gaps:")
    for g in result.state.gaps:
        print(f"  [{g.gap_id}] (resolved={g.resolved}): {g.description}")
    print("Verified Facts:")
    for f in result.state.verified_facts:
        print(f"  [{f.fact_id} for {f.gap_id}]: {f.statement}")

