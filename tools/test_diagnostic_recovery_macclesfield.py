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

target_qids = [
    ("5ae28058554299495565da90", "1958"),
    ("5a7e04b05542995f4f40238a", "Vanarama"),
]

for qid, expected_gold in target_qids:
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
    res_dict = result.to_dict()
    eval_score = score_result(res_dict, example)
    
    ans = result.prediction.answer
    print(f"Result Status: {result.status} (stop: {result.stop_reason})")
    print(f"Answer: {ans!r}")
    print(f"Exact Match: {eval_score['exact_match']}")
    print(f"Answer F1: {eval_score['answer_f1']:.4f}")
    print(f"Calls: {budget.llm_calls}, Retrievals: {budget.retrieval_calls}")
    print(f"Gaps in state:")
    for g in result.state.gaps:
        print(f"  [{g.gap_id}] resolved={g.resolved}: {g.description}")
    print(f"Verified facts:")
    for f in result.state.verified_facts:
        print(f"  [{f.fact_id} for {f.gap_id}]: {f.statement}")
